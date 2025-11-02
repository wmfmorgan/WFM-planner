# app/routes.py
from flask import Blueprint, render_template, request, jsonify
from . import db
from .models import Goal
from .forms import GoalForm
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html', title="WFM Planner")

@bp.route('/goals', methods=['GET', 'POST'])
def goals():
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(
            title=form.title.data,
            type=form.type.data,
            description=form.description.data,
            motivation=form.motivation.data
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({'status': 'success', 'goal_id': goal.id})

    goals = Goal.query.filter_by(parent_id=None).all()  # Root goals only
    return render_template('goals.html', goals=goals, form=form)

# ADD SUB-GOAL (STEP = GOAL)
@bp.route('/api/goal/<int:parent_id>/subgoal', methods=['POST'])
def add_subgoal(parent_id):
    parent = Goal.query.get_or_404(parent_id)
    data = request.json

    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date'}), 400

    subgoal = Goal(
        title=data['title'],
        type=data.get('type', 'task'),
        description=data.get('description', ''),
        motivation=data.get('motivation', ''),
        due_date=due_date,
        parent_id=parent_id
    )
    db.session.add(subgoal)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'goal_id': subgoal.id,
        'level': subgoal.level()
    })

# TOGGLE COMPLETION
@bp.route('/api/goal/<int:goal_id>/toggle', methods=['POST'])
def toggle_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    goal.completed = not goal.completed
    db.session.commit()
    return jsonify({
        'status': 'success',
        'completed': goal.completed,
        'progress': goal.progress()
    })

# DELETE GOAL (AND ALL CHILDREN)
@bp.route('/api/goal/<int:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'status': 'success'})

# EDIT GOAL
@bp.route('/api/goal/<int:goal_id>', methods=['PUT'])
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    goal.title = data.get('title', goal.title)
    goal.description = data.get('description', goal.description)
    goal.motivation = data.get('motivation', goal.motivation)
    if data.get('due_date'):
        try:
            goal.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        except:
            goal.due_date = None
    db.session.commit()
    return jsonify({'status': 'success'})