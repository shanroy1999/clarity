---
name: report
description: >
  Read and display the most recent Clarity weekly report from cache.
  Use when you want to re-read a report without re-running the pipeline.
arguments:
  - name: week_start
    description: Week to display YYYY-MM-DD. Defaults to most recent.
    required: false
---

Read the most recent report from .clarity-cache/.

If $week_start provided, read .clarity-cache/report-$week_start.json
Otherwise find the most recent: ls -t .clarity-cache/report-*.json | head -1

Display:
1. The full report_markdown text
2. Root cause on its own line
3. All detected patterns with severity and evidence
4. Load score and primary driver
5. Word count

If no report found, say so and suggest running /week to generate one.
