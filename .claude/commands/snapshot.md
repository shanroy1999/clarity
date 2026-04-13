---
name: snapshot
description: >
  Display the normalized life load snapshot for a given week.
  Shows all signals: meetings, email, tasks, finance. Useful for
  debugging what data the agents actually received.
arguments:
  - name: week_start
    description: Week to inspect YYYY-MM-DD. Defaults to most recent.
    required: false
---

Read the snapshot for the specified week.

If $week_start provided, read .clarity-cache/snapshot-$week_start.json
Otherwise find the most recent: ls -t .clarity-cache/snapshot-*.json | head -1

Display in a readable format:

## Calendar signals
- Total meeting hours, meetings per day breakdown
- Back-to-back count, overload days, free evenings
- Longest focus block

## Email signals
- Total received, unread, late-night sends, unanswered threads

## Task signals
- Completion rate, tasks by category, most avoided category
- Zero completion days

## Finance signals
- Total spend, vs budget percentage, high spend categories
- Spend by category breakdown

Flag any signals that look anomalous — very high or very low values
that might indicate a data ingestion problem.
