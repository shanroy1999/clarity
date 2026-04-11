#!/bin/bash

# Stop hook — quality gate with retry budget
# Checks report quality but never blocks indefinitely
# Max 2 retries, then passes with quality_flag: degraded

INPUT=$(cat)
RETRY_FILE=".clarity-cache/.quality-retry-count"
MAX_RETRIES=2

# Read current retry count
RETRY_COUNT=0
if [ -f "$RETRY_FILE" ]; then
  RETRY_COUNT=$(cat "$RETRY_FILE")
fi

# Check if this turn generated a report
HAS_REPORT=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
msg = data.get('last_assistant_message', '')
# Report present if it has numbers and is substantial
has_numbers = any(c.isdigit() for c in msg)
is_long = len(msg) > 200
print('yes' if (has_numbers and is_long) else 'no')
" 2>/dev/null || echo "no")

# If no report was generated this turn, approve immediately
if [ "$HAS_REPORT" = "no" ]; then
  rm -f "$RETRY_FILE"
  exit 0
fi

# If we've hit the retry budget, pass through with flag
if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
  echo "Quality check skipped after $MAX_RETRIES retries — report passed with quality_flag: degraded"
  rm -f "$RETRY_FILE"
  # Write flag to cache so backend knows
  echo '{"quality_flag": "degraded", "reason": "max_retries_exceeded"}' \
    > .clarity-cache/.quality-flag.json
  exit 0
fi

# Run the quality check
REPORT_TEXT=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('last_assistant_message', ''))
" 2>/dev/null)

WORD_COUNT=$(echo "$REPORT_TEXT" | wc -w | tr -d ' ')
HAS_NUMBERS=$(echo "$REPORT_TEXT" | grep -c '[0-9]' || echo "0")
HAS_GENERIC=$(echo "$REPORT_TEXT" | grep -ic 'try to\|consider\|you should\|make sure\|productivity' || echo "0")

FAILED=0
REASON=""

if [ "$WORD_COUNT" -gt 400 ]; then
  FAILED=1
  REASON="Report is $WORD_COUNT words — exceeds 400 word limit"
fi

if [ "$HAS_NUMBERS" -lt 2 ]; then
  FAILED=1
  REASON="Report lacks specific data citations — needs numbers from the snapshot"
fi

if [ "$HAS_GENERIC" -gt 2 ]; then
  FAILED=1
  REASON="Report contains generic advice — Clarity never says 'try to' or 'you should'"
fi

if [ "$FAILED" -eq 1 ]; then
  # Increment retry count
  echo $((RETRY_COUNT + 1)) > "$RETRY_FILE"
  echo "Quality check failed (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES): $REASON"
  echo "Please revise the report to fix this issue."
  exit 2
fi

# Passed — clean up
rm -f "$RETRY_FILE"
rm -f ".clarity-cache/.quality-flag.json"
exit 0