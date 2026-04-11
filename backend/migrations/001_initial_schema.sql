-- Clarity initial schema
-- Run with: npx supabase db push

create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz default now(),
  calendar_connected boolean default false,
  gmail_connected boolean default false,
  todoist_connected boolean default false,
  finance_connected boolean default false
);

create table weekly_snapshots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  week_start date not null,
  created_at timestamptz default now(),
  total_meeting_hours numeric(4,1),
  meetings_per_day jsonb,
  back_to_back_count integer,
  free_evening_count integer,
  longest_focus_block_hours numeric(3,1),
  overload_days jsonb,
  total_emails_received integer,
  unread_count integer,
  late_night_sends integer,
  unanswered_threads integer,
  total_tasks integer,
  completion_rate numeric(4,2),
  tasks_by_category jsonb,
  most_avoided_category text,
  zero_completion_days jsonb,
  total_spend numeric(10,2),
  spend_vs_budget_pct numeric(5,1),
  high_spend_categories jsonb,
  unique(user_id, week_start)
);

create table pattern_signals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  snapshot_id uuid references weekly_snapshots(id) on delete cascade,
  detected_at timestamptz default now(),
  pattern_type text not null,
  severity text not null,
  evidence jsonb,
  days_affected jsonb,
  historical_frequency integer default 0,
  weeks_consecutive integer default 1
);

create table weekly_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  snapshot_id uuid references weekly_snapshots(id),
  week_start date not null,
  created_at timestamptz default now(),
  report_markdown text not null,
  report_json jsonb,
  word_count integer,
  quality_score text,
  pattern_count integer,
  unique(user_id, week_start)
);

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
