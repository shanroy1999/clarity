---
name: detect-patterns
description: >
  Analyses a LifeLoadSnapshot to detect cross-time behavioral patterns
  for Clarity. Heavy analysis — always runs in a subagent to keep the
  main context clean. Use after /analyze-week has produced a snapshot.
invocation: auto
run-in-subagent: true
subagent-model: claude-haiku-4-5-20251001
allowed-tools:
  - Read
  - Write
---

# Pattern detection playbook

## Input
Read .clarity-cache/snapshot-{most-recent-date}.json

## Pattern types to detect

### Depletion cascade
Definition: 3+ meetings in a day → evening has no completed tasks → 
next morning starts late or has avoidance behaviour.
Evidence needed: calendar overload day + task completion drop + 
email send time shift.
Severity: HIGH if happens 2+ times in the week.

### Avoidance loop
Definition: Same task moved 3+ times in a week.
Evidence: task move history showing repeated rescheduling.
Emotional category: classify as financial / personal / communication / work.
Severity: HIGH if financial or personal, MEDIUM if work.

### Boundary erosion
Definition: Consistent after-hours work signals across 3+ days.
Evidence: late email sends + before-9am or after-6pm meetings.
Severity: MEDIUM always, HIGH if persists 3+ consecutive weeks.

### Social withdrawal
Definition: Personal tasks (calls, messages to friends/family) 
consistently moved or uncompleted.
Evidence: personal task category avoidance + personal communication 
tasks rescheduled.
Severity: HIGH — always flag this one.

## Output schema
Write to .clarity-cache/patterns-{date}.json:

```json
{
  "week_start": "YYYY-MM-DD",
  "patterns_detected": [
    {
      "type": "depletion_cascade",
      "severity": "HIGH",
      "evidence": ["description of evidence"],
      "days_affected": ["Mon", "Tue"],
      "historical_frequency": 0
    }
  ],
  "no_patterns_detected": false,
  "analysis_confidence": "high"
}
```

## Important
- If you detect nothing significant, say so honestly — don't manufacture patterns
- Weight recent occurrences more heavily than older ones
- Note when a pattern is new vs recurring across multiple weeks