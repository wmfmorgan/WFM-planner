# export_db.py
import sqlite3
import json
from datetime import date, datetime

conn = sqlite3.connect('instance/wfm_planner.db')
cur = conn.cursor()

tables = ['goal', 'note', 'event', 'task']

data = {}
for table in tables:
    cur.execute(f"SELECT * FROM {table}")
    columns = [desc[0] for desc in cur.description]
    rows = []
    for row in cur.fetchall():
        row_dict = dict(zip(columns, row))
        # Convert date/time to strings
        for k, v in row_dict.items():
            if isinstance(v, (date, datetime)):
                row_dict[k] = v.isoformat()
        rows.append(row_dict)
    data[table] = rows

with open('local_db.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Exported to local_db.json")