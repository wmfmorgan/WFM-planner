# app/routes.py
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, abort, url_for, flash, redirect, Response
from . import db
from .models import Goal, Note, Event
from .models import Task, TaskStatus
from .forms import GoalForm
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from calendar import Calendar, SUNDAY, setfirstweekday
from sqlalchemy import case
from sqlalchemy import and_, or_
import calendar
from calendar import monthcalendar, month_name
import shutil
import os
from flask import current_app
import json
from sqlalchemy import case as db_case

# Force Sunday as the first day of the week globally
calendar.setfirstweekday(calendar.SUNDAY)

bp = Blueprint('main', __name__)

@bp.before_request
def require_auth():
    auth = request.authorization
    #print(f"→ AUTH CHECK: {request.method} {request.path}")
    password = os.getenv("WFM_PASSWORD")
    if not (auth and auth.username == "admin" and auth.password == password):
        return ("Unauthorized", 401, {'WWW-Authenticate': 'Basic realm="WFM Planner"'})

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


# POST: Create goal via JSON
@bp.route('/goals', methods=['POST'])
def create_goal():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    form = GoalForm(data=data)  # Validate JSON as dict

    # FORCE DEFAULT IF BLANK
    if not form.type.data:
        form.type.data = 'annual'
    
    if not form.validate():
        return jsonify({'errors': form.errors}), 400

    # HANDLE parent_id: str → int/None
    parent_id = data.get('parent_id')
    if parent_id == '':
        parent_id = None
    else:
        parent_id = int(parent_id) if parent_id else None

    # HANDLE due_date: str → date
    due_date = None
    if form.due_date.data:
        try:
            due_date = form.due_date.data
        except ValueError:
            return jsonify({'error': 'Invalid due date format'}), 400

    # CREATE GOAL
    goal = Goal(
        title=form.title.data,
        type=form.type.data or 'annual',
        category=form.category.data,
        description=form.description.data,
        motivation=form.motivation.data,
        due_date=due_date,
        status=form.status.data,
        completed=form.completed.data,
        parent_id=parent_id
    )

    db.session.add(goal)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Goal saved!',
        'goal': goal.to_dict()  # Assuming Goal has to_dict() from ExportableMixin
    }), 200


@bp.route('/api/goals/<int:goal_id>', methods=['GET'])
def get_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    #print(jsonify(goal.to_dict()))
    return jsonify(goal.to_dict())

# GET: Render goals page
@bp.route('/goals', methods=['GET'])
def get_goals():
    # === GET: LOAD TOP-LEVEL GOALS ===
    goals = Goal.query.filter(
        Goal.parent_id.is_(None)
    ).options(
        db.joinedload(Goal.children)
    ).order_by(
        case((Goal.due_date.is_(None), 0), else_=1),
        Goal.due_date.asc(),
        Goal.id
    ).order_by(Goal.rank.asc(), Goal.id.asc()).all()

    # SORT CHILDREN RECURSIVELY
    def sort_children(goal):
        if goal.children:
            goal.children.sort(key=lambda x: (x.due_date or datetime.max.date(), x.id))
            for child in goal.children:
                sort_children(child)

    for goal in goals:
        sort_children(goal)

    form = GoalForm()  # For template if needed

    return render_template(
        'goals.html',
        goals=goals,
        form=form,
        today=today,
        today_quarter=today_quarter
    )


