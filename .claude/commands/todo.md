---
description: Show TodoNess status summary and dashboard URL
---

Read the TodoNess SQLite database at `$PROJECT_ROOT/data/claudetodo.db` and display a status summary.

Use Python to query the database:
```python
import sqlite3
conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
```

Show:
1. **Task counts by status**: active, in_progress, suggested, completed, dismissed
2. **Unparsed tasks**: count of tasks with parse_status != 'parsed'
3. **Last sync**: most recent entry from sync_log table (synced_at and sync_type)
4. **Dashboard URL**: http://localhost:8766

Format as a clean summary table. If the database doesn't exist, say "No database found. Run /todo-add to create your first task."
