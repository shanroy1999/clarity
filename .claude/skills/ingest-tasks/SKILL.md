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

## Critical privacy rule — mirrors email and calendar skills
NEVER store task titles or descriptions. A user's task list
("call therapist", "pay overdue tax bill", "email lawyer") is as
sensitive as their email body. Work only with derived signals:
category, count, timing, and move frequency.

## Category classification (no titles stored)
Classify each task into one of these categories based on keywords,
then discard the title:
- financial: bill, tax, invoice, bank, payment, rent, insurance
- personal: family member names, doctor, therapist, health, appointment
- communication: call, email, message, reply, text, reach out
- work: meeting, project, deadline, review, report, presentation
- admin: forms, documents, renewal, registration, subscription

## What to extract

### Completion signals
- Total tasks per category vs completed per category
- Overall completion rate (completed / total)
- Tasks moved or rescheduled more than twice — store count and category only
- Tasks unstarted for 7+ days — store count and category only

### Pattern signals
- Which days have zero task completions
- Most-avoided category (highest move rate)
- Correlation between high-meeting days and zero-completion days

## Output schema
Write to .clarity-cache/tasks-{YYYY-MM-DD}.json:

```json
{
  "week_start": "YYYY-MM-DD",
  "total_tasks": 0,
  "completed": 0,
  "completion_rate": 0.0,
  "by_category": {
    "financial": {"total": 0, "completed": 0, "moved": 0},
    "personal": {"total": 0, "completed": 0, "moved": 0},
    "communication": {"total": 0, "completed": 0, "moved": 0},
    "work": {"total": 0, "completed": 0, "moved": 0},
    "admin": {"total": 0, "completed": 0, "moved": 0}
  },
  "zero_completion_days": [],
  "most_avoided_category": "",
  "high_move_count": 0
}
```

## Never store
- Task titles or descriptions
- Project names if they reveal personal context
- Assignee names
- Any free-text content from the task