@bp.route('/year/<int:year>')
def year_page(year):
    if year < 2000 or year > 2100:
            abort(404)

    y_start = datetime(year, 1, 1).date()
    y_end = datetime(year, 12, 31).date()

    parent_id = request.args.get('parent_id', '').strip()
    if parent_id:
        try:
            parent_id = int(parent_id)
        except ValueError:
            parent_id = None
    else:
        parent_id = None

    annual_goals = Goal.query.filter(
        Goal.type == 'annual',
        or_(
            and_(Goal.due_date >= y_start, Goal.due_date <= y_end),
            Goal.due_date.is_(None)
        ),
        or_(Goal.parent_id.is_(None), Goal.parent_id == parent_id)
    ).order_by(
        case((Goal.due_date.is_(None), 0), else_=1),
        Goal.due_date.asc(),
        Goal.id
    ).order_by(Goal.rank.asc(), Goal.id.asc()).all()

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
    form = GoalForm()

    return render_template(
        'year.html',
        year=year,
        annual_goals_grouped=annual_goals_grouped,
        quarters=quarters,
        prev_url=f"/year/{prev_year}",
        next_url=f"/year/{next_year}",
        today=today,
        page_type='year',
        parent_type='year',
        form=form,
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
    ).order_by(Goal.due_date.asc(), Goal.rank.asc(), Goal.id).all()

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
  
    w_start = datetime(year,1,1).date()
    w_end = datetime(year,12,31).date()
    possible_parents = Goal.query.filter(
        Goal.type == 'annual',
        Goal.due_date >= w_start,
        Goal.due_date <= w_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).order_by(Goal.rank.asc(), Goal.id.asc()).all() 

    form = GoalForm()
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
        page_type='quarter',
        parent_type='annual',
        form=form,
        possible_parents=possible_parents,
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
    ).order_by(Goal.due_date.asc(), Goal.rank.asc(), Goal.id).all()

    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1

    # --- SUNDAY-FIRST CALENDAR WITH 100% CORRECT ISO WEEK NUMBERS ---
    calendar_with_weeks = []

    # Force Sunday as first day of week globally
    calendar.setfirstweekday(calendar.SUNDAY)

    # Use the module function — this works and respects setfirstweekday
    for week in calendar.monthcalendar(year, month):
        sunday_day = week[0]  # First element is now Sunday

        if sunday_day != 0:
            sun_date = date(year, month, sunday_day)
        else:
            first_of_month = date(year, month, 1)
            days_back = (first_of_month.weekday() + 1) % 7
            sun_date = first_of_month - timedelta(days=days_back)

        monday = sun_date + timedelta(days=1)
        iso_week = monday.isocalendar()[1]
        calendar_with_weeks.append((iso_week, week))

    monthly_goals_grouped = group_goals_by_status(monthly_goals)

    q_start, q_end = quarter_range(year, month)
    possible_parents = Goal.query.filter(
        Goal.type == 'quarterly',
        Goal.due_date >= q_start,
        Goal.due_date <= q_end,
        Goal.completed == False
    ).order_by(Goal.rank.asc(), Goal.id.asc()).all() 
 
    month_name = date(year, month, 1).strftime('%B')

    def events_on_date(y, m, d):
        d = datetime(y, m, d).date()
        return Event.query.filter(
            Event.start_date <= d,
            Event.end_date >= d
        ).order_by(Event.all_day.desc(), Event.start_time.asc()).all()

    form = GoalForm()
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
        today=today,
        page_type='month',
        parent_type='quarterly',
        form=form,
        possible_parents=possible_parents,
        today_quarter=today_quarter,
        events_on_date=events_on_date,
        calendar_with_weeks=calendar_with_weeks,
        month_name=month_name
    )


@bp.route('/week/<int:year>/<int:week>')
def week_page(year, week):
    setfirstweekday(SUNDAY)
    if week < 1 or week > 53:
        abort(404)

    try:
        # FIXED: Use %G (ISO year) + %V (ISO week) for true ISO Monday
        monday = datetime.strptime(f'{year}-W{week}-1', '%G-W%V-%w').date()
        # SUNDAY = Monday - 1 day
        w_start = monday - timedelta(days=1)
        w_end = w_start + timedelta(days=6)
    except ValueError:
        abort(404)

    w_end = w_start + timedelta(days=6)

    # PICK MONDAY FOR PARENT FILTER
    day_date = w_start
    actual_iso_week = (w_start + timedelta(days=1)).isocalendar()[1]  # Monday of this week

    m_start, m_end = month_range_from_week(year, week)

    possible_parents = Goal.query.filter(
        Goal.type == 'monthly',
        Goal.due_date >= m_start,
        Goal.due_date <= m_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).order_by(Goal.due_date.asc(), Goal.rank.asc(), Goal.id).all() 

    # GET WEEKLY GOALS
    weekly_goals = Goal.query.filter(
        Goal.type == 'weekly',
        or_(
            and_(Goal.due_date >= w_start, Goal.due_date <= w_end),
            Goal.due_date.is_(None)
        )
    ).order_by(
        db_case((Goal.due_date.is_(None), 0), else_=1),
        Goal.due_date.asc(),
        Goal.id
    ).order_by(Goal.rank.asc(), Goal.id.asc()).all()

    weekly_goals_grouped = group_goals_by_status(weekly_goals)
    
    
    # BUILD 7-DAY GRID (Sun-Sat)
    days = []
    current = w_start
    for i in range(7):
        day_date = current + timedelta(days=i)
        days.append(day_date)

    weeks = [{
        'week_num': week,
        'week_url': url_for('main.week_page', year=year, week=week),
        'days': days
    }]

    sample_month = w_start.month
    month_name = w_start.strftime('%B')

    # NAVIGATION
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

    form = GoalForm()
    # GET MONTH FROM FIRST DAY OF WEEK
    first_day = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w").date()
    month = first_day.month
    
    # GET 7 DAYS OF WEEK (SUNDAY START)
    # GET MONDAY OF ISO WEEK
    monday = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w").date()

    # SUNDAY = MONDAY - 1 DAY
    sunday = monday - timedelta(days=1)

    # BUILD 7 DAYS: SUN → SAT
    week_days = [sunday + timedelta(days=i) for i in range(7)]
    #week_days = [first_day + timedelta(days=i) for i in range(7)]

    # DEFINE events_on_date HELPER
    def events_on_date(year, month, day):
        date = datetime(year, month, day).date()
        return Event.query.filter(
            Event.start_date <= date,
            Event.end_date >= date
        ).order_by(
            Event.all_day.desc(),
            Event.start_time.asc()
        ).all()

    return render_template(
        'week.html',
        year=year,
        week=actual_iso_week,
        month=month,
        title=f"Week {actual_iso_week}: {w_start.strftime('%b %d')} - {w_end.strftime('%b %d, %Y')}",
        w_start=w_start,
        w_end=w_end,
        weekly_goals_grouped=weekly_goals_grouped,
        weeks=weeks,
        sample_month=sample_month,
        month_name=month_name,
        prev_url=f"/week/{prev_year}/{prev_week}",
        next_url=f"/week/{next_year}/{next_week}",
        parent_type='monthly',
        page_type='week',
        form=form,
        possible_parents=possible_parents,
        today=today,
        week_days=week_days,
        events_on_date=events_on_date,
        today_quarter=today_quarter
    )


