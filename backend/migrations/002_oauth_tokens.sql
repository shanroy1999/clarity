-- Migration 002: OAuth token storage
-- Depends on: 001_initial_schema.sql (users table)
--
-- access_token and refresh_token should be encrypted at rest
-- via Supabase pgsodium extension in production.
-- In development, tokens are stored as plaintext.
--
-- Never query this table from agents or skills.
-- Use backend/src/auth/token_refresh.py exclusively.

create table user_oauth_tokens (
  id           uuid        primary key default gen_random_uuid(),
  user_id      uuid        not null references users(id) on delete cascade,
  provider     text        not null check (provider in ('google', 'todoist')),
  access_token text        not null,
  refresh_token text,
  expires_at   timestamptz,
  updated_at   timestamptz not null default now(),
  unique(user_id, provider)
);

comment on table user_oauth_tokens is
  'OAuth tokens per user per provider. access_token and refresh_token '
  'must be encrypted at rest in production via pgsodium.';

comment on column user_oauth_tokens.refresh_token is
  'Null for providers using static API tokens. '
  'Google omits this on subsequent refreshes — preserve existing value.';
