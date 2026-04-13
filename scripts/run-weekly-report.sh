#!/bin/bash

# Weekly Clarity report runner
# Executed by Claude Code cloud scheduled task every Sunday at 8pm
# Environment variables injected by Claude Code at runtime

set -euo pipefail

cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Log the scheduled run start
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Weekly report scheduled run starting"

# Run the pipeline for the completed week
# Sunday 8pm — week just ended, analyse Mon-Sun
WEEK_START=$(date -v-Mon +%Y-%m-%d 2>/dev/null || date -d 'last monday' +%Y-%m-%d)

python3 agents/orchestrator.py "$WEEK_START"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Weekly report complete"
else
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Weekly report FAILED with exit code $EXIT_CODE"
fi

exit $EXIT_CODE