@bp.route('/day/<int:year>/<int:month>/<int:day>')
def day_page(year, month, day):

    try:
        day_date = datetime(year, month, day).date()
    except ValueError:
        abort(404)

    try:
        target_date = date(year=year, month=month, day=day)
    except ValueError:
        flash('Invalid date!')  # Redirect if needed: return redirect(url_for('index'))
    # Or raise 404: abort(404)

    daily_goals = Goal.query.filter(
        Goal.type == 'daily',
        Goal.due_date == day_date,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date, Goal.rank.asc(), Goal.id.asc()).all()

    prev_date = day_date - timedelta(days=1)
    next_date = day_date + timedelta(days=1)

    daily_goals_grouped = group_goals_by_status(daily_goals)
    
    # GET POSSIBLE PARENTS (weekly goals in same week, NOT completed)
    #day_date = datetime(year, month, day).date()
    #w_start = day_date - timedelta(days=day_date.weekday())
    #w_end = w_start + timedelta(days=6)
    w_start, w_end = week_range(year, month, day)
    possible_parents = Goal.query.filter(
        Goal.type == 'weekly',
        Goal.due_date >= w_start,
        Goal.due_date <= w_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).order_by(Goal.due_date.asc(), Goal.id).all()

    def events_on_date(y, m, d):
        date = datetime(y, m, d).date()
        return Event.query.filter(
            Event.start_date <= date,
            Event.end_date >= date
        ).order_by(
            Event.all_day.desc(),
            Event.start_time.asc()
        ).all()
        

    # 2. Load tasks
    # TARGET DATE LOGIC
    is_today = target_date == date.today()
    is_past = target_date < date.today()
    is_future = target_date > date.today()

    # BUILD FILTER
    filters = []
    #print(target_date)
    if is_today:
        #print('is_today')
        # TODAY: Incomplete (any date) + Completed today
        filters.append(
            or_(
                # All incomplete tasks (any date)
                Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]),
                #exclude future todo
                and_(
                        Task.status == TaskStatus.TODO,
                        Task.date <= target_date
                    ),
                # Completed TODAY
                and_(Task.status == TaskStatus.DONE, Task.date == target_date)
            )
        )
    elif is_past:
        #print('is_past')
        # PAST: Only completed on THAT day
        filters.append(
            and_(Task.status == TaskStatus.DONE, Task.date == target_date)
        )
    elif is_future:
        #print('is_future')
        # FUTURE: Only tasks with exact date
        filters.append(Task.date == target_date)

    
    today_tasks = Task.query.filter(*filters).order_by(
        case(
            (Task.status != TaskStatus.DONE, 0),  # Incomplete first
            else_=1
        ),
        Task.id
    ).order_by(Task.rank.asc(), Task.id.asc()).all()

    # ——— BACKLOG TASKS (date = NULL + not done) ———
    backlog_tasks = Task.query.filter(
        #Task.date.is_(None),
        Task.status == TaskStatus.BACKLOG
    ).order_by(Task.rank.asc(), Task.id.asc()).all()

    #print(filter)
    #print(today_tasks)

    # 3. Group for the Kanban board
    kanban = {
        'todo':        [t for t in today_tasks if t.status == TaskStatus.TODO],
        'in_progress': [t for t in today_tasks if t.status == TaskStatus.IN_PROGRESS],
        'blocked':     [t for t in today_tasks if t.status == TaskStatus.BLOCKED],
        'done':        [t for t in today_tasks if t.status == TaskStatus.DONE],
    }

    form = GoalForm()
    return render_template(
        'day.html',
        day_date=day_date,
        year=day_date.year,   # ← ADD THESE
        month=day_date.month,
        day=day_date.day,
        title=day_date.strftime('%A, %B %d, %Y'),
        daily_goals_grouped=daily_goals_grouped,
        prev_url=f"/day/{prev_date.year}/{prev_date.month}/{prev_date.day}",
        next_url=f"/day/{next_date.year}/{next_date.month}/{next_date.day}",
        today=today,
        page_type='day',
        parent_type='weekly',
        form=form,
        possible_parents=possible_parents,
        #year=year,
        #month=month,
        #day=day,
        month_name=calendar.month_name[month],
        events_on_date=events_on_date,
        today_quarter=today_quarter,
        date=target_date,
        kanban=kanban,
        backlog_tasks=backlog_tasks
    )


