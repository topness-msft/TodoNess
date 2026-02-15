---
description: Parse unparsed tasks — Claude reads raw text and enriches with structured fields
---

Parse tasks that were added via the dashboard input bar and need enrichment.

## Step 1: Fetch unparsed tasks

```python
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
conn.row_factory = sqlite3.Row
tasks = conn.execute("SELECT id, raw_input, title, description, key_people, action_type, user_notes, source_type, parse_status FROM tasks WHERE parse_status IN ('unparsed', 'queued') AND status NOT IN ('deleted', 'completed')").fetchall()
conn.close()
```

If no unparsed tasks, say "All tasks are already parsed!" and stop.

## Step 2: For each unparsed task, mark as 'parsing'

```python
conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
conn.execute("UPDATE tasks SET parse_status = 'parsing', updated_at = ? WHERE id = ?", (now, task_id))
conn.commit()
conn.close()
```

## Step 2b: Check if this is a coaching-only re-parse

A task needs **coaching-only** re-parse if it already has `title`, `description`, and `key_people` populated (i.e. it was previously fully parsed). This happens when the user changes the `action_type` or edits the description from the dashboard.

For coaching-only tasks, **skip Step 3** entirely. Jump straight to **Step 3b** to re-generate only `coaching_text`.

## Step 3: Full parse — reason about the raw_input

For each task's `raw_input`, use your intelligence to infer ALL of the following. Today's date is $CURRENT_DATE.

- **title**: A clean, concise task title (imperative form, e.g. "Schedule meeting with Pratap by Wednesday")
- **description**: A fuller description of what the task involves, including any implied sub-steps. Be helpful and specific.
- **priority**: Integer 1-5 based on urgency cues:
  - 1 = urgent/ASAP/critical/blocker
  - 2 = important/soon/time-sensitive
  - 3 = normal (default)
  - 4 = low importance
  - 5 = backlog/whenever/no rush
- **due_date**: ISO date (YYYY-MM-DD) resolved from any time references. "Next Wednesday" → calculate from today. "End of week" → Friday. "Tomorrow" → tomorrow. null if none implied.
- **key_people**: A JSON array of resolved people. For each name mentioned, call `ask_work_iq` with "Who is [name]? Give me the top 3-4 most likely matches with full name, email, and role." Pick the best match and store alternatives. Format:
  ```json
  [{"name": "John Wheat", "email": "john.wheat@contoso.com", "role": "PM",
    "alternatives": [
      {"name": "John Smith", "email": "john.smith@contoso.com", "role": "Engineer"},
      {"name": "John Adams", "email": "john.adams@contoso.com", "role": "Designer"}
    ]}]
  ```
  Store as a JSON string in the `key_people` column. If WorkIQ can't resolve, store `[{"name": "John", "alternatives": []}]`.
- **source_type**: One of 'email', 'meeting', 'chat', 'manual'. For dashboard-entered tasks, infer from what the user described (e.g. "reply to John's email" → 'email', "schedule a meeting" → 'meeting', otherwise 'manual'). Note: tasks created by /todo-refresh already have the correct source_type set from WorkIQ — don't overwrite those.
- **related_meeting**: If a meeting is mentioned, describe it. Use WorkIQ if helpful: call `ask_work_iq` with "What meetings do I have related to [topic]?" **Important:** After resolving people in the key_people step, always use their full resolved names (e.g. "Pratap Ladhani" not "Pratap") in all subsequent WorkIQ queries for more precise results.
- **action_type**: Classify the task into one of these action types based on intent:

  | action_type | Infer when... |
  |---|---|
  | `schedule-meeting` | scheduling, finding time, setting up a meeting |
  | `respond-email` | replying to, responding to, drafting an email |
  | `review-document` | reviewing, reading, giving feedback on a doc/PR/report |
  | `follow-up` | checking in, nudging, getting a status update |
  | `prepare` | preparing for a meeting, presentation, demo |
  | `general` | default fallback |

- **coaching_text**: Generate coaching tailored to the `action_type` and `user_notes` (see Step 3b).

## Step 3b: Generate coaching_text (used by both full parse and coaching-only re-parse)

Generate `coaching_text` based on the task's `action_type`, `description`, `key_people`, and `user_notes`. **Always read `user_notes`** and incorporate them into coaching.

Tailor coaching by action type:

