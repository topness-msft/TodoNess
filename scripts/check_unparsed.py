"""Check for unparsed tasks and stale refresh, output a message if action needed.

Used as a Claude Code Stop hook to auto-trigger parsing or refresh.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "claudetodo.db"
SYNC_REQUEST_FILE = Path(__file__).resolve().parent.parent / "data" / ".sync_requested"


def main():
    # Check for sync request marker (written by dashboard or 30-min periodic timer)
    if SYNC_REQUEST_FILE.exists():
        # Don't delete the marker here — /todo-refresh clears it
        print(json.dumps({
            "decision": "block",
            "reason": (
                "A TodoNess sync is due. "
                "Run /todo-refresh to scan M365 for new items."
            )
        }))
        return

    if not DB_PATH.exists():
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        # Check unparsed tasks
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE parse_status IN ('unparsed', 'queued') AND status NOT IN ('deleted', 'completed')"
        ).fetchone()
        unparsed_count = row["cnt"] if row else 0

        if unparsed_count > 0:
            conn.close()
            print(json.dumps({
                "decision": "block",
                "reason": (
                    f"There {'is' if unparsed_count == 1 else 'are'} {unparsed_count} unparsed "
                    f"task{'s' if unparsed_count != 1 else ''} in TodoNess. "
                    f"Run /todo-parse to enrich them."
                )
            }))
            return

        # Check for stale refresh during work hours (8am-6pm weekdays)
        now = datetime.now()
        is_work_hours = (
            now.weekday() < 5  # Monday-Friday
            and 8 <= now.hour < 18  # 8am-6pm
        )

        if is_work_hours:
            last_sync = conn.execute(
                "SELECT synced_at FROM sync_log WHERE sync_type IN ('full_scan', 'flagged_emails') ORDER BY synced_at DESC LIMIT 1"
            ).fetchone()

            if last_sync and last_sync["synced_at"]:
                last_dt = datetime.fromisoformat(
                    last_sync["synced_at"].replace("Z", "+00:00")
                )
                hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_since > 4:
                    conn.close()
                    print(json.dumps({
                        "decision": "notify",
                        "reason": (
                            f"Last TodoNess refresh was {hours_since:.0f} hours ago. "
                            f"Consider running /todo-refresh to check for new items."
                        )
                    }))
                    return
            else:
                # No sync ever recorded
                conn.close()
                print(json.dumps({
                    "decision": "notify",
                    "reason": (
                        "TodoNess has never been synced with M365. "
                        "Run /todo-refresh to scan for actionable items."
                    )
                }))
                return

        conn.close()
    except Exception:
        return


if __name__ == "__main__":
    main()
