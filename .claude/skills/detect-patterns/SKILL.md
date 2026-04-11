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
Read the last 4 weekly snapshots to enable cross-week comparison:

```bash
ls -t .clarity-cache/snapshot-*.json | head -4
```

Load all available snapshots (up to 4). If fewer than 4 exist, work
with what's available and note the limited history.

Label them: current (most recent), week-1, week-2, week-3.

Cross-week comparison is required for accurate severity:
- A pattern appearing once → severity LOW
- A pattern appearing 2 consecutive weeks → severity MEDIUM  
- A pattern appearing 3+ consecutive weeks → severity HIGH

historical_frequency in the output is the count of prior weeks
where this same pattern was detected. Never leave it at 0 unless
this is genuinely the first occurrence.

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