# API: UPDATE GOAL STATUS
@bp.route('/api/goals/<int:goal_id>/status', methods=['POST'])
def update_goal_status(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    new_status = data.get('status')

    if new_status in ['todo', 'in_progress', 'blocked', 'done']:
        goal.status = new_status
        # SYNC completed WITH status
        goal.completed = (new_status == 'done')
        db.session.commit()
    return jsonify({'status': 'success'})


# ADD SUB-GOAL
# app/routes.py — add_subgoal
# app/routes.py — add_subgoal
@bp.route('/api/goals/<int:parent_id>/subgoal', methods=['POST'])
def add_subgoal(parent_id):
    #print("=== /api/goals/{parent_id}/subgoal DEBUG ===")
    #print("Parent ID:", parent_id)
    #print("JSON data:", request.json)
    data = request.json

    # ENSURE parent_id IS VALID
    if not Goal.query.get(parent_id):
        return jsonify({'error': 'Parent not found'}), 404

    goal = Goal(
        title=data['title'],
        type=data['type'],
        category=data.get('category'),
        description=data.get('description'),
        motivation=data.get('motivation'),
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data.get('due_date') else None,
        status=data.get('status', 'todo'),
        completed=data.get('completed', False),
        parent_id=parent_id  # ← ALREADY INT FROM URL
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Subgoal saved!',
        'goal': goal.to_dict()
    })


# TOGGLE COMPLETION
#@bp.route('/api/goals/<int:goal_id>/toggle', methods=['POST'])
#def toggle_goal(goal_id):
#    goal = Goal.query.get_or_404(goal_id)
#    goal.completed = not goal.completed
#    db.session.commit()
#    return jsonify({
#        'status': 'success',
#        'completed': goal.completed,
#        'progress': goal.progress()
#    })


# DELETE GOAL
@bp.route('/api/goals/<int:goal_id>', methods=['DELETE'])
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
@bp.route('/api/goals/<int:goal_id>', methods=['PUT'])
def edit_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    goal.title = data.get('title', goal.title)
    goal.type = data.get('type', goal.type)
    goal.description = data.get('description', goal.description)
    goal.motivation = data.get('motivation', goal.motivation)
    goal.category = data.get('category', goal.category)
    if 'due_date' in data:
        try:
            goal.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None
        except:
            goal.due_date = None
    db.session.commit()
    return jsonify({
        "success": True,
        "goal": goal.to_dict()  # Make sure you have a .to_dict() method on Goal model
    }), 200

@bp.route('/api/note/<path:key>', methods=['GET', 'POST'])
def api_note(key):
    parts = key.split('-')
    if len(parts) < 4 or parts[0] != 'note':
        abort(400)
    #print(key)
    scope = parts[1]
    type_ = parts[-1]
    year = None
    quarter = None
    month = None
    week = None
    day = None
    
    time = None
    index = None

    i = 2
    if i < len(parts) and parts[i].isdigit():
        year = int(parts[i])
        i += 1

    if scope == 'quarter' and i < len(parts) and parts[i].isdigit():
        quarter = int(parts[i])
        i += 1

    #if scope in ['month', 'quarter', 'week', 'day'] and i < len(parts) and parts[i].isdigit():
    if scope in ['month', 'day'] and i < len(parts) and parts[i].isdigit():
        month = int(parts[i])
        i += 1

    if scope == 'week' and i < len(parts) and parts[i].isdigit():
        week = int(parts[i])
        i += 1

    if scope == 'day' and i < len(parts) and parts[i].isdigit():
        day = int(parts[i])
        i += 1

    i += 1 #skip the type

    if scope == 'day' and i < len(parts) and ':' in parts[i] and len(parts[i]) == 5:
        time = parts[i]
        i += 1

    if scope == 'day' and i < len(parts) and parts[i].isdigit():
        index = int(parts[i])
        i += 1

    if year is None:
        abort(400)

    filters = {
        'scope': scope,
        'year': year,
        'quarter': quarter,
        'month': month,
        'week': week,
        'day': day,
        'type': type_,
        'time': time,
        'index': index,
        }
    #print(filters)
    filters = {k: v for k, v in filters.items() if v is not None}

    if request.method == 'GET':
        note = Note.query.filter_by(**filters).first()
        return jsonify({
            'content': note.content if note else '',
            'completed': note.completed if note else False
    })

    if request.method == 'POST':
        data = request.json
        content = data.get('content', '')
        completed = data.get('completed', False)

        note = Note.query.filter_by(**filters).first()
        if not note:
            note = Note(**filters, completed=completed)
            db.session.add(note)
        else:
            if 'content' in data:
                note.content = content
            if 'completed' in data:
                note.completed = completed
        db.session.commit()
        return jsonify({'status': 'saved'})
    

