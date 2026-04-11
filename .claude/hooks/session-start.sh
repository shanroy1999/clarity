#!/bin/bash

# SessionStart hook — injects live context at the start of every session

TODAY=$(date +%Y-%m-%d)
DAY_OF_WEEK=$(date +%A)
WEEK_START=$(date -v-Mon +%Y-%m-%d 2>/dev/null || date -d 'last monday' +%Y-%m-%d 2>/dev/null || echo "$TODAY")

echo "=== Clarity session context ==="
echo "Today: $TODAY ($DAY_OF_WEEK)"
echo "Week started: $WEEK_START"
echo ""

# Service health — 2 second timeout on both checks
if curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
  echo "Backend:  running"
else
  echo "Backend:  not running (cd backend && uvicorn main:app --reload)"
fi

if curl -s --max-time 2 http://localhost:54321 > /dev/null 2>&1; then
  echo "Supabase: running"
else
  echo "Supabase: not running (npx supabase start)"
fi

echo ""

# Cache state — single block, no duplicate snapshot check
CACHE_DIR=".clarity-cache"
mkdir -p "$CACHE_DIR"

LATEST=$(ls -t "$CACHE_DIR"/snapshot-*.json 2>/dev/null | head -1)

if [ -n "$LATEST" ]; then
  # Age check
  if stat -f "%m" "$LATEST" > /dev/null 2>&1; then
    FILE_MOD=$(stat -f "%m" "$LATEST")   # macOS
  else
    FILE_MOD=$(stat -c "%Y" "$LATEST")   # Linux
  fi
  NOW=$(date +%s)
  AGE_DAYS=$(( (NOW - FILE_MOD) / 86400 ))

  if [ "$AGE_DAYS" -gt 8 ]; then
    echo "Cache: latest snapshot is $AGE_DAYS days old — consider /analyze-week"
  else
    echo "Cache: latest snapshot $LATEST ($AGE_DAYS days old)"
  fi

  # Warn if cache is bloated — do NOT auto-rotate here
  CACHE_COUNT=$(ls "$CACHE_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
  if [ "$CACHE_COUNT" -gt 40 ]; then
    echo "Cache: $CACHE_COUNT files — run /cleanup-cache to rotate"
  fi
else
  echo "Cache: no snapshots yet — run /analyze-week to generate one"
fi

# Token health check (requires ANTHROPIC_API_KEY and a logged-in user)
# Skip silently if no user context available yet
if [ -f ".env" ] && command -v python3 &> /dev/null; then
  python3 - << 'PYEOF' 2>/dev/null || true
import asyncio, sys, os
sys.path.insert(0, os.getcwd())

async def check():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from backend.src.auth.token_refresh import check_all_tokens
        # Use a dev user ID from env, skip if not set
        user_id = os.environ.get("CLARITY_DEV_USER_ID")
        if not user_id:
            return
        status = await check_all_tokens(user_id)
        for provider, state in status.items():
            icon = "ok" if state == "fresh" else "WARN"
            print(f"Token {provider}: {state} [{icon}]")
    except Exception:
        pass  # Never block session start on token check failure

asyncio.run(check())
PYEOF
fi

echo "================================"
