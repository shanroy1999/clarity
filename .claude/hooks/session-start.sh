#!/bin/bash

# SessionStart hook — injects live context at the start of every session
# Claude Code reads the stdout of this script as additional context

TODAY=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%A)
WEEK_START=$(date -v-Mon +%Y-%m-%d 2>/dev/null || date -d 'last monday' +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)

echo "=== Clarity Session Context ==="
echo "Today: $TODAY ($DAY_OF_WEEK)"
echo "Current week started: $WEEK_START"
echo ""

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo "Backend: running at http://localhost:8000"
else
  echo "Backend: not running (start with: cd backend && uvicorn main:app --reload)"
fi

# Check if Supabase is running
if curl -s http://localhost:54321 > /dev/null 2>&1; then
  echo "Supabase: running at http://localhost:54321"
else
  echo "Supabase: not running (start with: npx supabase start)"
fi

# Check for recent cache files
CACHE_DIR=".clarity-cache"
if [ -d "$CACHE_DIR" ]; then
  LATEST=$(ls -t "$CACHE_DIR"/snapshot-*.json 2>/dev/null | head -1)
  if [ -n "$LATEST" ]; then
    echo "Latest snapshot: $LATEST"
  else
    echo "No snapshots yet — run /analyze-week to generate one"
  fi
fi

echo "==============================="