@bp.route('/api/event', methods=['POST'])
def api_create_event():
    data = request.json
    event = Event(
        title=data['title'],
        start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
        start_time=datetime.strptime(data['start_time'], '%H:%M').time() if data['start_time'] else None,
        end_time=datetime.strptime(data['end_time'], '%H:%M').time() if data['end_time'] else None,
        all_day=data['all_day'],
        is_recurring=data['is_recurring'],
        recurrence_rule=data['recurrence_rule']
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'status': 'success'})

@bp.route('/api/event/<int:event_id>', methods=['GET', 'DELETE'])
def api_event(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'GET':
        return jsonify({
            'id': event.id,
            'title': event.title,
            'start_date': event.start_date.isoformat(),
            'end_date': event.end_date.isoformat(),
            'start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
            'end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
            'all_day': event.all_day,
            'is_recurring': event.is_recurring,
            'recurrence_rule': event.recurrence_rule
        })
    elif request.method == 'DELETE':
        db.session.delete(event)
        db.session.commit()
        return jsonify({'status': 'deleted'})
    

@bp.route('/api/event/<int:event_id>', methods=['PUT'])
def api_update_event(event_id):
    """
    Update an existing event.
    Expects JSON with any of: title, start_date, end_date, start_time, end_time,
    all_day, is_recurring, recurrence_rule
    """
    event = Event.query.get_or_404(event_id)
    data = request.get_json()

    # Update only provided fields
    if 'title' in data:
        event.title = data['title']
    if 'start_date' in data:
        event.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if 'end_date' in data:
        event.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    if 'start_time' in data:
        event.start_time = datetime.strptime(data['start_time'], '%H:%M').time() if data['start_time'] else None
    if 'end_time' in data:
        event.end_time = datetime.strptime(data['end_time'], '%H:%M').time() if data['end_time'] else None
    if 'all_day' in data:
        event.all_day = data['all_day']
    if 'is_recurring' in data:
        event.is_recurring = data['is_recurring']
    if 'recurrence_rule' in data:
        event.recurrence_rule = data['recurrence_rule'] if data.get('is_recurring') else None

    db.session.commit()
    return jsonify({
        'status': 'updated',
        'event': {
            'id': event.id,
            'title': event.title,
            'start_date': event.start_date.isoformat(),
            'end_date': event.end_date.isoformat(),
            'start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
            'end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
            'all_day': event.all_day,
            'is_recurring': event.is_recurring,
            'recurrence_rule': event.recurrence_rule
        }
    })

@bp.route('/backup')
def backup_db():
    db_filename = 'wfm_planner.db'
    db_path = os.path.join(current_app.instance_path, db_filename)
    backup_dir = os.path.join(current_app.instance_path, 'backups')

    # 1. Ensure backup dir exists
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception as e:
        current_app.logger.error(f"Failed to create backup dir: {e}")
        flash("Failed to create backup directory", "danger")
        return redirect(url_for('main.index'))

    # 2. Validate DB exists
    if not os.path.exists(db_path):
        flash("Database file not found!", "danger")
        return redirect(url_for('main.index'))

    # 3. Prevent huge files
    try:
        db_size = os.path.getsize(db_path)
        if db_size > 100 * 1024 * 1024:  # 100MB
            flash("Database too large to backup (>100MB)", "danger")
            return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f"Failed to check DB size: {e}")
        flash("Failed to access database", "danger")
        return redirect(url_for('main.index'))

    # 4. Generate safe filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # 5. Copy with error handling
    try:
        shutil.copy2(db_path, backup_path)  # copy2 preserves metadata
        current_app.logger.info(f"Backup created: {backup_filename}")
        flash(f"Backup created: {backup_filename}", "success")
    except Exception as e:
        current_app.logger.error(f"Backup failed: {e}")
        flash("Backup failed. Check server logs.", "danger")

    return redirect(url_for('main.index'))

from flask import current_app
import shutil

