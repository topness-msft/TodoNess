---
name: respond-email
description: Draft an email response for an email-sourced task
triggers:
  - task sourced from email
  - user asks to reply to email
  - "draft response" or "reply to" in context
---

# Respond to Email

Draft a contextual email response for a task that originated from an email.

## Steps

1. **Load task context**: Read the task from TodoNess SQLite database at `$PROJECT_ROOT/data/claudetodo.db`. Get the task details and any entries from the task_context table.

2. **Get email thread**: Use WorkIQ to retrieve the full email thread:
   - Call `ask_work_iq`: "Show me the full email thread for the email with subject '[task source_snippet or title]'. Include all replies and the most recent message."

3. **Get calendar context**: Check if there are related meetings:
   - Call `ask_work_iq`: "Do I have any upcoming meetings related to '[task title]' or with [task key_people]?"

4. **Draft response**: Based on the email thread and calendar context, draft a professional email response that:
   - Addresses the key points from the most recent email
   - References relevant meetings or deadlines
   - Maintains appropriate tone and formality
   - Is concise and actionable

5. **Save context**: Store the email thread and draft as task_context entries in SQLite.

6. **Present to user**: Show the draft response and ask if they want to modify it.
