import sqlite3
import os

DB_PATH = os.path.abspath("simulation_logs.db")
print(f"DB Path: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print("DB does not exist found!")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 20")
rows = cursor.fetchall()

print(f"Found {len(rows)} rows.")
for r in rows:
    print(r)

conn.close()