@bp.route('/restore', methods=['GET', 'POST'])
def restore_db():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash("No file selected", "danger")
            return redirect(request.url)

        # 1. Validate filename
        if not file.filename.lower().endswith('.db'):
            flash("File must be a .db SQLite database", "danger")
            return redirect(request.url)

        # 2. Read & validate size
        try:
            file_data = file.read()
            if len(file_data) > 50 * 1024 * 1024:  # 50MB max
                flash("File too large (max 50MB)", "danger")
                return redirect(request.url)

            # 3. Basic SQLite header check
            if not file_data.startswith(b'SQLite format 3\x00'):
                flash("Not a valid SQLite database", "danger")
                return redirect(request.url)

            # 4. Save securely
            db_path = os.path.join(current_app.instance_path, 'wfm_planner.db')
            with open(db_path, 'wb') as f:
                f.write(file_data)

            flash("Database restored successfully!", "success")
            return redirect(url_for('main.index'))

        except Exception as e:
            current_app.logger.error(f"Restore failed: {e}")
            flash("Restore failed. Check server logs.", "danger")
            return redirect(request.url)

    # === GET: List backups ===
    backup_dir = os.path.join(current_app.instance_path, 'backups')
    try:
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
            backups = []
        else:
            backups = [
                f for f in os.listdir(backup_dir)
                if f.endswith('.db') and os.path.isfile(os.path.join(backup_dir, f))
            ]
            backups.sort(
                key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
                reverse=True
            )
    except Exception as e:
        current_app.logger.error(f"Failed to list backups: {e}")
        backups = []
        flash("Could not load backup list", "warning")

    today = date.today()
    today_quarter = (today.month - 1) // 3 + 1

    return render_template(
        'restore.html',
        backups=backups,
        today=today,
        today_quarter=today_quarter
    )

import json
from flask import send_file, request, flash, redirect, url_for, Response

@bp.route('/export-json')
def export_json():
    data = {}
    for table_name in db.metadata.tables.keys():
        model = globals().get(table_name.capitalize())
        if not model or not hasattr(model, 'query') or not hasattr(model, 'to_dict'):
            continue
        data[table_name] = [row.to_dict() for row in model.query.all()]

    json_str = json.dumps(data, indent=2)
    resp = Response(json_str, mimetype='application/json')
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    resp.headers['Content-Disposition'] = f'attachment; filename=wfm_planner_{ts}.json'
    return resp


from flask import request, flash, redirect, url_for, render_template
from datetime import datetime, date, time
from app.models import TaskStatus  # ← Make sure this is imported

@bp.route('/import-json', methods=['GET', 'POST'])
def import_json():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.json'):
            try:
                data = json.load(file)

                for table, rows in data.items():
                    model_name = table.capitalize()
                    model = globals().get(model_name)
                    if not model:
                        continue

                    # Clear existing data
                    db.session.query(model).delete()

                    for row in rows:
                        row.pop('id', None)  # Let DB assign new ID

                        # === DATE CONVERSIONS ===
                        date_fields = ['due_date', 'start_date', 'end_date', 'date']  # ← ADD 'date'
                        for field in date_fields:
                            if field in row and row[field]:
                                try:
                                    row[field] = datetime.strptime(row[field], '%Y-%m-%d').date()
                                except ValueError:
                                    row[field] = None

                        # === TIME CONVERSIONS ===
                        time_fields = ['start_time', 'end_time']
                        for field in time_fields:
                            if field in row and row[field]:
                                try:
                                    row[field] = datetime.strptime(row[field], '%H:%M:%S').time()
                                except ValueError:
                                    row[field] = None

                        # === DATETIME CONVERSIONS ===
                        if 'created_at' in row and row['created_at']:
                            try:
                                row['created_at'] = datetime.fromisoformat(
                                    row['created_at'].replace('Z', '+00:00')
                                )
                            except ValueError:
                                row['created_at'] = datetime.utcnow()

                        # === ENUM CONVERSIONS (Task.status, Goal.status) ===
                        if table == 'task' and 'status' in row:
                            try:
                                row['status'] = TaskStatus(row['status'])
                            except ValueError:
                                row['status'] = TaskStatus.TODO

                        if table == 'goal' and 'status' in row:
                            # Map string → string (since Goal.status is String)
                            valid = {'todo', 'in_progress', 'blocked', 'done'}
                            row['status'] = row['status'] if row['status'] in valid else 'todo'

                        # === CREATE OBJECT ===
                        obj = model(**row)
                        db.session.add(obj)

                db.session.commit()
                flash("Database imported successfully!", "success")
                return redirect(url_for('main.index'))

            except Exception as e:
                db.session.rollback()
                flash(f"Import failed: {str(e)}", "danger")

        flash("Invalid file", "danger")

    # GET: Show upload form
    today = date.today()
    today_quarter = (today.month - 1) // 3 + 1
    return render_template('import_json.html', today=today, today_quarter=today_quarter)

