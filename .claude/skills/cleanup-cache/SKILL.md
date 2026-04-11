---
name: cleanup-cache
description: >
  Rotates .clarity-cache/ files — keeps the last 4 weeks of each type
  and deletes older files. Always shows a preview before deleting.
  Run manually when warned by session-start that cache is bloated.
invocation: manual
allowed-tools:
  - Bash
  - Read
---

# Cache cleanup playbook

## Always preview before deleting
1. List all files in .clarity-cache/ grouped by prefix
2. Show exactly which files will be kept and which will be deleted
3. Ask for confirmation before proceeding
4. Only delete after confirmation

## What to keep
- The 4 most recent files of each type: snapshot, patterns, report,
  calendar, email, tasks
- Never delete: .quality-flag.json, .quality-retry-count
- Never delete files less than 24 hours old

## After cleanup
- Report total files deleted
- Report current cache size
- Confirm what remains
