"""Briefing cache service — manages the Chief of Staff briefing data."""

import json
import logging
from datetime import datetime, timezone

from ..db import get_connection

logger = logging.getLogger(__name__)

STALE_HOURS = 18  # Briefing is stale after 18 hours


def get_cached_briefing() -> dict | None:
    """Return cached briefing data or None if never generated.

    Returns dict with keys: status, content (parsed JSON), generated_at,
    refresh_started_at, error_message.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status, content, generated_at, refresh_started_at, error_message "
            "FROM briefing_cache WHERE id = 1"
        ).fetchone()
        if not row:
            return None
        result = {
            "status": row["status"],
            "content": json.loads(row["content"]) if row["content"] else None,
            "generated_at": row["generated_at"],
            "refresh_started_at": row["refresh_started_at"],
            "error_message": row["error_message"],
        }
        result["is_stale"] = is_stale(row["generated_at"])
        return result
    except Exception as e:
        logger.error(f"Failed to read briefing cache: {e}")
        return None
    finally:
        conn.close()


def is_stale(generated_at: str | None = None, max_hours: float = STALE_HOURS) -> bool:
    """Check if briefing is stale (older than max_hours)."""
    if not generated_at:
        return True
    try:
        gen_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - gen_dt).total_seconds() / 3600
        return age > max_hours
    except (ValueError, TypeError):
        return True


def mark_refresh_started():
    """Set status to 'running' with timestamp."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO briefing_cache (id, status, refresh_started_at) "
            "VALUES (1, 'running', ?) "
            "ON CONFLICT(id) DO UPDATE SET status='running', refresh_started_at=?",
            (now, now),
        )
        conn.commit()
    finally:
        conn.close()


def save_briefing(data: dict):
    """Save generated briefing content and mark as ready."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        content_json = json.dumps(data, ensure_ascii=False)
        conn.execute(
            "INSERT INTO briefing_cache (id, status, content, generated_at) "
            "VALUES (1, 'ready', ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status='ready', content=?, "
            "generated_at=?, error_message=NULL",
            (content_json, now, content_json, now),
        )
        conn.commit()
        logger.info("Briefing cache updated")
    finally:
        conn.close()


def mark_refresh_error(error_msg: str):
    """Record a refresh failure."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE briefing_cache SET status='error', error_message=? WHERE id=1",
            (error_msg,),
        )
        conn.commit()
    finally:
        conn.close()


def collect_task_data() -> str:
    """Collect active/waiting/in_progress/suggested tasks as a formatted string
    suitable for embedding in a prompt."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, status, priority, key_people, source_type, "
            "source_id, due_date, committed_date, coaching_text, waiting_activity, "
            "created_at, updated_at "
            "FROM tasks "
            "WHERE status IN ('active','in_progress','waiting','suggested') "
            "ORDER BY priority, status, updated_at DESC"
        ).fetchall()

        lines = []
        for r in rows:
            people = ""
            if r["key_people"]:
                try:
                    kp = json.loads(r["key_people"])
                    people = ", ".join(p.get("name", p.get("email", "")) for p in kp)
                except (json.JSONDecodeError, TypeError):
                    people = r["key_people"]

            waiting_info = ""
            if r["waiting_activity"]:
                try:
                    wa = json.loads(r["waiting_activity"])
                    waiting_info = f" | waiting_status={wa.get('status', '')} summary={wa.get('summary', '')}"
                except (json.JSONDecodeError, TypeError):
                    pass

            line = (
                f"#{r['id']} [{r['status']}] P{r['priority']} — {r['title']}"
                f" | people: {people or 'none'}"
                f" | source: {r['source_type'] or 'manual'}"
                f" | due: {r['due_date'] or 'none'}"
                f" | updated: {r['updated_at']}"
                f"{waiting_info}"
            )
            lines.append(line)

        return f"Total: {len(lines)} tasks\n" + "\n".join(lines)
    finally:
        conn.close()