# --------------------------------------------------------------
# API: add a task (only from the To-Do column)
# --------------------------------------------------------------
@bp.route('/api/task', methods=['POST'])  # Or @app.route if not Blueprint
def api_add_task():
    data = request.get_json()
    backlog = data.get('backlog', False)

    task_date = None
    if not backlog:
        # Only require year/month/day if NOT backlog
        try:
            year = int(data['year'])
            month = int(data['month'])
            day = int(data['day'])
            task_date = date(year=year, month=month, day=day)
        except (KeyError, TypeError, ValueError) as e:
            return jsonify({'error': 'Invalid or missing date for non-backlog task'}), 400
    task = Task(
        description=data['description'],
        date=task_date,
        status = TaskStatus.BACKLOG if backlog else TaskStatus.TODO,
        notes=data.get('notes', '')
    )
  

    #print(task)
    db.session.add(task)
    db.session.commit()
    return jsonify({'id': task.id, 'description': task.description})


# --------------------------------------------------------------
# API: change task status (drag-and-drop)
# --------------------------------------------------------------
@bp.route('/api/task/<int:task_id>/status', methods=['POST'])  # Or @app.route
def api_update_status(task_id):
    data = request.json
    status_str = data.get('status', '').strip().upper()  # ← UPPERCASE IT
    
    if status_str not in [e.name for e in TaskStatus]:
        return jsonify(success=False, error="Invalid status"), 400

    task = Task.query.get_or_404(task_id)
    
    new_status = TaskStatus[status_str]  # ← Now works with 'BLOCKED'
    
    # Set date to today when marked DONE
    if new_status == TaskStatus.DONE:
        task.date = date.today()
        #current_app.logger.info(f"Task {task.id}: marked DONE on {task.date}")
    elif data['status'] == 'backlog':
        task.date = None                       # ← CLEAR THE DATE
    else:
        # Any other status change on a dated task → keep today's date
        if task.date is None:
            task.date = date.today()       # ← was in backlog, now pulled to today
    
    
    task.status = new_status
    db.session.commit()
    
    return jsonify(success=True)

from typing import Tuple

def quarter_range(year: int, month: int) -> Tuple[date, date]:
    """
    Return (start_date, end_date) for the quarter that contains the given year/month.
    """
    # 1-based quarter number
    q = (month - 1) // 3 + 1

    # First month of the quarter
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)

    # Last month of the quarter
    end_month = start_month + 2
    # Next month, day 1
    next_month = date(year, end_month, 28) + timedelta(days=4)
    end = next_month.replace(day=1) - timedelta(days=1)   # last day of end_month

    return start, end

