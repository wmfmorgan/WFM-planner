# app/models.py
from datetime import datetime, date, timedelta
from collections import defaultdict
from . import db  # Import the shared db from __init__.py

# === HELPER FUNCTIONS FOR STEP TYPE & HIERARCHY ===
def get_step_type(due_date):
    """Detect step type based on due_date"""
    if not due_date:
        return 'day'
    dt = due_date
    # Quarter: 1st of Jan, Apr, Jul, Oct
    if dt.day == 1 and dt.month in [1, 4, 7, 10]:
        return 'quarter'
    # Month: 1st of any month
    elif dt.day == 1:
        return 'month'
    # Week: Any Monday
    elif dt.weekday() == 0:
        return 'week'
    # Default
    else:
        return 'day'

def quarter_key(d):
    """Return first day of the quarter"""
    return date(d.year, ((d.month - 1) // 3) * 3 + 1, 1)

def month_key(d):
    """Return first day of the month"""
    return date(d.year, d.month, 1)

def week_key(d):
    """Return Monday of the week"""
    return d - timedelta(days=d.weekday())

# === GOAL MODEL ===
class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    motivation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    steps = db.relationship('Step', backref='goal', lazy=True, cascade='all, delete-orphan')

    # === PROGRESS OVERALL ===
    def progress(self):
        total = len(self.steps)
        if total == 0:
            return 0
        completed = len([s for s in self.steps if s.completed])
        return int((completed / total) * 100)

    # === PROGRESS BY TYPE ===
    def progress_by_type(self, step_type):
        steps = [s for s in self.steps if s.step_type == step_type]
        if not steps:
            return 0
        completed = len([s for s in steps if s.completed])
        return int((completed / len(steps)) * 100)

    # === NESTED HIERARCHY: Q → M → W → D ===
    def nested_steps(self):
        steps = [s for s in self.steps if s.due_date]
        steps.sort(key=lambda s: s.due_date)

        hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for step in steps:
            q = quarter_key(step.due_date)
            m = month_key(step.due_date)
            w = week_key(step.due_date)
            hierarchy[q][m][w].append(step)

        return hierarchy


# === STEP MODEL ===
class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.Date)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=False)

    # Auto-computed step type
    _type = db.Column(db.String(20), default='day')

    # === CUSTOM SAVE WITH TYPE DETECTION ===
    def save(self):
        if self.due_date:
            self._type = get_step_type(self.due_date)
        else:
            self._type = 'day'
        db.session.add(self)
        db.session.commit()

    # === READABLE PROPERTY ===
    @property
    def step_type(self):
        return self._type