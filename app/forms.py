# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

GOAL_TYPES = [
    ('Work', 'Work'), ('Marital', 'Marital'), ('Family', 'Family'),
    ('Physical', 'Physical'), ('Mental', 'Mental'), ('Hobby', 'Hobby'),
    ('Social', 'Social'), ('Financial', 'Financial')
]

class GoalForm(FlaskForm):
    title = StringField('Goal Title', validators=[DataRequired()])
    type = SelectField('Goal Type', choices=GOAL_TYPES, validators=[DataRequired()])
    description = TextAreaField('Goal Description', validators=[DataRequired()])
    motivation = TextAreaField('Goal Motivation')
    submit = SubmitField('Save Goal')