def month_range_from_week(year: int, week_num: int) -> tuple[date, date]:
    """
    Given a year and ISO week number, return (start, end) of the month
    that contains the majority of days in that week.
    Weeks start on Sunday.
    """
    # Step 1: Find the Sunday of the given ISO week
    jan4 = date(year, 1, 4)  # Jan 4 is always in week 1
    jan4_weekday = jan4.weekday()  # Mon=0 ... Sun=6
    # Days to Sunday of week 1
    days_to_sunday = (jan4_weekday + 1) % 7
    week1_sunday = jan4 - timedelta(days=days_to_sunday)
    # Sunday of target week
    week_sunday = week1_sunday + timedelta(weeks=week_num - 1)

    # Step 2: Get all 7 days of the week (Sun → Sat)
    week_days = [week_sunday + timedelta(days=i) for i in range(7)]

    # Step 3: Count how many days fall in each month
    month_counts = {}
    for d in week_days:
        key = (d.year, d.month)
        month_counts[key] = month_counts.get(key, 0) + 1

    # Step 4: Pick the month with the most days
    dominant_year, dominant_month = max(month_counts.items(), key=lambda x: x[1])[0]

    # Step 5: Return first and last day of that month
    start = date(dominant_year, dominant_month, 1)
    # Next month, day 1 - 1 day
    next_month = start.replace(month=start.month % 12 + 1, year=start.year + (start.month // 12))
    if next_month.month == 1:
        next_month = next_month.replace(year=next_month.year)
    end = next_month - timedelta(days=1)

    return start, end

from datetime import date, timedelta

def week_range(year: int, month: int, day: int) -> tuple[date, date]:
    """
    Return (week_start_sunday, week_end_saturday) for the given date.
    Week starts on Sunday.
    """
    #print(year, month, day)
    given_date = date(year, month, day)
    
    # weekday(): Mon=0, Tue=1, ..., Sun=6
    # Days to subtract to get to Sunday
    days_to_sunday = (given_date.weekday() + 1) % 7
    
    week_start = given_date - timedelta(days=days_to_sunday)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end

from flask import jsonify
from datetime import datetime, date, timedelta
import requests
from icalendar import Calendar
import pytz

# ——— THE EXPANDER — DEFINED ONCE, AT THE TOP — LIKE A TRUE CHAMPION ———
def expand_recurring_event(base_start_utc, base_end_utc, rrule_str, target_date):
    occurrences = []
    params = {}
    for part in rrule_str.upper().split(';'):
        if '=' not in part:
            continue
        k, v = part.split('=', 1)
        params[k] = v

    if params.get('FREQ') != 'WEEKLY':
        return []

    interval = int(params.get('INTERVAL', '1'))
    until_str = params.get('UNTIL')
    byday = params.get('BYDAY', '')

    duration = base_end_utc - base_start_utc

    # Parse UNTIL
    until_dt = None
    if until_str and len(until_str) >= 15:
        try:
            until_dt = datetime.strptime(until_str[:15], "%Y%m%dT%H%M%S")
            if until_str.endswith('Z'):
                until_dt = until_dt.replace(tzinfo=None)
        except:
            pass

    # Map BYDAY
    weekday_map = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
    target_weekdays = [weekday_map[d.strip()] for d in byday.split(',') if d.strip() in weekday_map]
    if not target_weekdays:
        target_weekdays = [base_start_utc.weekday()]

    # Find Monday of original week
    week_monday = base_start_utc - timedelta(days=base_start_utc.weekday())
    current_week_monday = week_monday

    while current_week_monday.date() <= target_date + timedelta(days=365):
        if until_dt and current_week_monday >= until_dt:
            break

        for wd in target_weekdays:
            candidate = current_week_monday + timedelta(days=wd)
            if candidate.date() < base_start_utc.date():
                continue
            if until_dt and candidate >= until_dt:
                continue
            if candidate.date() == target_date:
                start_time = base_start_utc.time()
                end_time = (base_start_utc + duration).time()
                occurrences.append((start_time, end_time))

        current_week_monday += timedelta(days=7 * interval)

    return occurrences


@bp.route('/api/import-calendar', defaults={'datestr': None})
@bp.route('/api/import-calendar/<datestr>')
def import_calendar(datestr):
    # THIS IS THE KEY — FORCE FULL RANGE
    base_url = os.getenv('ICS_CALENDAR_URL', '').split('?')[0]
    ics_url = base_url #f"{base_url}?st=20250101&et=20261231"

    target_date = date.today()
    if datestr and len(datestr) == 8 and datestr.isdigit():
        try:
            target_date = date(int(datestr[:4]), int(datestr[4:6]), int(datestr[6:8]))
        except:
            return jsonify({'success': False, 'error': 'Bad date'}), 400

    central = pytz.timezone('US/Central')

    try:
        response = requests.get(ics_url, timeout=30)
        response.raise_for_status()
        cal = Calendar.from_ical(response.content)

        imported = 0
        for component in cal.walk():

            if component.name != "VEVENT":
                continue

            dtstart_prop = component.get('dtstart')
            if not dtstart_prop:
                continue

            # Skip all-day
            if isinstance(dtstart_prop.dt, date) and not isinstance(dtstart_prop.dt, datetime):
                continue

            # Use RECURRENCE-ID if present — that's the real date
            date_prop = component.get('recurrence-id') or dtstart_prop
            raw_date = date_prop.dt

            if isinstance(raw_date, datetime):
                if raw_date.tzinfo is None:
                    raw_date = raw_date.replace(tzinfo=pytz.UTC)
                event_date = raw_date.astimezone(central).date()
            else:
                event_date = raw_date

            if event_date != target_date:
                continue

            # Now get actual times from DTSTART/DTEND
            start_raw = dtstart_prop.dt
            end_raw = component.get('dtend').dt if component.get('dtend') else start_raw + timedelta(minutes=30)

            if isinstance(start_raw, datetime) and start_raw.tzinfo is None:
                start_raw = start_raw.replace(tzinfo=pytz.UTC)
            if isinstance(end_raw, datetime) and end_raw.tzinfo is None:
                end_raw = end_raw.replace(tzinfo=pytz.UTC)

            start_central = start_raw.astimezone(central)
            end_central = end_raw.astimezone(central)

            event = Event(
                title=str(component.get('summary', 'Untitled')),
                start_date=target_date,
                end_date=target_date,
                start_time=start_central.time(),
                end_time=end_central.time(),
            )
            db.session.add(event)
            imported += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'date': target_date.strftime('%Y-%m-%d'),
            'imported': imported
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
            
@bp.route('/api/task/<int:task_id>/today', methods=['POST'])
def pull_task_to_today(task_id):
    task = Task.query.get_or_404(task_id)
    task.date = date.today()
    task.status = TaskStatus.TODO # Reset to TODO when pulled to today
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/task/<int:task_id>/rank', methods=['POST'])
def update_task_rank(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}
    task.rank = data.get('rank', 0)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/goals/<int:goal_id>/rank', methods=['POST'])
def update_goal_rank(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.get_json() or {}
    goal.rank = data.get('rank', 0)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)  
    db.session.delete(task)
    db.session.commit()
    return jsonify(success=True), 200

# routes/task.py or wherever your task API lives
@bp.route('/api/task/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    task.description = data.get('description', task.description).strip()
    db.session.commit()
    return jsonify(success=True)