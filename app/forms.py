# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DateField, BooleanField, SubmitField  # ← ADDED DateField!
from wtforms.validators import DataRequired

GOAL_CATEGORY = [
    ('Work', 'Work'), ('Marital', 'Marital'), ('Family', 'Family'),
    ('Physical', 'Physical'), ('Mental', 'Mental'), ('Hobby', 'Hobby'),
    ('Social', 'Social'), ('Financial', 'Financial')
]

class GoalForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    type = SelectField('Type', choices=[
        ('annual', 'Annual'), ('quarterly', 'Quarterly'), 
        ('monthly', 'Monthly'), ('weekly', 'Weekly'), ('daily', 'Daily')
    ], validators=[DataRequired()], default='annual')
    category = SelectField('Category', choices=GOAL_CATEGORY)
    description = TextAreaField('Description')
    motivation = TextAreaField('Motivation')
    due_date = DateField('Due Date', format='%Y-%m-%d')
    status = SelectField('Status', choices=[
        ('todo', 'To Do'), ('in_progress', 'In Progress'), 
        ('blocked', 'Blocked'), ('done', 'Done')
    ], default='todo')
    completed = BooleanField('Completed')
    submit = SubmitField('Save Goal')