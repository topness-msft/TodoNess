"""Query templates for WorkIQ MCP integration.

These templates are used by Claude Code commands (/todo-refresh, /todo-add)
to query WorkIQ for M365 context. The Tornado server never calls these directly.
"""

# ── Query Templates ────────────────────────────────────────────────────────

FULL_SCAN = (
    "What items across my Inbox emails, Teams messages, and meetings need my attention or action? "
    "For ALL email searches, only look in my Inbox folder (not Sent, Archive, or other folders). "
    "Include: "
    "(1) ALL emails currently flagged in my Inbox (no time limit — include every flagged email), "
    "(2) any emails in my Inbox categorized as 'TodoNess' (no time limit), "
    "(3) emails in my Inbox from the last {days} days asking for my response that I haven't replied to, "
    "(4) Teams messages from the last 3 days directed at me or @mentioning me that I haven't responded to, "
    "(5) action items from meetings in the last 3 days assigned to me or that I committed to, "
    "(6) emails or Teams messages I SENT in the last {days} days that contain a question or request "
    "where the recipient hasn't responded yet. "
    "For each item, give me: source type (email/teams/meeting), subject or topic, "
    "person name and email, date, and a brief summary of what's needed."
)

EMAIL_THREAD = (
    "Show me the full email thread for the email with subject '{subject}' "
    "from {sender}. Include all replies and the most recent message."
)

PERSON_CONTEXT = (
    "What recent interactions have I had with {person_name}? "
    "Include recent emails, meetings, and any pending items."
)

CALENDAR_AVAILABILITY = (
    "What does my calendar look like for {date_range}? "
    "Show me free and busy slots."
)

TASK_REFRESH = (
    "Regarding '{task_title}': {task_description} "
    "What's the latest context from my emails and meetings about this? "
    "Has anything changed since {last_refresh}?"
)


def format_query(template: str, **kwargs) -> str:
    """Format a query template with the given parameters."""
    return template.format(**kwargs)
