# app/routes.py
from flask import Blueprint, render_template, request, jsonify, abort, url_for, flash, redirect
from . import db
from .models import Goal, Note, Event
from .forms import GoalForm
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from calendar import Calendar, SUNDAY, setfirstweekday
from sqlalchemy import case
from sqlalchemy import and_, or_
import calendar
from calendar import monthcalendar, day_name
from calendar import month_name  # ← ADD THIS LINE


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


from datetime import datetime
from sqlalchemy import case as db_case

@bp.route('/goals', methods=['GET', 'POST'])
def goals():
    form = GoalForm()
    print(form)
    if request.method == 'POST':
        print("=== /goals POST DEBUG ===")
        print("Form data:", dict(request.form))
        print("Parent ID:", request.form.get('parent_id'))
        # DEBUG: Check what came in
        print("Raw type from form:", request.form.get('type'))
    
        # FORCE DEFAULT IF BLANK
        if not form.type.data:
            form.type.data = 'annual'
        print("Forced type to 'annual'")

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

            print(goal)
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
        db.or_(
            Goal.parent_id.is_(None),
            Goal.parent_id == ''
        )
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

    annual_goals = Goal.query.filter(
        Goal.type == 'annual',
        db.or_(
            db.and_(Goal.due_date >= y_start, Goal.due_date <= y_end),
            Goal.due_date.is_(None)
        ),
        db.or_(  # ← ADD THIS
            Goal.parent_id.is_(None),
            Goal.parent_id == ''
        )
    ).order_by(
        db.case((Goal.due_date.is_(None), 0), else_=1),
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
  
    # GET POSSIBLE PARENTS (weekly goals in same week, NOT completed)
    start_month = (q_num - 1) * 3 + 1
    day_date = datetime(year, start_month, 1).date()
    w_start = day_date - timedelta(days=day_date.weekday())
    w_end = w_start + timedelta(days=6)
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
    ).order_by(Goal.due_date).all()

    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1

    # SUNDAY-FIRST CALENDAR
    setfirstweekday(SUNDAY)  # ← FORCE SUNDAY
    #cal = monthcalendar(year, month)
    cal = Calendar(firstweekday=SUNDAY)
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                day_date = datetime(year, month, 1).date()
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
    # GET POSSIBLE PARENTS (weekly goals in same week, NOT completed)
    # GET POSSIBLE PARENTS (monthly goals overlapping week, NOT completed)
    m_start_dt = datetime(m_start.year, m_start.month, 1)  # datetime
    m_end_dt = m_start_dt + relativedelta(months=1) - timedelta(days=1)  # datetime

    possible_parents = Goal.query.filter(
        Goal.type == 'quarterly',
        or_(
            and_(Goal.due_date >= m_start_dt.date(), Goal.due_date <= m_end_dt.date()),
            Goal.due_date.is_(None)
        ),
        Goal.completed == False
    ).order_by(Goal.due_date.asc(), Goal.id).all()
  
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

    # GENERATE CALENDAR WITH WEEK NUMBERS
    cal = monthcalendar(year, month)
    calendar_with_weeks = []
    for i, week in enumerate(cal, start=1):
        # Get week number from first non-zero day
        first_day = None
        for day in week:
            if day != 0:
                first_day = date(year, month, day)
                break
        if first_day:
            week_num = first_day.isocalendar()[1]
        else:
            # Fallback: use first day of month
            week_num = date(year, month, 1).isocalendar()[1] + i - 1
        calendar_with_weeks.append((week_num, week))

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
        weeks=weeks,
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
        # Monday of the week (ISO)
        w_start = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
    except ValueError:
        abort(404)
    w_end = w_start + timedelta(days=6)

    # PICK MONDAY FOR PARENT FILTER
    day_date = w_start

    # GET POSSIBLE PARENTS (monthly goals overlapping week, NOT completed)
    m_start_dt = datetime(w_start.year, w_start.month, 1)  # datetime
    m_end_dt = m_start_dt + relativedelta(months=1) - timedelta(days=1)  # datetime

    possible_parents = Goal.query.filter(
        Goal.type == 'monthly',
        or_(
            and_(Goal.due_date >= m_start_dt.date(), Goal.due_date <= m_end_dt.date()),
            Goal.due_date.is_(None)
        ),
        Goal.completed == False
    ).order_by(Goal.due_date.asc(), Goal.id).all()

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
        week=week,
        month=month,
        title=f"Week {week}: {w_start.strftime('%b %d')} - {w_end.strftime('%b %d, %Y')}",
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

    daily_goals = Goal.query.filter(
        Goal.type == 'daily',
        Goal.due_date == day_date,
        Goal.parent_id.isnot(None)
    ).order_by(Goal.due_date).all()

    prev_date = day_date - timedelta(days=1)
    next_date = day_date + timedelta(days=1)

    daily_goals_grouped = group_goals_by_status(daily_goals)
    
    # GET POSSIBLE PARENTS (weekly goals in same week, NOT completed)
    day_date = datetime(year, month, day).date()
    w_start = day_date - timedelta(days=day_date.weekday())
    w_end = w_start + timedelta(days=6)
    possible_parents = Goal.query.filter(
        Goal.type == 'weekly',
        Goal.due_date >= w_start,
        Goal.due_date <= w_end,
        Goal.completed == False  # ← EXCLUDE COMPLETED
    ).all()

    def events_on_date(y, m, d):
        date = datetime(y, m, d).date()
        return Event.query.filter(
            Event.start_date <= date,
            Event.end_date >= date
        ).order_by(
            Event.all_day.desc(),
            Event.start_time.asc()
        ).all()
    
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
        today_quarter=today_quarter
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
    print("=== /api/goal/{parent_id}/subgoal DEBUG ===")
    print("Parent ID:", parent_id)
    print("JSON data:", request.json)
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
    print(key)
    scope = parts[1]
    type_ = parts[-2]
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
    print(filters)
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