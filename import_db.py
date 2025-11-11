import json
import os
from sqlalchemy import create_engine

# Render auto-injects DATABASE_URL
engine = create_engine(os.environ['DATABASE_URL'])

with open('local_db.json') as f:
    data = json.load(f)

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()

from app.models import Goal, Note, Event, Task
from datetime import datetime, date

for table, rows in data.items():
    Model = {'goal': Goal, 'note': Note, 'event': Event, 'task': Task}[table]
    for row in rows:
        for k, v in row.items():
            if v and ('date' in k or 'time' in k):
                if 'date' in k:
                    row[k] = datetime.fromisoformat(v).date()
                elif 'time' in k:
                    row[k] = datetime.fromisoformat(v).time()
        obj = Model(**row)
        session.add(obj)
    session.commit()

print("Import complete!")