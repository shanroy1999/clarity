#!/bin/bash

# PreToolUse hook — validates agent files before writing
# Fires before any Write tool call
# Exit 2 blocks the write and shows the message

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
")

CONTENT=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('content', ''))
")

# Only validate files in agents/
if [[ "$FILE_PATH" != agents/*.py ]]; then
  exit 0
fi

# Check for required module docstring
if ! echo "$CONTENT" | grep -q '"""'; then
  echo "ERROR: Agent file $FILE_PATH must have a module docstring."
  echo "Every agent file needs a docstring explaining what it does."
  exit 2
fi

# Check for typed run() function
if ! echo "$CONTENT" | grep -q 'async def run('; then
  echo "ERROR: Agent file $FILE_PATH must have an async def run() function."
  echo "All Clarity agents expose a single async run() entrypoint."
  exit 2
fi

# Check file won't exceed 300 lines
LINE_COUNT=$(echo "$CONTENT" | wc -l)
if [ "$LINE_COUNT" -gt 300 ]; then
  echo "ERROR: Agent file $FILE_PATH is $LINE_COUNT lines — exceeds 300 line limit."
  echo "Break it into smaller modules."
  exit 2
fi

echo "Agent structure validated: $FILE_PATH"
exit 0