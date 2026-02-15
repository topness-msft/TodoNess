"""Add 'deleted' to the status CHECK constraint.

SQLite doesn't support altering CHECK constraints, so we recreate the table.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "claudetodo.db"
conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA foreign_keys=OFF")

conn.executescript("""
BEGIN;

CREATE TABLE IF NOT EXISTS tasks_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('suggested','active','in_progress','completed','dismissed','deleted')),
    parse_status    TEXT NOT NULL DEFAULT 'parsed'
                        CHECK (parse_status IN ('unparsed','queued','parsing','parsed')),
    raw_input       TEXT,
    priority        INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    due_date        TEXT,
    committed_date  TEXT,
    source_type     TEXT DEFAULT 'manual'
                        CHECK (source_type IN ('email','meeting','chat','manual')),
    source_id       TEXT,
    source_url      TEXT,
    source_snippet  TEXT,
    coaching_text   TEXT,
    key_people      TEXT,
    related_meeting TEXT,
    user_notes      TEXT DEFAULT '',
    suggestion_refreshed_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

INSERT INTO tasks_new SELECT * FROM tasks;
DROP TABLE tasks;
ALTER TABLE tasks_new RENAME TO tasks;

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_parse_status ON tasks(parse_status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

COMMIT;
""")

conn.execute("PRAGMA foreign_keys=ON")
conn.close()
print("Migration complete — 'deleted' status now allowed.")
