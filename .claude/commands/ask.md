---
name: ask
description: >
  Ask the Clarity conversation agent a question about your week.
  Uses the most recent report and snapshot as context.
  Equivalent to using the conversation UI but from the terminal.
arguments:
  - name: question
    description: The question to ask about your week.
    required: true
---

Answer this question about the user's week: $question

First read the context:
- Most recent report: ls -t .clarity-cache/report-*.json | head -1
- Most recent snapshot: ls -t .clarity-cache/snapshot-*.json | head -1
- Most recent patterns: ls -t .clarity-cache/patterns-*.json | head -1

Then answer following the conversation agent rules:
- Cite specific numbers from the data in your answer
- Under 150 words
- Never speculate beyond what the data shows
- Connect the answer to a detected pattern if relevant
- Be direct, not therapeutic
