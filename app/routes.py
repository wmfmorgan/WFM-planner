# app/routes.py
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
from calendar import monthcalendar, day_name
from calendar import month_name  # ← ADD THIS LINE
import shutil
from flask import send_file
import os
from flask import current_app
import json


bp = Blueprint('main', __name__)

# GLOBAL TODAY FOR NAVBAR
today = datetime.now().date()
today_quarter = ((today.month - 1) // 3) + 1

def get_iso_week_for_sunday(sun_date):
    """
    Given a Sunday date, find the ISO week number of that week's Monday.
    Minimal: No state change, just date math for remapping.
    """
    if sun_date.weekday() != 6:  # Quick guard (Sun == 6)
        raise ValueError("Input must be a Sunday")
    mon_date = sun_date - timedelta(days=6)
    return mon_date.isocalendar()[1]

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


from datetime import datetime
from sqlalchemy import case as db_case

@bp.route('/goals', methods=['GET', 'POST'])
def goals():
    form = GoalForm()
    #print(form)
    if request.method == 'POST':
        #print("=== /goals POST DEBUG ===")
        #print("Form data:", dict(request.form))
        #print("Parent ID:", request.form.get('parent_id'))
        # DEBUG: Check what came in
        #print("Raw type from form:", request.form.get('type'))
    
        # FORCE DEFAULT IF BLANK
        if not form.type.data:
            form.type.data = 'annual'
        #print("Forced type to 'annual'")

        if form.validate_on_submit():
            # === HANDLE parent_id: '' → None ===
            parent_id = request.form.get('parent_id')
            if parent_id == '':
                parent_id = None
            else:
                parent_id = int(parent_id) if parent_id else None

            # === HANDLE due_date: string → date ===
            due_date = None
            if form.due_date.data:
                if isinstance(form.due_date.data, str):
                    try:
                        due_date = datetime.strptime(form.due_date.data, '%Y-%m-%d').date()
                    except ValueError:
                        flash('Invalid due date format.', 'danger')
                        return redirect(url_for('main.goals'))
                else:
                    # Already a date object (from DB)
                    due_date = form.due_date.data

            # === CREATE GOAL ===
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

            #print(goal)
            db.session.add(goal)
            db.session.commit()
            flash('Goal saved!', 'success')
        else:
            flash('Form validation failed.', 'danger')
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{getattr(form, field).label.text}: {error}", 'danger')
        return redirect(url_for('main.goals'))

    # === GET: LOAD TOP-LEVEL GOALS ===
    goals = Goal.query.filter(
        Goal.parent_id.is_(None)
    ).options(
        db.joinedload(Goal.children)
    ).order_by(
        db_case((Goal.due_date.is_(None), 0), else_=1),
        Goal.due_date.asc(),
        Goal.id
    ).all()

    # === SORT CHILDREN RECURSIVELY ===
    def sort_children(goal):
        if goal.children:
            goal.children.sort(key=lambda x: (x.due_date or datetime.max.date(), x.id))
            for child in goal.children:
                sort_children(child)

    for goal in goals:
        sort_children(goal)

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
    ).all()

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
    ).order_by(Goal.due_date.asc(), Goal.id).all()

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
  
    # GET POSSIBLE PARENTS (weekly goals in same week, NOT completed)
    #start_month = (q_num - 1) * 3 + 1
    #day_date = datetime(year, start_month, 1).date()
    #w_start = day_date - timedelta(days=day_date.weekday())
    #w_end = w_start + timedelta(days=6)
    w_start = datetime(year,1,1).date()
    w_end = datetime(year,12,31).date()
    possible_parents = Goal.query.filter(
        Goal.type == 'annual',
        Goal.due_date >= w_start,
        Goal.due_date <= w_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).all() 

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
    ).order_by(Goal.due_date.asc(), Goal.id).all()

    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1

    # --- SUNDAY-FIRST CALENDAR WITH 100% CORRECT ISO WEEK NUMBERS ---
    calendar_with_weeks = []
    cal = Calendar(firstweekday=SUNDAY)

    for week in cal.monthdayscalendar(year, month):
        sunday_day = week[0]  # First day = Sunday (0 if padding)

        if sunday_day != 0:
            sun_date = date(year, month, sunday_day)
        else:
            first_of_month = date(year, month, 1)
            days_back = (first_of_month.weekday() + 1) % 7
            sun_date = first_of_month - timedelta(days=days_back)

        # CORRECT: Monday = Sunday + 1 day
        monday = sun_date + timedelta(days=1)
        iso_week = monday.isocalendar()[1]

        calendar_with_weeks.append((iso_week, week))        
    monthly_goals_grouped = group_goals_by_status(monthly_goals)
    # GET POSSIBLE PARENTS (weekly goals in same week, NOT completed)
    # GET POSSIBLE PARENTS (monthly goals overlapping week, NOT completed)
    m_start_dt = datetime(m_start.year, m_start.month, 1)  # datetime
    m_end_dt = m_start_dt + relativedelta(months=1) - timedelta(days=1)  # datetime
    #print("date")
    #today = date.today()  # Nov 10, 2025
    q_start, q_end = quarter_range(year, month)
    #print(f"Start: {q_start} | End: {q_end}")
    #last_day = last_day_of_month(year, month)
    #print(last_day)  # 2025-11-30
    #m_start_dt = datetime(m_start.year, m_start.month, 1).date()
    #m_end_dt = last_day
    possible_parents = Goal.query.filter(
        Goal.type == 'quarterly',
        Goal.due_date >= q_start,
        Goal.due_date <= q_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).all() 

    #print(F"Possbile Parens: {possible_parents}")

    #possible_parents = Goal.query.filter(
     #   Goal.type == 'quarterly',
      #  or_(
      #      and_(Goal.due_date >= m_start_dt.date(), Goal.due_date <= m_end_dt.date()),
      #      Goal.due_date.is_(None)
    # ),
    #   Goal.completed == False
    #).order_by(Goal.due_date.asc(), Goal.id).all()
  
    calendar = monthcalendar(year, month)
    month_name = date(year, month, 1).strftime('%B')


    def events_on_date(year, month, day):
        date = datetime(year, month, day).date()
        return Event.query.filter(
            Event.start_date <= date,
            Event.end_date >= date
        ).order_by(
            Event.all_day.desc(),  # All day first
            Event.start_time.asc()   # Then by time
        ).all()

 

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
        #weeks=weeks,
        today=today,
        page_type='month',
        parent_type='quarterly',
        form=form,
        possible_parents=possible_parents,
        today_quarter=today_quarter,
        events_on_date=events_on_date,
        calendar=calendar,  # ← ADD THIS
        calendar_with_weeks=calendar_with_weeks,
        month_name=month_name  # ← ADD THIS
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

    # GET POSSIBLE PARENTS (monthly goals overlapping week, NOT completed)
    #m_start_dt = datetime(w_start.year, w_start.month, 1)  # datetime
    #m_end_dt = m_start_dt + relativedelta(months=1) - timedelta(days=1)  # datetime

    m_start, m_end = month_range_from_week(year, week)

    possible_parents = Goal.query.filter(
        Goal.type == 'monthly',
        Goal.due_date >= m_start,
        Goal.due_date <= m_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).order_by(Goal.due_date.asc(), Goal.id).all() 

    #possible_parents = Goal.query.filter(
     #   Goal.type == 'monthly',
     #   or_(
     #       and_(Goal.due_date >= m_start_dt.date(), Goal.due_date <= m_end_dt.date()),
    #      Goal.due_date.is_(None)
     #   ),
    #  Goal.completed == False
    #).order_by(Goal.due_date.asc(), Goal.id).all()

    # GET WEEKLY GOALS
    weekly_goals = Goal.query.filter(
        Goal.type == 'weekly',
        or_(
            and_(Goal.due_date >= w_start, Goal.due_date <= w_end),
            Goal.due_date.is_(None)
        )
        #or_(Goal.parent_id.is_(None), Goal.parent_id == '')
    ).order_by(
        db_case((Goal.due_date.is_(None), 0), else_=1),
        Goal.due_date.asc(),
        Goal.id
    ).all()

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
    ).order_by(Goal.due_date).all()

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

    # FINAL QUERY
    today_tasks = Task.query.filter(*filters).order_by(
        case(
            (Task.status != TaskStatus.DONE, 0),  # Incomplete first
            else_=1
        ),
        Task.id
    ).all()

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
        kanban=kanban
    )


