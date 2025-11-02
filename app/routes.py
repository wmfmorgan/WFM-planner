# app/routes.py
from flask import Blueprint, render_template, request, jsonify
from . import db
from .models import Goal, Step
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
    goals = Goal.query.all()
    return render_template('goals.html', goals=goals, form=form)

@bp.route('/api/goal/<int:goal_id>/step', methods=['POST'])
def add_step(goal_id):
    data = request.json
    title = data.get('title')
    due_date_str = data.get('due_date')
    step_type = data.get('step_type', 'auto')

    if not title:
        return jsonify({'status': 'error', 'message': 'Title required'}), 400

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date'}), 400

    step = Step(title=title, due_date=due_date, goal_id=goal_id)
    if step_type != 'auto':
        step._type = step_type
    step.save()

    return jsonify({
        'status': 'success',
        'step_id': step.id,
        'step_type': step.step_type
    })

@bp.route('/api/step/<int:step_id>/toggle', methods=['POST'])
def toggle_step(step_id):
    step = Step.query.get_or_404(step_id)
    step.completed = not step.completed
    db.session.commit()
    return jsonify({
        'status': 'success',
        'completed': step.completed,
        'progress': step.goal.progress()
    })


# app/routes.py — ADD THESE ROUTES

@bp.route('/api/goal/<int:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Goal deleted'})

@bp.route('/api/goal/<int:goal_id>', methods=['PUT'])
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    goal.title = data.get('title', goal.title)
    goal.type = data.get('type', goal.type)
    goal.description = data.get('description', goal.description)
    goal.motivation = data.get('motivation', goal.motivation)
    db.session.commit()
    return jsonify({'status': 'success'})

# app/routes.py
@bp.route('/api/step/<int:step_id>', methods=['DELETE'])
def delete_step(step_id):
    step = Step.query.get_or_404(step_id)
    db.session.delete(step)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Step deleted'}), 200

@bp.route('/api/step/<int:step_id>', methods=['PUT'])
def edit_step(step_id):
    step = Step.query.get_or_404(step_id)
    data = request.json
    step.title = data.get('title', step.title)
    due_date_str = data.get('due_date')
    step_type = data.get('step_type', 'auto')

    if due_date_str:
        try:
            step.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except:
            step.due_date = None
    else:
        step.due_date = None

    if step_type != 'auto':
        step._type = step_type
    else:
        step._type = get_step_type(step.due_date) if step.due_date else 'day'

    db.session.commit()
    return jsonify({
        'status': 'success',
        'step_type': step.step_type
    })