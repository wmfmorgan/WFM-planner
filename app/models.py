# app/models.py
from datetime import datetime, date
from . import db

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # e.g., Annual, Q1, Jan, etc.
    description = db.Column(db.Text, nullable=False)
    motivation = db.Column(db.Text)
    due_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=True)

    # Self-referencing relationship
    children = db.relationship(
        'Goal',
        backref=db.backref('parent', remote_side=[id]),
        lazy=True,
        cascade='all, delete-orphan'
    )

    def progress(self):
        """Roll-up progress from children"""
        if not self.children:
            return 100 if self.completed else 0
        total = len(self.children)
        completed = sum(1 for c in self.children if c.progress() == 100)
        return int((completed / total) * 100) if total else 0

    def level(self):
        """Determine hierarchy level"""
        if not self.parent:
            return 'annual'
        depth = 0
        p = self.parent
        while p:
            depth += 1
            p = p.parent
        levels = ['annual', 'quarter', 'month', 'week', 'day']
        return levels[min(depth, len(levels) - 1)]

    def __repr__(self):
        return f"<Goal {self.id}: {self.title} [{self.level()}]>"