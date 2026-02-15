"""Parse WorkIQ responses into task suggestions with deduplication."""

from ..models import list_tasks


def generate_source_id(source_type: str, sender: str, subject: str, date: str) -> str:
    """Build a stable composite key for deduplication.

    Format: {source_type}::{sender_lower}::{subject_first_50_lower}::{date}
    """
    sender_part = (sender or "").strip().lower()
    subject_part = (subject or "").strip().lower()[:50]
    date_part = (date or "").strip()[:10]  # YYYY-MM-DD
    return f"{source_type}::{sender_part}::{subject_part}::{date_part}"


def find_duplicate(title: str, source_id: str | None = None,
                   source_type: str | None = None,
                   sender: str | None = None,
                   subject: str | None = None) -> dict | None:
    """Check if a similar task already exists (active, suggested, or dismissed).

    Three-level matching:
    1. Primary: exact source_id match (most reliable)
    2. Secondary: source_type + sender + subject-prefix match (for emails)
    3. Tertiary: title-prefix fallback (first 40 chars)
    """
    all_tasks = list_tasks()
    title_lower = title.lower().strip()

    for task in all_tasks:
        # Primary: exact source_id match
        if source_id and task.get("source_id") and task["source_id"] == source_id:
            return task

    # Secondary: source_type + sender + subject-prefix
    if source_type and sender and subject:
        sender_lower = sender.strip().lower()
        subject_prefix = subject.strip().lower()[:30]
        for task in all_tasks:
            task_sid = task.get("source_id") or ""
            if task_sid.startswith(f"{source_type}::"):
                parts = task_sid.split("::")
                if len(parts) >= 3:
                    if parts[1] == sender_lower and parts[2].startswith(subject_prefix):
                        return task

    # Tertiary: title-prefix fallback
    for task in all_tasks:
        if task["title"].lower().strip()[:40] == title_lower[:40]:
            return task

    return None


def should_create_suggestion(
    title: str,
    source_id: str | None = None,
    source_type: str | None = None,
    sender: str | None = None,
    subject: str | None = None,
) -> bool:
    """Return True if this suggestion doesn't already exist."""
    existing = find_duplicate(title, source_id, source_type, sender, subject)
    if existing is None:
        return True
    # Don't re-suggest dismissed items
    if existing["status"] == "dismissed":
        return False
    # Don't duplicate existing items
    return False
