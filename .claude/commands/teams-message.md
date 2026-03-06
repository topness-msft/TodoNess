---
description: Draft a Teams message for chat-based tasks
---

Draft a Teams message based on a task's context and people.

**Input:** $ARGUMENTS (task ID — **required**)

Today's date is $CURRENT_DATE.

## Step 0: Validate input

If `$ARGUMENTS` is empty or not a valid integer, stop immediately with:
> **Usage:** `/teams-message <task_id>`
>
> Example: `/teams-message 21`

## Step 1: Read the task from SQLite

```python
import sqlite3

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
conn.row_factory = sqlite3.Row
task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
conn.close()
```

If the task doesn't exist, stop with: "Task #[id] not found."

Extract: `key_people`, `user_notes`, `description`, `title`, `related_meeting`.

## Step 2: Gather context from WorkIQ

Query WorkIQ to understand the conversation context:

1. "What are my recent Teams chats with [key_people names] about [topic from title/description]? Show the most recent messages."
2. If `related_meeting` is set, also query: "What was discussed in [related_meeting] with [key_people names]?"

Check `user_notes` for specific points or tone the user wants.

## Step 3: Draft the Teams message

Based on context and task details, draft a Teams-appropriate message.

**You MUST output your draft using this EXACT format, including the `<<<SKILL_OUTPUT>>>` and `<<<END_SKILL_OUTPUT>>>` marker lines. These markers are required for the dashboard to capture your output:**

```
<<<SKILL_OUTPUT>>>
To: [name] (via Teams)

[Draft message]

---
Tone: [casual/direct/detailed — inferred from context]
Purpose: [what this message aims to accomplish]
<<<END_SKILL_OUTPUT>>>
```

**Guidelines:**
- Teams messages should be **shorter and more conversational** than emails
- Lead with the key point or ask — don't bury it
- Use bullet points if there are multiple items
- If `user_notes` specify what to discuss, build the message around those points
- For a quick ping, keep it to 1-2 sentences
- For a more substantive message, use a brief opener + bullets + clear ask
- Don't over-formalize — "Hey [first name]," is fine for Teams

Your output will be automatically saved to the dashboard. No further action needed.
