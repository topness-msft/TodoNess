# TodoNess - Project Notes

## Overview
TodoNess is a local AI-powered task manager that integrates with Microsoft 365 via WorkIQ MCP. It reads M365 context (flagged emails, meetings, calendar) to surface actionable suggestions, lets users manage tasks through a web dashboard, and provides AI coaching on each task.

## Technology Stack
- **Runtime:** Python 3.11
- **Web Framework:** Tornado 6.5
- **Templating:** Jinja2 3.1.6
- **Database:** SQLite3 (WAL mode)
- **Dependencies:** Zero external — all pre-installed

## Architecture
```
Claude Code Commands (/todo-refresh, /todo-review)
  ↕ calls WorkIQ MCP    ↕ writes SQLite
SQLite DB (data/claudetodo.db)
  tasks | task_context | refresh_schedule | sync_log
Tornado Web Server (localhost:8766)
  Reads SQLite → serves dashboard + REST API + WebSocket
```

WorkIQ queries happen inside Claude Code commands only. The Tornado server never calls WorkIQ directly.

## Key Files
- `src/db.py` — SQLite schema, connection management
- `src/models.py` — Task CRUD, lifecycle (promote/dismiss/complete/start), context, sync log
- `src/app.py` — Tornado routes, entry point (port 8766)
- `src/handlers/task_api.py` — REST API: /api/tasks, /api/tasks/<id>, /api/stats
- `src/handlers/task_actions.py` — POST /api/tasks/<id>/action
- `src/handlers/ws.py` — WebSocket at /ws for live updates
- `src/handlers/dashboard.py` — GET / renders dashboard
- `src/services/workiq_queries.py` — M365 query templates (FULL_SCAN single-call approach)
- `src/services/suggestion_engine.py` — Deduplication logic (source_id composite keys)
- `src/services/refresh_scheduler.py` — Adaptive refresh intervals

## Commands
| Command | Purpose | Uses WorkIQ? |
|---------|---------|-------------|
| `/todo` | Status summary + dashboard URL | No |
| `/todo-add "text"` | Add task via NL, Claude parses + WorkIQ resolves | Yes |
| `/todo-parse` | Parse unparsed tasks from dashboard | Yes |
| `/todo-refresh` | Full M365 scan: single WorkIQ call → suggested tasks | Yes |
| `/todo-review` | Interactive review of tasks needing attention | Yes |

## Skills
- `respond-email` — Draft email response for email-sourced tasks
- `schedule-meeting` — Suggest meeting times based on calendar availability
- `teams-message` — Draft a Teams message for chat-based tasks
- `follow-up` — Draft a follow-up message for tasks needing a check-in
- `prepare` — Build preparation notes for meetings/presentations

## Database Schema
Four tables: `tasks`, `task_context`, `refresh_schedule`, `sync_log`. See `src/db.py` for full schema.

## Task Status Flow
- **suggested** → active, dismissed
- **active** → in_progress, completed, dismissed
- **in_progress** → active, completed
- **completed** → active
- **dismissed** → active, suggested

## Parse Status Flow (dashboard input)
unparsed → queued → parsing → parsed

## Sync Flow (/todo-refresh)
1. Check sync_log for last sync time → determine scan window (1-7 days)
2. Single WorkIQ FULL_SCAN call covering: flagged emails, unanswered emails, Teams messages, meeting action items, outbound asks
3. Parse results → dedup via source_id composite key → create as `suggested` tasks
4. Parse any unparsed tasks (same as /todo-parse)
5. Log to sync_log with result summary JSON

## Running
```bash
# Start the TodoNess dashboard
python -m src.app 8766
# Open http://localhost:8766
```
