# TodoNess

Local AI-powered task manager that integrates with Microsoft 365 via WorkIQ MCP.

TodoNess scans your Teams messages, meetings, and flagged emails to surface actionable items as suggested tasks. It provides AI coaching, follow-up drafting, and meeting prep through a web dashboard.

## Prerequisites

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- WorkIQ MCP configured in Claude Code settings

## Quick Start

```bash
# Start the dashboard server
python -m src.app

# Open http://localhost:8766
```

## Usage

The dashboard runs as a local web server. AI features (scanning, parsing, skills) run through Claude Code slash commands:

| Command | Purpose |
|---------|---------|
| `/todo` | Status summary and dashboard URL |
| `/todo-add "text"` | Add a task with natural language parsing |
| `/todo-parse` | Parse tasks added via the dashboard quick-add |
| `/todo-refresh` | Scan M365 for new actionable items |
| `/todo-review` | Review tasks needing attention |

Skills generate contextual drafts for individual tasks:

| Skill | Purpose |
|-------|---------|
| `respond-email` | Draft an email response |
| `schedule-meeting` | Suggest meeting times |
| `teams-message` | Draft a Teams message |
| `follow-up` | Draft a follow-up message |
| `prepare` | Build meeting/presentation prep notes |

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture, database schema, and development notes.

```
Claude Code Commands (/todo-refresh, /todo-add, skills)
  |-- calls WorkIQ MCP for M365 data
  |-- writes results to SQLite

SQLite DB (data/claudetodo.db)
  |-- tasks, task_context, refresh_schedule, sync_log

Tornado Web Server (localhost:8766)
  |-- reads SQLite, serves dashboard + REST API + WebSocket
```

Zero external dependencies beyond Python's standard library.
