# import_db.py
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Goal, Note, Event, Task
from datetime import datetime, date

# Connect to Render DB
engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

# Load JSON
with open('local_db.json') as f:
    data = json.load(f)

# Import each table
for table, rows in data.items():
    Model = {'goal': Goal, 'note': Note, 'event': Event, 'task': Task}[table]
    for row in rows:
        for k, v in row.items():
            if v and 'date' in k:
                row[k] = datetime.fromisoformat(v).date()
            elif v and 'time' in k:
                # Fix: Strip trailing zeros from microseconds
                clean_time = v.split('.')[0]  # "08:30:00.000000" → "08:30:00"
                row[k] = datetime.strptime(clean_time, '%H:%M:%S').time()
        obj = Model(**row)
        session.add(obj)
    session.commit()

print("All data imported!")