# app/routes.py
from flask import Blueprint, render_template, request, jsonify, abort, url_for, flash, redirect
from . import db
from .models import Goal
from .forms import GoalForm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import Calendar, SUNDAY

bp = Blueprint('main', __name__)

# GLOBAL TODAY FOR NAVBAR
today = datetime.now().date()
today_quarter = ((today.month - 1) // 3) + 1


# REUSABLE: GROUP GOALS BY STATUS
def group_goals_by_status(goals):
    grouped = {
        'todo': [],
        'in_progress': [],
        'blocked': [],
        'done': []
    }
    for goal in goals:
        status = getattr(goal, 'status', 'todo')
        if status not in grouped:
            status = 'todo'
        grouped[status].append(goal)
    return grouped


@bp.route('/')
def index():
    return render_template('index.html', title="WFM Planner", today=today, today_quarter=today_quarter)


# app/routes.py — UPDATE goals() route
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
        flash('Goal created successfully!', 'success')
        return redirect(url_for('main.goals'))

    # FETCH + SORT: oldest to newest, with children
    goals = Goal.query.filter_by(parent_id=None).options(
        db.joinedload(Goal.children)
    ).order_by(Goal.due_date.asc(), Goal.id).all()

    # SORT CHILDREN RECURSIVELY
    def sort_children(goal):
        if goal.children:
            goal.children.sort(key=lambda x: (x.due_date or datetime.max.date(), x.id))
            for child in goal.children:
                sort_children(child)

    for goal in goals:
        sort_children(goal)

    return render_template('goals.html', goals=goals, form=form, today=today, today_quarter=today_quarter)


@bp.route('/year/<int:year>')
def year_page(year):
    if year < 2000 or year > 2100:
        abort(404)

    y_start = datetime(year, 1, 1).date()
    y_end = datetime(year, 12, 31).date()

    annual_goals = Goal.query.filter(
        db.or_(
            Goal.type == 'annual',
            db.and_(
                Goal.due_date >= y_start,
                Goal.due_date <= y_end
            ),
            Goal.due_date.is_(None)
        ),
        Goal.parent_id.is_(None)
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

    annual_goals_grouped = group_goals_by_status(annual_goals)

    return render_template(
        'year.html',
        year=year,
        annual_goals_grouped=annual_goals_grouped,
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
        Goal.type == 'quarterly',
        Goal.due_date >= q_start,
        Goal.due_date <= q_end,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date).all()

    prev_year = year - 1 if q_num == 1 else year
    prev_q = 4 if q_num == 1 else q_num - 1
    next_year = year + 1 if q_num == 4 else year
    next_q = 1 if q_num == 4 else q_num + 1
    
    # Build months for calendar
    months = []
    for m in range(start_month, start_month + 3):
        m_date = datetime(year, m, 1).date()
        months.append({
            'num': m,
            'name': m_date.strftime('%B'),
            'url': f"/month/{year}/{m}"
        })
    
    quarterly_goals_grouped = group_goals_by_status(quarterly_goals)

    return render_template(
        'quarter.html',
        year=year,
        q_num=q_num,
        title=f"{year} Q{q_num}",
        q_start=q_start,
        q_end=q_end,
        quarterly_goals_grouped=quarterly_goals_grouped,
        prev_url=f"/quarter/{prev_year}/Q{prev_q}",
        next_url=f"/quarter/{next_year}/Q{next_q}",
        months=months,
        today=today,
        today_quarter=today_quarter
    )


@bp.route('/month/<int:year>/<int:month>')
def month_page(year, month):
    if month < 1 or month > 12:
        abort(404)

    m_start = datetime(year, month, 1).date()
    if month == 12:
        m_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        m_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

    monthly_goals = Goal.query.filter(
        Goal.type == 'monthly',
        Goal.due_date >= m_start,
        Goal.due_date <= m_end,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date).all()

    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1

    # SUNDAY-FIRST CALENDAR
    cal = Calendar(firstweekday=SUNDAY)
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                day_date = datetime(year, month, day).date()
                week_data.append({
                    'day': day,
                    'url': f"/day/{year}/{month}/{day:02d}"
                })
        sample_day = next((d for d in week if d != 0), 1)
        iso_week = datetime(year, month, sample_day).isocalendar()[1]
        weeks.append({
            'week_num': iso_week,
            'week_url': f"/week/{year}/{iso_week}",
            'days': week_data
        })

    monthly_goals_grouped = group_goals_by_status(monthly_goals)

    return render_template(
        'month.html',
        year=year,
        month=month,
        title=f"{m_start.strftime('%B %Y')}",
        m_start=m_start,
        m_end=m_end,
        monthly_goals_grouped=monthly_goals_grouped,
        prev_url=f"/month/{prev_year}/{prev_month}",
        next_url=f"/month/{next_year}/{next_month}",
        weeks=weeks,
        today=today,
        today_quarter=today_quarter
    )


@bp.route('/week/<int:year>/<int:week>')
def week_page(year, week):
    if week < 1 or week > 53:
        abort(404)

    try:
        w_start = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
    except ValueError:
        abort(404)
    w_end = w_start + timedelta(days=6)

    weekly_goals = Goal.query.filter(
        Goal.type == 'weekly',
        Goal.due_date >= w_start,
        Goal.due_date <= w_end,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date).all()

    # Build 7-day calendar (Sun-Sat)
    days = []
    current = w_start
    for i in range(7):
        day_date = current + timedelta(days=i)
        days.append({
            'day': day_date.day,
            'date': day_date,
            'url': f"/day/{day_date.year}/{day_date.month}/{day_date.day:02d}"
        })

    weeks = [{
        'week_num': week,
        'week_url': url_for('main.week_page', year=year, week=week),
        'days': days
    }]

    sample_month = w_start.month
    month_name = w_start.strftime('%B')

    prev_week = week - 1
    prev_year = year
    if prev_week == 0:
        prev_week = 52
        prev_year -= 1
    next_week = week + 1
    next_year = year
    if next_week > 52:
        next_week = 1
        next_year += 1

    weekly_goals_grouped = group_goals_by_status(weekly_goals)

    return render_template(
        'week.html',
        year=year,
        week=week,
        title=f"Week {week}: {w_start.strftime('%b %d')} - {w_end.strftime('%b %d, %Y')}",
        w_start=w_start,
        w_end=w_end,
        weekly_goals_grouped=weekly_goals_grouped,
        weeks=weeks,
        sample_month=sample_month,
        month_name=month_name,
        prev_url=f"/week/{prev_year}/{prev_week}",
        next_url=f"/week/{next_year}/{next_week}",
        today=today,
        today_quarter=today_quarter
    )


@bp.route('/day/<int:year>/<int:month>/<int:day>')
def day_page(year, month, day):
    try:
        day_date = datetime(year, month, day).date()
    except ValueError:
        abort(404)

    daily_goals = Goal.query.filter(
        Goal.type == 'daily',
        Goal.due_date == day_date,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date).all()

    prev_date = day_date - timedelta(days=1)
    next_date = day_date + timedelta(days=1)

    daily_goals_grouped = group_goals_by_status(daily_goals)

    return render_template(
        'day.html',
        day_date=day_date,
        title=day_date.strftime('%A, %B %d, %Y'),
        daily_goals_grouped=daily_goals_grouped,
        prev_url=f"/day/{prev_date.year}/{prev_date.month}/{prev_date.day}",
        next_url=f"/day/{next_date.year}/{next_date.month}/{next_date.day}",
        today=today,
        today_quarter=today_quarter
    )


# API: UPDATE GOAL STATUS
@bp.route('/api/goal/<int:goal_id>/status', methods=['POST'])
def update_goal_status(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    if data.get('status') in ['todo', 'in_progress', 'blocked', 'done']:
        goal.status = data['status']
        db.session.commit()
    return jsonify({'status': 'success'})


# ADD SUB-GOAL
# app/routes.py — add_subgoal
@bp.route('/api/goal/<int:parent_id>/subgoal', methods=['POST'])
def add_subgoal(parent_id):
    parent = Goal.query.get_or_404(parent_id)
    data = request.json

    # Use provided type (from JS)
    goal_type = data.get('type', 'daily')

    due_date = None
    if data.get('due_date'):
        try:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        except:
            pass

    subgoal = Goal(
        title=data['title'],
        type=goal_type,
        description=data.get('description', ''),
        motivation=data.get('motivation', ''),
        due_date=due_date,
        parent_id=parent_id
    )
    db.session.add(subgoal)
    db.session.commit()
    return jsonify({'status': 'success'})


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
    # Delete all children recursively
    def delete_children(g):
        for child in g.children:
            delete_children(child)
            db.session.delete(child)
        db.session.delete(g)
    
    delete_children(goal)
    db.session.commit()
    return jsonify({'status': 'success'})


# EDIT GOAL
@bp.route('/api/goal/<int:goal_id>', methods=['PUT'])
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    goal.title = data.get('title', goal.title)
    goal.type = data.get('type', goal.type)
    goal.description = data.get('description', goal.description)
    goal.motivation = data.get('motivation', goal.motivation)
    if 'due_date' in data:
        try:
            goal.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None
        except:
            goal.due_date = None
    db.session.commit()
    return jsonify({'status': 'success'})

@bp.route('/api/goal/<int:goal_id>/reparent', methods=['POST'])
def reparent_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    goal.parent_id = data.get('parent_id')
    db.session.commit()
    return jsonify({'status': 'success'})