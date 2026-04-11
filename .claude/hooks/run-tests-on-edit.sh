#!/bin/bash

# PostToolUse hook — runs pytest after any Python file is written in backend/
# Input arrives as JSON on stdin

INPUT=$(cat)

# Extract the file path that was just written
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
")

# Only run if the file is in backend/ and is a Python file
if [[ "$FILE_PATH" == backend/*.py ]]; then
  echo "Running tests for $FILE_PATH..."
  
  cd backend
  python3 -m pytest --tb=short -q 2>&1
  EXIT_CODE=$?
  
  if [ $EXIT_CODE -ne 0 ]; then
    echo "Tests failed after editing $FILE_PATH"
    exit 2  # Exit code 2 blocks Claude and shows this message
  fi
  
  echo "All tests passed."
fi

exit 0