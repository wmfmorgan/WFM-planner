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


# Apply to login attempts
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth():
            return ("Unauthorized", 401, {'WWW-Authenticate': 'Basic realm="WFM Planner"'})
        return f(*args, **kwargs)
    return decorated

def get_current_sunday_week():
    """Return (year, week) for current Sunday-start week."""
    today = datetime.now().date()
    # Go back to Sunday (weekday: 0=Mon, 6=Sun)
    sunday = today - timedelta(days=today.weekday() + 1)
    return sunday.isocalendar()[0], sunday.isocalendar()[1]

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///wfm_planner.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # CONFIG
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(app.instance_path, 'wfm_planner.db')
    ).replace('postgres://', 'postgresql://', 1)  # Render fix
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.jinja_env.autoescape = True
    
# === AUTH & LIMITER SETUP ===
    def check_auth():
        auth = request.authorization
        password = os.getenv("WFM_PASSWORD")
        return auth and auth.username == "admin" and auth.password == password

    limiter = Limiter(
        app=app,
       key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    # Attach to app for routes to use
    app.check_auth = check_auth
    app.limiter = limiter

    # INIT
    db.init_app(app)
    migrate.init_app(app, db)
    

    
    # BLUEPRINT
    from . import routes
    #routes.setup_auth_and_limiter(app)

    limiter.limit("5 per minute", exempt_when=lambda: request.authorization and request.authorization.username == "admin")       
    app.register_blueprint(routes.bp)

    # JINJA GLOBAL
    app.jinja_env.globals['get_current_sunday_week'] = get_current_sunday_week

    # === AUTO CREATE DB & MIGRATE ON FIRST RUN ===
    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()  # Creates tables if no migrations
        # OR use migrate if you have migrations
        # from flask_migrate import upgrade
        # upgrade()

    return app

# Required for Render
app = create_app()