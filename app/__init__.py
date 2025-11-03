# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta

db = SQLAlchemy()
migrate = Migrate()

def get_current_sunday_week():
    """Return (year, week) for current Sunday-start week."""
    today = datetime.now().date()
    # Go back to Sunday (weekday: 0=Mon, 6=Sun)
    sunday = today - timedelta(days=today.weekday() + 1)
    return sunday.isocalendar()[0], sunday.isocalendar()[1]

def create_app():
    app = Flask(__name__)
    
    # CONFIG
    app.config['SECRET_KEY'] = 'macho-madness-yeah!'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wfm_planner.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # INIT
    db.init_app(app)
    migrate.init_app(app, db)

    # BLUEPRINT
    from . import routes
    app.register_blueprint(routes.bp)

    # JINJA GLOBAL
    app.jinja_env.globals['get_current_sunday_week'] = get_current_sunday_week

    return app