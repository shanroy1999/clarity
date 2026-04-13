---
name: audit
description: >
  Read and summarize the Clarity audit trail. Shows what data was
  accessed, when, and by which agents. Useful for privacy verification.
arguments:
  - name: lines
    description: Number of recent entries to show. Defaults to 50.
    required: false
---

Read the Clarity audit trail from .clarity-audit.jsonl.

Show the last $lines entries (default 50) formatted as a table:
  timestamp | event type | tool | resource | session

Then summarize:
- Total MCP data access events (user_facing: true)
- Which data sources were accessed (calendar, gmail, todoist, financial)
- Any blocked tool calls (mcp_access_blocked events)
- Sessions in the log

Flag anything unusual — unexpected data sources, blocked calls,
or gaps in the audit trail.
