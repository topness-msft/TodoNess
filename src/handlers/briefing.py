"""Briefing page handler and API — Chief of Staff briefing."""

import hashlib
import json
import logging
import os

import tornado.web

from ..services.briefing import (
    get_cached_briefing,
    is_stale,
    mark_refresh_started,
)
from ..services.claude_runner import run_copilot

logger = logging.getLogger(__name__)

BRIEFING_TIMEOUT = 600  # 10 min — WorkIQ + narrative generation


class BriefingPageHandler(tornado.web.RequestHandler):
    """GET /briefing — serve the briefing HTML with API adapter injected."""

    def get(self):
        static_dir = self.application.settings.get("static_path", "static")
        mock_path = os.path.join(static_dir, "mock-briefing.html")

        with open(mock_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Inject the API adapter script with cache-busting hash
        adapter_path = os.path.join(static_dir, "js", "briefing-api.js")
        try:
            with open(adapter_path, "rb") as af:
                h = hashlib.md5(af.read()).hexdigest()[:8]
        except FileNotFoundError:
            h = "0"
        adapter_tag = f'<script src="/static/js/briefing-api.js?v={h}"></script>'
        html = html.replace("</body>", adapter_tag + "\n</body>")

        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        self.write(html)


class BriefingAPIHandler(tornado.web.RequestHandler):
    """GET /api/briefing — return cached briefing data."""

    def get(self):
        cached = get_cached_briefing()
        if not cached:
            self.write({
                "status": "empty",
                "content": None,
                "generated_at": None,
                "is_stale": True,
            })
            return

        self.write({
            "status": cached["status"],
            "content": cached["content"],
            "generated_at": cached["generated_at"],
            "is_stale": cached["is_stale"],
            "refresh_started_at": cached.get("refresh_started_at"),
            "error_message": cached.get("error_message"),
        })


class BriefingRefreshHandler(tornado.web.RequestHandler):
    """POST /api/briefing/refresh — trigger a briefing regeneration."""

    def post(self):
        mark_refresh_started()
        result = run_copilot(
            "/briefing-generate",
            label="briefing",
            timeout=BRIEFING_TIMEOUT,
        )
        if result["ok"]:
            self.write({"ok": True, "message": "Briefing refresh started"})
        else:
            self.write({"ok": False, "message": result["message"]})
