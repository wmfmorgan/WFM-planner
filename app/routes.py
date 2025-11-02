# app/routes.py
from flask import Blueprint, render_template, request, jsonify
from . import db  # Import from __init__.py
from .models import Goal, Step
from .forms import GoalForm

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

# app/routes.py
from datetime import datetime
from .models import Step

@bp.route('/api/goal/<int:goal_id>/step', methods=['POST'])
def add_step(goal_id):
    data = request.json
    title = data['title']
    due_date_str = data.get('due_date')
    user_type = data.get('step_type', 'day')  # ← User override

    # Convert date string
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date'}), 400

    # === FINAL TYPE: User override wins ===
    final_type = user_type if user_type != 'auto' else 'day'
    if due_date and user_type == 'auto':
        final_type = get_step_type(due_date)  # Auto-detect

    step = Step(
        title=title,
        due_date=due_date,
        goal_id=goal_id,
        _type=final_type  # ← Set directly
    )
    db.session.add(step)
    db.session.commit()

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