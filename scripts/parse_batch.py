"""Batch parse the current unparsed tasks."""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "claudetodo.db"
conn = sqlite3.connect(str(DB_PATH))
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

pratap_people = json.dumps([{
    "name": "Pratap Ladhani",
    "email": "Pratap.Ladhani@microsoft.com",
    "role": "Principal PM Manager",
    "alternatives": [
        {"name": "Pratap Rao Rayachoti", "email": "prayachoti@microsoft.com", "role": "Software Engineer II"},
        {"name": "Pratap Singha", "email": "Pratap.Singha@microsoft.com", "role": "Senior Technical PM"},
        {"name": "Pratap Chandar", "email": "prjoseph@microsoft.com", "role": "Senior Software Engineer"},
    ],
}])

saurabh_people = json.dumps([{
    "name": "Saurabh Pant",
    "email": "spant@microsoft.com",
    "role": "GM, Copilot Acceleration Team",
    "alternatives": [
        {"name": "Saurabh Kuchhal", "email": "sakuchha@microsoft.com", "role": "Principal Solution Architect"},
        {"name": "Saurabh Gupta", "email": "sauragupta@microsoft.com", "role": "Principal Group Product Manager"},
        {"name": "Saurabh Surana", "email": "sasurana@microsoft.com", "role": "Principal Architect"},
    ],
}])

pratap_aamer_people = json.dumps([
    {
        "name": "Pratap Ladhani",
        "email": "Pratap.Ladhani@microsoft.com",
        "role": "Principal PM Manager",
        "alternatives": [
            {"name": "Pratap Rao Rayachoti", "email": "prayachoti@microsoft.com", "role": "Software Engineer II"},
            {"name": "Pratap Singha", "email": "Pratap.Singha@microsoft.com", "role": "Senior Technical PM"},
        ],
    },
    {
        "name": "Aamer Kaleem",
        "email": "Aamer.Kaleem@microsoft.com",
        "role": "Principal PM Manager",
        "alternatives": [
            {"name": "Aamer Shedam", "email": "aamer.shedam@microsoft.com", "role": "Sr Onboard Mgr"},
            {"name": "Aamer Mohammed", "email": "abmoham@microsoft.com", "role": "Principal Software Engineer"},
        ],
    },
])

updates = [
    # #1: "this is a new task" — generic, no people/date
    (1, "New task", "", 3, None, None, "manual", None,
     "Break this down into a specific, actionable next step to make progress."),

    # #2: "schedule a meeting this week with saurabh"
    (2, "Schedule meeting with Saurabh Pant this week",
     "Set up a meeting with Saurabh Pant (GM, Copilot Acceleration Team). Check mutual calendar availability for this week and send an invite.",
     3, "2026-02-20", saurabh_people, "meeting",
     "Meeting to be scheduled with Saurabh Pant",
     "Check Saurabh's calendar via /schedule-meeting, then send an Outlook invite with a clear agenda. Treat tentative blocks as available."),

    # #11: duplicate of #10 — "schedule a meeting by next thurs with pratap"
    (11, "Schedule meeting with Pratap Ladhani by Thursday",
     "Set up a meeting with Pratap Ladhani (Principal PM Manager, Power CAT) before Thursday Feb 19.",
     3, "2026-02-19", pratap_people, "meeting",
     "Meeting to be scheduled with Pratap Ladhani",
     "Use /schedule-meeting to find mutual availability, then send the Outlook invite with a clear agenda."),

    # #12: duplicate
    (12, "Schedule meeting with Pratap Ladhani by Thursday",
     "Set up a meeting with Pratap Ladhani (Principal PM Manager, Power CAT) before Thursday Feb 19.",
     3, "2026-02-19", pratap_people, "meeting",
     "Meeting to be scheduled with Pratap Ladhani",
     "Use /schedule-meeting to find mutual availability, then send the Outlook invite with a clear agenda."),

    # #13: duplicate
    (13, "Schedule meeting with Pratap Ladhani by Thursday",
     "Set up a meeting with Pratap Ladhani (Principal PM Manager, Power CAT) before Thursday Feb 19.",
     3, "2026-02-19", pratap_people, "meeting",
     "Meeting to be scheduled with Pratap Ladhani",
     "Use /schedule-meeting to find mutual availability, then send the Outlook invite with a clear agenda."),

    # #14: "schedule a meeting with pratap and aamer this week"
    (14, "Schedule meeting with Pratap Ladhani and Aamer Kaleem this week",
     "Set up a meeting with Pratap Ladhani (Principal PM Manager) and Aamer Kaleem (Principal PM Manager, CAPE). Find mutual availability for all three calendars this week.",
     3, "2026-02-20", pratap_aamer_people, "meeting",
     "Meeting to be scheduled with Pratap Ladhani and Aamer Kaleem",
     "Use /schedule-meeting to check all three calendars. With multiple attendees, morning slots tend to have better availability. Send one invite to both."),
]

for u in updates:
    task_id = u[0]
    conn.execute(
        """UPDATE tasks
           SET title=?, description=?, priority=?, due_date=?,
               key_people=?, source_type=?, related_meeting=?,
               coaching_text=?, parse_status='parsed', updated_at=?
           WHERE id=?""",
        (u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], now, task_id),
    )
    print(f"Parsed #{task_id}: {u[1]}")

conn.commit()
conn.close()
print("Done — all tasks parsed.")
