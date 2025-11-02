# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# SINGLE SOURCE OF TRUTH: One db instance
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'macho-madness-yeah!'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wfm_planner.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # INITIALIZE DB WITH APP
    db.init_app(app)

    # Import models AFTER db is created
    from . import models

    from .routes import bp
    app.register_blueprint(bp)

    # Create tables
    with app.app_context():
        db.create_all()

    return app