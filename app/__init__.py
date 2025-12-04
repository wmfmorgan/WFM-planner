# app/__init__.py
from functools import wraps
import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ========= CONFIG =========
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret'),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            'DATABASE_URL',
            'sqlite:///' + os.path.join(app.instance_path, 'wfm_planner.db')
        ).replace('postgres://', 'postgresql://', 1),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    from datetime import date   # ← Add this import at the top with the others!

    @app.context_processor
    def inject_today():
        real_today = date.today()                                   # ← FRESH DAILY, BROTHER!
        return dict(
            today=real_today,
            today_quarter=(real_today.month - 1) // 3 + 1
        )

    # ========= AUTH =========
    def check_auth():
        auth = request.authorization
        password = os.getenv("WFM_PASSWORD")
        return auth and auth.username == "admin" and auth.password == password

    # ========= LIMIIIIIIITEEEERRRR — THE FINAL FORM =========
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",  # Silences warning (dev only)
        headers_enabled=True
    )

    # GLOBAL BURST LIMIT — CORRECT WAY
    limiter._default_limits = ["15 per minute"]  # This is the real way

    # ADMIN BYPASSES ALL LIMITS — OFFICIAL METHOD
    @limiter.request_filter
    def exempt_admin():
        return check_auth()

    # ========= ATTACH =========
    app.check_auth = check_auth
    app.limiter = limiter

    # ========= DB =========
    db.init_app(app)
    migrate.init_app(app, db)

    # ========= REGISTER BLUEPRINT FIRST =========
    from . import routes
    app.register_blueprint(routes.bp)

    # ========= NOW PROTECT SPECIFIC ENDPOINTS =========
    # Fix the real endpoint names (Flask uses function name, not route path)
    protected_endpoints = {
        'import_calendar': "3 per minute",           # ← this is the function name!
        'api_add_task': "12 per minute",
        'create_goal': "12 per minute",
        'add_subgoal': "12 per minute",
        'update_goal_status': "12 per minute",
        'api_create_event': "10 per minute",
        'api_note': "100 per minute",
    }

    for endpoint_name, limit_str in protected_endpoints.items():
        if endpoint_name in routes.bp.view_functions:
            original_func = routes.bp.view_functions[endpoint_name]
            routes.bp.view_functions[endpoint_name] = limiter.limit(
                limit_str,
                exempt_when=check_auth
            )(original_func)

    # ========= JINJA =========
    def get_current_sunday_week():
        today = datetime.now().date()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        return sunday.isocalendar()[:2]

    app.jinja_env.globals['get_current_sunday_week'] = get_current_sunday_week

    # ========= DB CREATE =========
    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()

    return app


# Required for "flask run"
# app = create_app()