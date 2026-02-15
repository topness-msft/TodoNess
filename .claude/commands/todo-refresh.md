---
description: Full M365 scan — single WorkIQ call surfaces actionable items as suggested tasks
---

Perform a comprehensive M365 scan via WorkIQ to surface actionable items as suggested tasks.

Today's date is $CURRENT_DATE.

## Step 0: Clear sync request marker

```python
from pathlib import Path
p = Path('$PROJECT_ROOT/data') / '.sync_requested'
if p.exists():
    p.unlink()
```

## Step 1: Determine sync window

```python
import sqlite3
from datetime import datetime, timezone, timedelta

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
conn.row_factory = sqlite3.Row
last_sync = conn.execute(
    "SELECT synced_at FROM sync_log WHERE sync_type IN ('full_scan', 'flagged_emails') ORDER BY synced_at DESC LIMIT 1"
).fetchone()
conn.close()

now = datetime.now(timezone.utc)
if last_sync and last_sync['synced_at']:
    last_dt = datetime.fromisoformat(last_sync['synced_at'].replace('Z', '+00:00'))
    days_since = max(1, (now - last_dt).days)  # floor at 1 for overlap safety
    if days_since > 7:
        days_since = 7  # cap at 7 days
else:
    days_since = 7  # first run default
```

Report the sync window: "Scanning the last {days_since} day(s)..."

## Step 2: Single WorkIQ scan

Call `ask_work_iq` with ONE comprehensive query (covers all 5 source categories in a single call):

```
What items across my Inbox emails, Teams messages, and meetings need my attention or action? For ALL email searches, only look in my Inbox folder (not Sent, Archive, or other folders). Include: (1) ALL emails currently flagged in my Inbox (no time limit — include every flagged email), (2) any emails in my Inbox categorized as 'TodoNess' (no time limit), (3) emails in my Inbox from the last {days_since} days asking for my response that I haven't replied to, (4) Teams messages from the last 3 days directed at me or @mentioning me that I haven't responded to, (5) action items from meetings in the last 3 days assigned to me or that I committed to, (6) emails or Teams messages I SENT in the last {days_since} days that contain a question or request where the recipient hasn't responded yet. For each item, give me: source type (email/teams/meeting), subject or topic, person name and email, date, and a brief summary of what's needed.
```

## Step 3: Parse results and create tasks

For **each item** WorkIQ returns, reason about the following fields:

- **title**: Clean imperative task title (e.g. "Reply to Sarah's budget proposal", "Follow up with Mehdi on deployment timeline")
- **source_type**: `email`, `chat`, or `meeting` — based on WorkIQ's categorization (Teams messages → `chat`)
- **action_type**: Infer from content:
  - `respond-email` — for emails needing a reply
  - `follow-up` — for items I sent that need a response, or items I need to chase
  - `schedule-meeting` — if a meeting needs scheduling
  - `prepare` — if meeting prep is needed
  - `general` — fallback
- **source_snippet**: WorkIQ's summary of what's needed
- **source_url**: Link from WorkIQ response if available, otherwise null
- **key_people**: JSON array with person name and email from the item. Format: `[{"name": "Full Name", "email": "email@domain.com"}]`
- **priority**: Infer from urgency cues:
  - P1: explicit deadline today, escalation language, executive asks
  - P2: time-sensitive, important sender, approaching deadline
  - P3: normal (default)
  - P4: FYI items, low-stakes follow-ups
- **source_id**: Generate a composite dedup key: `{source_type}::{sender_email_lower}::{subject_first_50_lower}::{date_YYYY-MM-DD}`

### Dedup check

For each item, before creating a task, check for duplicates:

```python
import sqlite3

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
conn.row_factory = sqlite3.Row
existing = conn.execute(
    "SELECT id, status, source_id, title FROM tasks WHERE source_id = ? OR LOWER(SUBSTR(title, 1, 40)) = LOWER(SUBSTR(?, 1, 40))",
    (source_id, title)
).fetchall()
conn.close()
```

**Skip** the item if:
- A task with the same `source_id` already exists (any status)
- A task with the same title prefix (first 40 chars, case-insensitive) already exists
- A dismissed task matches — never re-suggest dismissed items

**Note on flagged/categorized emails:** WorkIQ always returns these regardless of age. Normal dedup applies — if already in the DB, skip. But any *newly* flagged email that isn't already in the DB is always created as a suggestion.

If no duplicate found, create the task:

```python
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
conn.execute(
    """INSERT INTO tasks (title, description, status, parse_status, priority,
       source_type, source_id, source_snippet, source_url, key_people,
       action_type, coaching_text, created_at, updated_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (title, '', 'suggested', 'parsed', priority,
     source_type, source_id, source_snippet, source_url, key_people,
     action_type, None, now, now)
)
conn.commit()
conn.close()
```

Track counts: `created`, `skipped_dedup`, and counts by source type (`email`, `chat`, `meeting`).

## Step 4: Parse any unparsed tasks

Check for tasks with `parse_status IN ('unparsed', 'queued')` — if any exist, run the same logic as `/todo-parse` to enrich them.

## Step 5: Log the sync

```python
import json
import sqlite3
from datetime import datetime, timezone

summary = json.dumps({
    "email": email_count,
    "chat": chat_count,
    "meeting": meeting_count,
    "created": created_count,
    "skipped_dedup": skipped_count
})

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
conn.execute(
    "INSERT INTO sync_log (sync_type, result_summary, tasks_created, tasks_updated, synced_at) VALUES (?,?,?,?,?)",
    ('full_scan', summary, created_count, 0,
     datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
)
conn.commit()
conn.close()
```

## Step 6: Show summary

Display a summary table:

```
TodoNess Refresh Complete
─────────────────────────
Source       | Found | Created | Skipped
─────────────────────────────────────────
Email        |   X   |    X    |    X
Teams/Chat   |   X   |    X    |    X
Meeting      |   X   |    X    |    X
─────────────────────────────────────────
Total        |   X   |    X    |    X

Review suggestions in the dashboard and promote tasks you want to work on.
Dashboard: http://localhost:8766
```

If no new items were found, say: "Everything is up to date — no new items found since last sync."
