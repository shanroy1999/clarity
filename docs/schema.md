# Clarity database schema

## Design principle
Only derived signals and insights are persisted in Supabase.
Raw calendar, email, and task content never leaves the agent context.
All raw data processing happens in-memory and is discarded after
writing to .clarity-cache/ locally.

## Tables

### users
Stores the Clarity user account and OAuth connection status.

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz default now(),
  -- OAuth connection status (tokens stored in Supabase Vault, not here)
  calendar_connected boolean default false,
  gmail_connected boolean default false,
  todoist_connected boolean default false,
  finance_connected boolean default false
);
```

### weekly_snapshots
The normalized week of life load data — derived signals only.

```sql
create table weekly_snapshots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  week_start date not null,
  created_at timestamptz default now(),
  -- Calendar signals
  total_meeting_hours numeric(4,1),
  meetings_per_day jsonb,           -- {"Mon": 3, "Tue": 1, ...}
  back_to_back_count integer,
  free_evening_count integer,
  longest_focus_block_hours numeric(3,1),
  overload_days jsonb,              -- ["Mon", "Wed"]
  -- Email signals
  total_emails_received integer,
  unread_count integer,
  late_night_sends integer,
  unanswered_threads integer,
  -- Task signals
  total_tasks integer,
  completion_rate numeric(4,2),
  tasks_by_category jsonb,
  most_avoided_category text,
  zero_completion_days jsonb,
  -- Finance signals
  total_spend numeric(10,2),
  spend_vs_budget_pct numeric(5,1),
  high_spend_categories jsonb,
  unique(user_id, week_start)
);
```

### pattern_signals
Detected patterns from the pattern-detector agent.

```sql
create table pattern_signals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  snapshot_id uuid references weekly_snapshots(id) on delete cascade,
  detected_at timestamptz default now(),
  pattern_type text not null,       -- 'depletion_cascade', 'avoidance_loop', etc.
  severity text not null,           -- 'HIGH', 'MEDIUM', 'LOW'
  evidence jsonb,                   -- array of evidence strings
  days_affected jsonb,              -- ["Mon", "Tue"]
  historical_frequency integer default 0,
  weeks_consecutive integer default 1
);
```

### weekly_reports
The final insight document delivered to the user.

```sql
create table weekly_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  snapshot_id uuid references weekly_snapshots(id),
  week_start date not null,
  created_at timestamptz default now(),
  report_markdown text not null,    -- the full report text
  report_json jsonb,                -- structured version for frontend
  word_count integer,
  quality_score text,               -- 'passed', 'passed_with_flag'
  pattern_count integer,
  unique(user_id, week_start)
);
```

### alert_triggers
Proactive alerts sent to the user.

```sql
create table alert_triggers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  triggered_at timestamptz default now(),
  pattern_type text not null,
  severity text not null,
  message text not null,
  delivered boolean default false,
  delivery_channel text default 'push'
);
```

## Auth and secrets
- OAuth tokens for Google Calendar, Gmail, Todoist stored in Supabase Vault
- Never in environment variables, never in code
- Token refresh handled by backend/src/auth/token_refresh.py
- Token expiry checked before every MCP session via SessionStart hook

## What stays local (.clarity-cache/)
- Raw MCP data (discarded after ingestion)
- Intermediate cache files (snapshot, patterns, report)
- Rotated weekly — keep last 4, delete older
- Never synced to Supabase

## Hook authentication
All Claude Code HTTP hooks must include header:
  X-Clarity-Secret: ${CLARITY_HOOK_SECRET}

FastAPI validation (add to every hook endpoint):
```python
def verify_hook_secret(x_clarity_secret: str = Header(...)):
    if x_clarity_secret != os.environ["CLARITY_HOOK_SECRET"]:
        raise HTTPException(status_code=403, detail="Invalid hook secret")
```
### user_oauth_tokens
OAuth token storage. access_token and refresh_token should be
encrypted at rest using Supabase pgsodium in production.
Never query this table from agents — use backend/src/auth/token_refresh.py.

```sql
create table user_oauth_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  provider text not null,
  access_token text not null,
  refresh_token text,
  expires_at timestamptz,
  updated_at timestamptz default now(),
  unique(user_id, provider)
);
```

## Token lifecycle
- Tokens stored by OAuth callback handler (not yet built)
- ensure_fresh_token() called before every MCP session
- Refresh happens automatically if expiry < 10 minutes away
- Re-authorization required if refresh_token is missing or revoked
- Google sometimes omits refresh_token on subsequent refreshes —
  always preserve the existing one when that happens

## Token lifecycle (corrected)
- Google Calendar + Gmail: OAuth2 with refresh tokens
  - access_token expires after 60 minutes
  - ensure_fresh_token() refreshes automatically within 10 minute buffer
  - refresh_token preserved across refreshes (Google omits on subsequent)
  - Re-authorization required if refresh_token is revoked

- Todoist: static API token
  - Set once in .env as TODOIST_API_TOKEN
  - Stored in user_oauth_tokens with no expires_at
  - check_all_tokens() reports "static" — never "expiring" or "expired"
  - User must regenerate manually in Todoist settings if revoked
  - No _refresh_todoist_token function — intentionally omitted

## Token lifecycle (corrected)
- Google Calendar + Gmail: OAuth2 with refresh tokens
  - access_token expires after 60 minutes
  - ensure_fresh_token() refreshes automatically within 10 minute buffer
  - refresh_token preserved across refreshes (Google omits on subsequent)
  - Re-authorization required if refresh_token is revoked

- Todoist: static API token
  - Set once in .env as TODOIST_API_TOKEN
  - Stored in user_oauth_tokens with no expires_at
  - check_all_tokens() reports "static" — never "expiring" or "expired"
  - User must regenerate manually in Todoist settings if revoked
  - No _refresh_todoist_token function — intentionally omitted
