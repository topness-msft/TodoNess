"""Adaptive refresh scheduling based on priority and deadline proximity."""

from datetime import datetime, timedelta, timezone
from ..db import get_connection

# Base intervals in minutes by priority (1=urgent, 5=low)
BASE_INTERVALS = {1: 5, 2: 10, 3: 30, 4: 120, 5: 240}

# Near deadline (within 24h) intervals
NEAR_DEADLINE_INTERVALS = {1: 5, 2: 5, 3: 15, 4: 30, 5: 60}

# Urgent (within 4h) intervals
URGENT_INTERVALS = {1: 5, 2: 5, 3: 5, 4: 10, 5: 15}

MAX_INTERVAL = 480  # 8 hours cap
BACKOFF_THRESHOLD = 3  # consecutive no-change before doubling


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def compute_interval(priority: int, due_date: str | None, consecutive_no_change: int = 0) -> int:
    """Compute the refresh interval in minutes for a task."""
    now = datetime.now(timezone.utc)
    deadline = _parse_dt(due_date)

    if deadline:
        hours_until = (deadline - now).total_seconds() / 3600
        if hours_until <= 4:
            interval = URGENT_INTERVALS.get(priority, 30)
        elif hours_until <= 24:
            interval = NEAR_DEADLINE_INTERVALS.get(priority, 30)
        else:
            interval = BASE_INTERVALS.get(priority, 30)
    else:
        interval = BASE_INTERVALS.get(priority, 30)

    # Backoff: double interval after BACKOFF_THRESHOLD consecutive no-change refreshes
    if consecutive_no_change >= BACKOFF_THRESHOLD:
        doublings = consecutive_no_change - BACKOFF_THRESHOLD + 1
        interval = min(interval * (2 ** doublings), MAX_INTERVAL)

    return min(interval, MAX_INTERVAL)


def update_schedule(task_id: int, priority: int, due_date: str | None, had_changes: bool):
    """Update the refresh schedule for a task after a refresh."""
    conn = get_connection()
    now = _now()

    row = conn.execute(
        "SELECT * FROM refresh_schedule WHERE task_id = ?", (task_id,)
    ).fetchone()

    if row:
        no_change = 0 if had_changes else row["consecutive_no_change"] + 1
    else:
        no_change = 0 if had_changes else 1

    interval = compute_interval(priority, due_date, no_change)
    next_refresh = (
        datetime.now(timezone.utc) + timedelta(minutes=interval)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute(
        """INSERT INTO refresh_schedule (task_id, interval_minutes, next_refresh_at, last_refresh_at, consecutive_no_change)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(task_id) DO UPDATE SET
               interval_minutes = excluded.interval_minutes,
               next_refresh_at = excluded.next_refresh_at,
               last_refresh_at = excluded.last_refresh_at,
               consecutive_no_change = excluded.consecutive_no_change""",
        (task_id, interval, next_refresh, now, no_change),
    )
    conn.commit()
    conn.close()


def get_tasks_due_for_refresh() -> list[dict]:
    """Return task IDs that are due for a refresh, ordered by priority."""
    conn = get_connection()
    now = _now()
    rows = conn.execute(
        """SELECT t.*, rs.next_refresh_at, rs.interval_minutes, rs.consecutive_no_change
           FROM tasks t
           LEFT JOIN refresh_schedule rs ON t.id = rs.task_id
           WHERE t.status IN ('active', 'in_progress')
             AND (rs.next_refresh_at IS NULL OR rs.next_refresh_at <= ?)
           ORDER BY t.priority ASC""",
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_schedule(task_id: int) -> dict | None:
    """Get the refresh schedule for a task."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM refresh_schedule WHERE task_id = ?", (task_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
