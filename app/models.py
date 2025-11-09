# app/models.py
from datetime import datetime, date
from . import db

# app/models.py
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(20), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    quarter = db.Column(db.Integer)
    month = db.Column(db.Integer)
    week = db.Column(db.Integer)
    day = db.Column(db.Integer)
    time = db.Column(db.String(5))  # "14:00" — ADD THIS
    index = db.Column(db.Integer)  # Task index — ADD THIS
    type = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.UniqueConstraint('scope', 'year', 'quarter', 'month', 'week', 'day', 'time', 'index', 'type', name='uix_note'),
    )

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), default='annual')  # e.g., Annual, Q1, Jan, etc.
    description = db.Column(db.Text, nullable=False)
    motivation = db.Column(db.Text)
    due_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=True)
    status = db.Column(db.String(20), default='todo', nullable=False, server_default='todo')  # 'todo', 'in_progress', 'blocked', 'done'
    category = db.Column(db.String(20))
    
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
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'category': self.category,
            'description': self.description,
            'motivation': self.motivation,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'completed': self.completed,
            'parent_id': self.parent_id
        }


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)  # NULL = all day
    end_time = db.Column(db.Time)    # NULL = all day
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_rule = db.Column(db.String(50))  # 'daily', 'weekly', 'monthly'
    all_day = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Event {self.title}>"