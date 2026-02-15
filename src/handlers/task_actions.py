"""Action handlers: promote, dismiss, status transitions."""

import json
import tornado.web

from ..models import (
    promote_task, dismiss_task, complete_task, start_task,
    transition_task, get_task, update_task,
)
from .ws import broadcast


class TaskActionHandler(tornado.web.RequestHandler):
    """POST /api/tasks/<id>/action — perform a lifecycle action."""

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def post(self, task_id):
        try:
            body = json.loads(self.request.body)
        except (json.JSONDecodeError, TypeError):
            self.set_status(400)
            self.write(json.dumps({"error": "Invalid JSON"}))
            return

        action = body.get("action", "")
        tid = int(task_id)

        action_map = {
            "promote": promote_task,
            "dismiss": dismiss_task,
            "complete": complete_task,
            "start": start_task,
        }

        if action in action_map:
            try:
                task = action_map[action](tid)
            except ValueError as e:
                self.set_status(400)
                self.write(json.dumps({"error": str(e)}))
                return
        elif action == "transition":
            new_status = body.get("status")
            if not new_status:
                self.set_status(400)
                self.write(json.dumps({"error": "status required for transition"}))
                return
            try:
                task = transition_task(tid, new_status)
            except ValueError as e:
                self.set_status(400)
                self.write(json.dumps({"error": str(e)}))
                return
        else:
            self.set_status(400)
            self.write(json.dumps({
                "error": f"Unknown action '{action}'",
                "valid": list(action_map.keys()) + ["transition"],
            }))
            return

        if task is None:
            self.set_status(404)
            self.write(json.dumps({"error": "Task not found"}))
            return

        self.write(json.dumps({"task": task}))
        broadcast({"type": "task_updated", "task": task})


class TaskRefreshHandler(tornado.web.RequestHandler):
    """POST /api/tasks/<id>/refresh — queue task for re-parsing by Claude."""

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def post(self, task_id):
        tid = int(task_id)
        task = get_task(tid)
        if not task:
            self.set_status(404)
            self.write(json.dumps({"error": "Task not found"}))
            return

        # Set to 'queued' so UI shows progression; the Stop hook / todo-parse
        # will move it to 'parsing' then 'parsed'
        updated = update_task(tid, parse_status="queued")
        self.write(json.dumps({"task": updated}))
        broadcast({"type": "task_updated", "task": updated})
