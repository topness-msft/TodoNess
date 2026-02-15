import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "claudetodo.db"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, title, parse_status FROM tasks WHERE parse_status != 'parsed' ORDER BY id").fetchall()
for r in rows:
    print(f"#{r['id']} | {r['parse_status']} | {r['title'][:70]}")
if not rows:
    print("All tasks parsed.")
conn.close()
