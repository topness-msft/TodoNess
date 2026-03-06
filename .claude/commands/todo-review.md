---
description: Interactive review of tasks needing attention
---

Walk through tasks that need attention and take action.

Steps:
1. Query for tasks needing attention:
   - Overdue tasks (due_date < today, status != completed/dismissed)
   - Suggested tasks (status = 'suggested') — need promote/dismiss decision
   - Stale active tasks (suggestion_refreshed_at > 24 hours ago or NULL)

2. Present each group with counts:
   ```
   TodoNess Review

   Overdue (2)
   Pending Suggestions (3)
   Stale Active Tasks (1)
   ```

3. For each task in priority order, present:
   - Task title, priority, due date, source
   - Coaching text if available
   - Available actions based on status

4. Ask the user what action to take:
   - Suggested tasks: Promote to active? Dismiss? Skip?
   - Overdue tasks: Mark complete? Update due date? Dismiss?
   - Stale tasks: Refresh context via WorkIQ? Skip?

5. If refreshing context, call `ask_work_iq` with task-specific query and update coaching_text.

6. Show summary of actions taken.
