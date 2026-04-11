---
name: ingest-tasks
description: >
  Processes Todoist task data to detect avoidance patterns and task
  completion rates for Clarity. Invoke manually with /ingest-tasks
  when you want to analyse task behaviour for a specific week.
invocation: manual
allowed-tools:
  - Read
  - Write
---

# Task ingestion playbook

## What to extract

### Completion signals
- Tasks completed vs total tasks (completion rate)
- Tasks moved/rescheduled more than twice (avoidance signal)
- Tasks sitting unstarted for 7+ days
- Personal tasks vs work tasks ratio

### Pattern signals
- Which days have zero task completions
- Category of most-avoided tasks (financial, personal, communication)
- Correlation between high meeting days and task completion rate

## Output schema
Write to .clarity-cache/tasks-{YYYY-MM-DD}.json:

```json
{
  "week_start": "YYYY-MM-DD",
  "total_tasks": 0,
  "completed": 0,
  "completion_rate": 0.0,
  "moved_tasks": [],
  "avoided_tasks": [],
  "zero_completion_days": [],
  "avoidance_categories": []
}
```