- **schedule-meeting**: Mention calendar availability for key_people (query WorkIQ if helpful), suggest duration/agenda. If `user_notes` contain agenda items → use them. If notes mention a duration → suggest that duration. Note the `/schedule-meeting` skill is available to help.
- **respond-email**: Suggest key points to address based on the source/description. Recommend appropriate tone. Note the `/respond-email` skill is available to help draft the reply.
- **review-document**: Suggest focus areas for the review, time-box the review (e.g. "aim for 30 min").
- **follow-up**: Suggest timeline based on priority/due_date, draft a follow-up outline.
- **prepare**: List concrete prep steps, suggest materials to gather, reference related_meeting if set.
- **general**: Break into 2-3 concrete next steps.

**Important:** Always use full resolved names (e.g. "Pratap Ladhani" not "Pratap") in the coaching text so inline people pills render correctly in the dashboard. If `user_notes` contain context (agenda, constraints, preferences), weave that context into the coaching.

## Step 3c: Auto-invoke action-specific enrichment

After generating coaching_text, auto-generate `skill_output` based on `action_type`. This runs the same logic as the standalone skill but inline during parsing. If `key_people` is empty, skip enrichment and set `skill_output` to null.

Build a name list from `key_people` JSON for all queries below.

| action_type | WorkIQ query | skill_output format |
|---|---|---|
| `schedule-meeting` | "Shared calendar availability for [names] [this week / by due_date]. Treat tentative as available. Only show slots during each person's Outlook working hours. Show free slots >= 30 min." | `Suggested meeting slots:\n1. [Day], [Time]-[Time] ([dur])\n...\nDuration: [from user_notes or 30 min]\nAttendees: [names]` |
| `respond-email` | "Recent email thread about [topic] with [names]. Show last 2-3 messages." | `To: [name] <[email]>\nSubject: Re: [topic]\n\n[Draft body]\n---\nTone: [inferred]\nKey points: [bullets]` |
| `follow-up` | "Most recent emails and Teams messages with [names] about [topic]. When was the last interaction?" | `Channel: [Email/Teams based on source_type]\nTo: [name]\n\n[Draft follow-up]\n---\nLast interaction: [date]\nUrgency: [from due_date]` |
| `prepare` | "Agenda and attendees for [related_meeting]. Recent docs related to [topic]." | `Prep Notes: [event]\nBefore:\n[ ] [item]\nTalking points:\n- [point]\nMaterials:\n- [doc]\nTime estimate: [X min]` |
| `general`, `review-document` | No auto-enrichment | `skill_output` = null |

**Guidelines:**
- Check `user_notes` for constraints, tone, specific asks — weave into the output
- For `follow-up` with `source_type = 'chat'`: draft as a Teams message (casual tone)
- For `follow-up` with `source_type = 'email'` or `'meeting'`: draft as email
- Store result in `skill_output` (NOT coaching_text)

If the action_type doesn't qualify or key_people is empty, set `skill_output` to null (don't carry over stale data on re-parse).

## Step 4: Write the structured fields back

**For full parse:**

```python
conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
conn.execute(
    """UPDATE tasks
       SET title=?, description=?, priority=?, due_date=?,
           key_people=?, source_type=?, related_meeting=?,
           coaching_text=?, action_type=?, skill_output=?,
           suggestion_refreshed_at=?, parse_status='parsed', updated_at=?
       WHERE id=?""",
    (title, description, priority, due_date, key_people, source_type,
     related_meeting, coaching_text, action_type, skill_output, now, now, task_id)
)
conn.commit()
conn.close()
```

**For coaching-only re-parse:**

```python
conn = sqlite3.connect('$PROJECT_ROOT/data/claudetodo.db')
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
conn.execute(
    """UPDATE tasks
       SET coaching_text=?, skill_output=?, suggestion_refreshed_at=?,
           parse_status='parsed', updated_at=?
       WHERE id=?""",
    (coaching_text, skill_output, now, now, task_id)
)
conn.commit()
conn.close()
```

## Step 5: Show summary

For each parsed task, display:
- Task ID and clean title
- Priority (P1-P5)
- Due date if set
- Key people if identified
- Action type (with icon)
- Coaching tip
- Skill output (if generated — e.g. scheduling slots for schedule-meeting)
- Source type
- Whether it was a full parse or coaching-only refresh

End with: "Parsed N task(s). Run /todo to see your updated task list."
