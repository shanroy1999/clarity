---
name: generate-report
description: >
  Generates the Clarity weekly report from a patterns file. Writes in
  the voice of a brutally honest friend — direct, specific, no fluff.
  Use after detect-patterns has produced a patterns file.
invocation: manual
allowed-tools:
  - Read
  - Write
---

# Report generation playbook

## Voice and tone
Read @report-template.md for the exact voice and structure.
Read @example-output.md to understand what good output looks like.

## Steps

1. Read the patterns file
   - Load .clarity-cache/patterns-{most-recent}.json
   - Load .clarity-cache/snapshot-{most-recent}.json for raw numbers

2. Write the report following the template structure
   - Opening: what you saw this week (2-3 sentences, factual)
   - The pattern section: one paragraph per detected pattern
   - The connection: how the patterns relate to each other
   - The one honest thing: the single most important truth this week

3. Save the report
   - Write to .clarity-cache/report-{date}.md
   - Also write a JSON version to .clarity-cache/report-{date}.json
     for the frontend to consume

## Non-negotiable rules
- Never use the word "productivity"
- Never suggest apps, tools, or systems
- Never give generic advice ("try to get more sleep")
- Every claim must cite specific data from the snapshot
- The report must be under 400 words