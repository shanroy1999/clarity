---
name: ingest-calendar
description: >
  Normalizes raw Google Calendar event data into Clarity's LifeLoadSnapshot
  schema. Use when calendar data has just been fetched via MCP and needs to
  be processed before analysis. Triggers automatically when calendar JSON
  is present in context.
invocation: auto
allowed-tools:
  - Read
  - Write
  - Bash
---

# Calendar ingestion playbook

You are processing raw Google Calendar data for Clarity.
Your job is to normalize it into the LifeLoadSnapshot schema.

## Input
Raw calendar events from the Google Calendar MCP tool.
Each event has: id, summary, start, end, attendees, location, description.

## What to extract and normalize

### Meeting load signals
- Total meeting hours per day
- Back-to-back meetings (gap < 15 minutes between consecutive meetings)
- Meetings with 4+ attendees (high cognitive load)
- Meetings before 9am or after 6pm (boundary violations)
- Longest uninterrupted focus block per day
- Number of days with zero free hours (9am-6pm)

### Pattern signals
- Days with 3+ meetings (historically correlates with evening depletion)
- Weeks with no free evenings (5pm-10pm unscheduled)
- Recurring meetings that dominate the week

## Output schema
Write a JSON file to .clarity-cache/calendar-{YYYY-MM-DD}.json:

```json
{
  "week_start": "YYYY-MM-DD",
  "total_meeting_hours": 0,
  "meetings_per_day": {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0},
  "back_to_back_count": 0,
  "free_evening_count": 0,
  "longest_focus_block_hours": 0,
  "overload_days": [],
  "boundary_violations": [],
  "raw_event_count": 0
}
```

## Rules
- Never store attendee names or email addresses
- Never store meeting descriptions or notes
- Only store derived signals, never raw content
- If an event has no end time, skip it
- Treat all-day events as non-meeting time (personal days, holidays)