# API: UPDATE GOAL STATUS
@bp.route('/api/goal/<int:goal_id>/status', methods=['POST'])
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
@bp.route('/api/goal/<int:parent_id>/subgoal', methods=['POST'])
def add_subgoal(parent_id):
    #print("=== /api/goal/{parent_id}/subgoal DEBUG ===")
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
    return jsonify({'status': 'success', 'goal_id': goal.id})


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

@bp.route('/api/goal/<int:goal_id>', methods=['GET'])
def get_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    return jsonify(goal.to_dict())

# EDIT GOAL
@bp.route('/api/goal/<int:goal_id>', methods=['PUT'])
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
    return jsonify({'status': 'success'})

@bp.route('/api/goal/<int:goal_id>/reparent', methods=['POST'])
def reparent_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    data = request.json
    goal.parent_id = data.get('parent_id')
    db.session.commit()
    return jsonify({'status': 'success'})

@bp.route('/api/goal/create', methods=['POST'])
def create_goal():
    data = request.json
    goal = Goal(
        title=data['title'],
        type=data['type'],
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify({'status': 'success', 'goal_id': goal.id})

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
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    
    if not os.path.exists(db_path):
        flash("Database file not found!", "danger")
        return redirect(url_for('main.index'))
    
    shutil.copy(db_path, backup_path)
    flash(f"Backup created: {os.path.basename(backup_path)}", "success")
    return redirect(url_for('main.index'))

from flask import current_app
import shutil

@bp.route('/restore', methods=['GET', 'POST'])
def restore_db():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.db'):
            # SAVE TO INSTANCE PATH
            db_path = os.path.join(current_app.instance_path, 'wfm_planner.db')
            file.save(db_path)
            flash("Database restored successfully!", "success")
            return redirect(url_for('main.index'))
        flash("Invalid file", "danger")
    
    today = date.today()
    today_quarter = (today.month - 1) // 3 + 1
    
    backups = sorted([f for f in os.listdir('backups') if f.endswith('.db')], 
                     key=lambda x: os.path.getmtime(f'backups/{x}'), reverse=True)
    
    return render_template('restore.html', backups=backups, today=today, today_quarter=today_quarter)

import json
from flask import send_file, request, flash, redirect, url_for, Response

@bp.route('/export-json')
def export_json():
    """Export all DB tables to JSON"""
    data = {}
    for table in db.metadata.tables.keys():
        model = globals()[table.capitalize()]
        data[table] = [row.__dict__ for row in model.query.all()]
        for row in data[table]:
            row.pop('_sa_instance_state', None)
    
    json_str = json.dumps(data, indent=2, default=str)
    response = Response(json_str, mimetype='application/json')
    response.headers['Content-Disposition'] = f'attachment; filename=wfm_planner_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    return response


@bp.route('/import-json', methods=['GET', 'POST'])
def import_json():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.json'):
            data = json.load(file)
            for table, rows in data.items():
                model = globals()[table.capitalize()]
                db.session.query(model).delete()
                for row in rows:
                    # CONVERT DATES
                    if 'due_date' in row and row['due_date']:
                        row['due_date'] = datetime.strptime(row['due_date'], '%Y-%m-%d').date()
                    if 'start_date' in row and row['start_date']:
                        row['start_date'] = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                    if 'end_date' in row and row['end_date']:
                        row['end_date'] = datetime.strptime(row['end_date'], '%Y-%m-%d').date()
                    
                    # CONVERT TIMES
                    if 'start_time' in row and row['start_time']:
                        row['start_time'] = datetime.strptime(row['start_time'], '%H:%M:%S').time()
                    if 'end_time' in row and row['end_time']:
                        row['end_time'] = datetime.strptime(row['end_time'], '%H:%M:%S').time()
                    
                    # CONVERT created_at
                    if 'created_at' in row and row['created_at']:
                        row['created_at'] = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
                    
                    obj = model(**row)
                    db.session.add(obj)
            db.session.commit()
            flash("Database imported from JSON!", "success")
            return redirect(url_for('main.index'))
        flash("Invalid file", "danger")
    
    today = date.today()
    today_quarter = (today.month - 1) // 3 + 1
    return render_template('import_json.html', today=today, today_quarter=today_quarter)

# --------------------------------------------------------------
# API: add a task (only from the To-Do column)
# --------------------------------------------------------------
@bp.route('/api/task', methods=['POST'])  # Or @app.route if not Blueprint
def api_add_task():
    data = request.get_json()
    task_date = date(
        year=int(data['year']),
        month=int(data['month']),
        day=int(data['day'])
    )
    task = Task(
        description=data['description'],
        date=task_date,
        status=TaskStatus.TODO,
        notes=data.get('notes', '')
    )
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
        current_app.logger.info(f"Task {task.id}: marked DONE on {task.date}")
    
    task.status = new_status
    db.session.commit()
    
    return jsonify(success=True)

@bp.context_processor
def inject_week_info():
    today = date.today()
    # Calculate days to subtract to get to Sunday (weeks start Sunday)
    days_to_sunday = (today.weekday() + 1) % 7  # Mon=0 → 1, Sun=6 → 0
    this_sunday = today - timedelta(days=days_to_sunday)
    current_week_num = this_sunday.isocalendar()[1]
    
    return {
        'current_week_num': current_week_num,
        'today': today
    }

def last_day_of_month(year: int, month: int) -> date:
    # Next month, day 1
    next_month = date(year, month, 28) + timedelta(days=4)  # Safe: 28 + 4 always rolls over
    # Back 1 day = last day of current month
    return next_month.replace(day=1) - timedelta(days=1)

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