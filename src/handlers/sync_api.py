"""Sync status handler — marker-file approach.

The Tornado server writes a .sync_requested marker file on demand or every
30 min via PeriodicCallback.  Claude's Stop hook (check_unparsed.py) detects
the marker and tells Claude to run /todo-refresh.  No subprocess spawning.
"""

import json
import logging
import tornado.web
from pathlib import Path

from ..models import get_last_sync

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNC_REQUEST_FILE = PROJECT_ROOT / "data" / ".sync_requested"


def request_sync() -> dict:
    """Write the sync marker file so the Stop hook triggers /todo-refresh."""
    try:
        SYNC_REQUEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYNC_REQUEST_FILE.write_text("requested")
        logger.info("Sync marker written")
        return {"ok": True, "message": "Sync requested. Will run on next Claude interaction."}
    except Exception as e:
        logger.error(f"Failed to write sync marker: {e}")
        return {"ok": False, "message": str(e)}


def is_sync_pending() -> bool:
    """Check if a sync request marker is waiting."""
    return SYNC_REQUEST_FILE.exists()


class SyncStatusHandler(tornado.web.RequestHandler):
    """GET /api/sync-status — last sync info + pending state.
    POST /api/sync-status — request a sync (writes marker file).
    """

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def get(self):
        last_sync = get_last_sync("full_scan") or get_last_sync("flagged_emails")
        self.write(json.dumps({
            "last_sync": dict(last_sync) if last_sync else None,
            "sync_pending": is_sync_pending(),
        }))

    def post(self):
        result = request_sync()
        if not result["ok"]:
            self.set_status(500)
        self.write(json.dumps(result))
