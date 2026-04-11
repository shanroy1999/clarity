---
name: analyze-week
description: >
  Runs a complete Clarity weekly analysis for a given week. Coordinates
  all ingestion skills and produces a LifeLoadSnapshot ready for the
  agent intelligence layer. Always invoked manually by the user.
invocation: manual
arguments:
  - name: week_start
    description: Start date of the week to analyze (YYYY-MM-DD). Defaults to last Monday.
    required: false
allowed-tools:
  - Read
  - Write
  - Bash
  - mcp__google-calendar__list_events
  - mcp__gmail__list_messages
  - mcp__todoist__get_tasks
---

# Analyze week playbook

## Usage
/analyze-week → analyzes the most recent completed week
/analyze-week 2026-04-07 → analyzes the week starting April 7

## Steps to follow in order

1. Determine the week range
   - If $week_start provided, use it
   - Otherwise calculate last Monday's date
   - Week is always Monday to Sunday

2. Fetch all data sources via MCP
   - Calendar: fetch events for the week
   - Email: fetch message metadata for the week
   - Tasks: fetch tasks due or completed during the week

3. Run ingestion skills in sequence
   - Trigger ingest-calendar on calendar data
   - Trigger ingest-email on email data
   - Trigger ingest-tasks on task data

4. Merge all cache files into a single LifeLoadSnapshot
   - Read .clarity-cache/calendar-{date}.json
   - Read .clarity-cache/email-{date}.json
   - Read .clarity-cache/tasks-{date}.json
   - Write merged snapshot to .clarity-cache/snapshot-{date}.json

5. Report what was found
   - Print a brief summary: X meetings, Y tasks, Z emails
   - Note any immediate signals that look significant
   - Tell the user the snapshot is ready for analysis

## Never do
- Never run analysis without fetching fresh data first
- Never skip a data source even if it seems empty
- Never store raw content, only derived signals