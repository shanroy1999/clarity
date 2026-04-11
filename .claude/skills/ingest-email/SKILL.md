---
name: ingest-email
description: >
  Processes Gmail data to extract stress and workload signals for Clarity.
  Use when email metadata has been fetched via MCP. Detects email volume
  spikes, late-night sends, and unanswered threads as overwhelm signals.
invocation: auto
allowed-tools:
  - Read
  - Write
---

# Email ingestion playbook

## Critical privacy rule
NEVER read email body content. Work only with metadata:
subject line (first 5 words only), sender domain, timestamp, thread length.

## What to extract

### Volume signals
- Total emails received per day
- Emails sent after 9pm (late-night work signal)
- Unread count at end of week
- Threads with 5+ replies (high-engagement threads = mental overhead)

### Stress signals
- Emails from manager received outside business hours
- Threads unanswered for 3+ days (avoidance signal)
- Days where sent emails spike >50% above weekly average

## Output schema
Write to .clarity-cache/email-{YYYY-MM-DD}.json:

```json
{
  "week_start": "YYYY-MM-DD",
  "total_received": 0,
  "total_sent": 0,
  "unread_count": 0,
  "late_night_sends": 0,
  "unanswered_threads": 0,
  "high_volume_days": [],
  "avoidance_signals": []
}
```