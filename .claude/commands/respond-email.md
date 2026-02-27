---
description: Draft an email response for email-sourced tasks
---

Draft an email reply based on a task's context, people, and source material.

**Input:** $ARGUMENTS (task ID — **required**)

Today's date is $CURRENT_DATE.

## Step 0: Validate input

If `$ARGUMENTS` is empty or not a valid integer, stop immediately with:
> **Usage:** `/respond-email <task_id>`
>
> Example: `/respond-email 20`

## Step 1: Read the task from SQLite

```python
import sqlite3

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
conn.row_factory = sqlite3.Row
task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
conn.close()
```

If the task doesn't exist, stop with: "Task #[id] not found."

Extract: `key_people`, `user_notes`, `description`, `title`, `source_snippet`, `source_url`, `related_meeting`.

## Step 2: Gather email context from WorkIQ

Build a WorkIQ query to get the relevant email thread. Use the key_people names and task description to find the right context:

1. If `source_snippet` or `source_url` exists, query: "Show me the recent email thread about [topic from title/description] with [key_people names]. Include the last 2-3 messages so I can see what was said."
2. If no source context, query: "What are my recent emails with [key_people names] about [topic from title/description]? Show me the most recent thread."

Also check `user_notes` for any tone, points, or constraints the user wants in the reply.

## Step 3: Draft the email reply

Based on the email context and task details, draft a professional email reply.

**You MUST output your draft using this EXACT format, including the `<<<SKILL_OUTPUT>>>` and `<<<END_SKILL_OUTPUT>>>` marker lines. These markers are required for the dashboard to capture your output:**

```
<<<SKILL_OUTPUT>>>
To: [name] <[email]>
Subject: Re: [inferred or from source]

[Draft body]

---
Tone: [professional/casual/urgent — inferred from context]
Key points addressed:
- [point 1]
- [point 2]
<<<END_SKILL_OUTPUT>>>
```

**Guidelines:**
- Keep it concise — aim for 3-5 sentences unless the context demands more
- Mirror the tone of the original thread
- If `user_notes` specify points to address, make sure they're all covered
- Include a clear call-to-action or next step at the end
- Use the person's first name in the greeting (e.g. "Hi Mehdi,")
- Do NOT include agenda items or coaching — those stay in coaching_text

Your output will be automatically saved to the dashboard. No further action needed.
