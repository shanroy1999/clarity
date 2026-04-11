#!/bin/bash

# Async SubagentStart/SubagentStop hook — logs agent timing to terminal
# Shows which Clarity agent is running and timestamps

INPUT=$(cat)
TIMESTAMP=$(date +"%H:%M:%S")

EVENT=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('event', 'unknown'))
")

AGENT_ID=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('subagent_id', data.get('agent_id', 'unknown')))
")

if [[ "$EVENT" == "SubagentStart" ]]; then
  echo "[$TIMESTAMP] Agent started: $AGENT_ID" >> .clarity-audit.jsonl
else
  echo "[$TIMESTAMP] Agent finished: $AGENT_ID" >> .clarity-audit.jsonl
fi

exit 0