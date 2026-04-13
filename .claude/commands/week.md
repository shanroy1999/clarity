---
name: week
description: >
  Run the full Clarity weekly pipeline for the current or specified week.
  Fetches data, runs agents, generates report. Use every Sunday or
  whenever you want a fresh analysis.
arguments:
  - name: week_start
    description: Monday date YYYY-MM-DD. Defaults to last Monday.
    required: false
---

Run the Clarity weekly pipeline.

If $week_start is provided, use it. Otherwise calculate last Monday:
  python3 -c "from datetime import date,timedelta; t=date.today(); print((t-timedelta(days=t.weekday())).isoformat())"

Then run:
  source .venv/bin/activate
  python3 -m agents.orchestrator $week_start

After completion:
- Print the report_markdown from the output
- Show patterns_detected count and load_score
- If alert_count > 0, list the alert patterns and their severity
- Tell me the cache files that were written
