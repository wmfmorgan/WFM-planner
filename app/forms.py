# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms import StringField, SelectField, TextAreaField, DateField, SubmitField  # ← ADDED DateField!
from wtforms.validators import DataRequired

GOAL_TYPES = [
    ('Work', 'Work'), ('Marital', 'Marital'), ('Family', 'Family'),
    ('Physical', 'Physical'), ('Mental', 'Mental'), ('Hobby', 'Hobby'),
    ('Social', 'Social'), ('Financial', 'Financial')
]

# SMART EXAMPLE TEXT
SMART_EXAMPLE = (
    "Specific, Measurable, Achievable, Relevant, Time-Bound: "
    "By the end of 2025, I want to set my retirement savings to IRS annual limits ($23,000) "
    "in increments of 5% each quarter so I hit the max by the end of 2025, "
    "so that I have a comfortable retirement."
)

class GoalForm(FlaskForm):
    title = StringField('Goal Title', validators=[DataRequired()])
    type = SelectField('Goal Type', choices=[
        ('annual', 'Annual'),
        ('quarter', 'Quarter'),
        ('month', 'Month'),
        ('week', 'Week'),
        ('day', 'Day')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    motivation = TextAreaField('Motivation')
    due_date = DateField('Due Date (Optional)', format='%Y-%m-%d')  # ← NOW WORKS!
    submit = SubmitField('Create Goal')