from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'macho-madness-yeah!'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wfm_planner.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db) 
    
    from . import models
    from .routes import bp
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    return app