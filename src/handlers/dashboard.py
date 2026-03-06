"""Dashboard page handler — serves the main HTML UI."""

import tornado.web

from ..models import get_stats, get_last_sync


class DashboardHandler(tornado.web.RequestHandler):
    """GET / — render the TodoNess dashboard."""

    def get(self):
        stats = get_stats()
        last_sync = get_last_sync()
        self.render(
            "dashboard.html",
            stats=stats,
            last_sync=last_sync,
        )
