# app/routes.py
from flask import Blueprint, render_template, request, jsonify, abort
from . import db
from .models import Goal
from .forms import GoalForm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

bp = Blueprint('main', __name__)

# GLOBAL TODAY FOR NAVBAR
today = datetime.now().date()
today_quarter = ((today.month - 1) // 3) + 1


@bp.route('/')
def index():
    return render_template('index.html', title="WFM Planner", today=today, today_quarter=today_quarter)


@bp.route('/goals', methods=['GET', 'POST'])
def goals():
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(
            title=form.title.data,
            type=form.type.data,
            description=form.description.data,
            motivation=form.motivation.data,
            due_date=form.due_date.data
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({'status': 'success', 'goal_id': goal.id})

    goals = Goal.query.filter_by(parent_id=None).all()
    return render_template('goals.html', goals=goals, form=form, today=today, today_quarter=today_quarter)


@bp.route('/year/<int:year>')
def year_page(year):
    if year < 2000 or year > 2100:
        abort(404)

    y_start = datetime(year, 1, 1).date()
    y_end = datetime(year, 12, 31).date()

    annual_goals = Goal.query.filter(
        Goal.parent_id.is_(None),
        (
            (Goal.due_date >= y_start) &
            (Goal.due_date <= y_end)
            | (Goal.due_date.is_(None))
        )
    ).order_by(Goal.due_date.asc(), Goal.id).all()

    quarters = []
    for q in range(1, 5):
        q_start = datetime(year, (q-1)*3 + 1, 1).date()
        q_end = q_start + relativedelta(months=3) - timedelta(days=1)
        quarters.append({
            'num': q,
            'start': q_start,
            'end': q_end,
            'url': f"/quarter/{year}/Q{q}"
        })

    prev_year = year - 1
    next_year = year + 1

    return render_template(
        'year.html',
        year=year,
        annual_goals=annual_goals,
        quarters=quarters,
        prev_url=f"/year/{prev_year}",
        next_url=f"/year/{next_year}",
        today=today,
        today_quarter=today_quarter
    )


@bp.route('/quarter/<int:year>/Q<int:q_num>')
def quarter_page(year, q_num):
    if q_num not in [1, 2, 3, 4]:
        abort(404)

    start_month = (q_num - 1) * 3 + 1
    q_start = datetime(year, start_month, 1).date()
    q_end = q_start + relativedelta(months=3) - timedelta(days=1)

    quarterly_goals = Goal.query.filter(
        Goal.due_date >= q_start,
        Goal.due_date <= q_end,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date).all()

    prev_year = year - 1 if q_num == 1 else year
    prev_q = 4 if q_num == 1 else q_num - 1
    next_year = year + 1 if q_num == 4 else year
    next_q = 1 if q_num == 4 else q_num + 1

    return render_template(
        'quarter.html',
        year=year,
        q_num=q_num,
        title=f"{year} Q{q_num}",
        q_start=q_start,
        q_end=q_end,
        quarterly_goals=quarterly_goals,
        prev_url=f"/quarter/{prev_year}/Q{prev_q}",
        next_url=f"/quarter/{next_year}/Q{next_q}",
        today=today,
        today_quarter=today_quarter
    )


# ADD SUB-GOAL
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


# DELETE GOAL
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
    else:
        goal.due_date = None
    db.session.commit()
    return jsonify({'status': 'success'})