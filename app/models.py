# app/models.py
from datetime import datetime
from . import db  # Import from __init__.py

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    motivation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    steps = db.relationship('Step', backref='goal', lazy=True, cascade='all, delete-orphan')

    def progress(self):
        total = len(self.steps)
        if total == 0:
            return 0
        completed = len([s for s in self.steps if s.completed])
        return int((completed / total) * 100)

class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.Date)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)