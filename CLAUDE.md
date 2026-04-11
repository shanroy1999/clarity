# Clarity — AI life load intelligence

## What this project is
Clarity reads a user's calendar, email, tasks, and financial data,
detects patterns across time, and tells them honestly why they feel
overwhelmed. It is not a productivity tool. It surfaces insight, not
tasks. The core output: a weekly report in the voice of a brutally
honest friend.

## Tech stack
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS
- Backend: FastAPI, Python 3.11, Pydantic
- Database: Supabase (PostgreSQL) — see docs/schema.md for tables
- AI: Anthropic Claude API (claude-sonnet-4-6)
- Data connections: MCP servers (Google Calendar, Gmail, Todoist, custom financial)
- Deployment: Vercel (frontend), Railway (backend)

## Project structure
- frontend/ — Next.js web app (report view, dashboard, conversation UI)
- backend/ — FastAPI server, Supabase client, auth, hook endpoints
- agents/ — Agent orchestration code (Python, Agent SDK)
- docs/ — Architecture decisions, schema, PRDs
- .claude/skills/ — SKILL.md files: ingest-calendar, ingest-email,
  ingest-tasks, detect-patterns, analyze-week, generate-report, cleanup-cache
- .claude/hooks/ — Hook scripts: session-start, validate-agent-structure,
  run-tests-on-edit, audit-logger, quality-gate, agent-timer
- .claude/agents/ — Subagent definitions (Phase 5)
- .claude/rules/ — Path-scoped rules: python.md, typescript.md, agents.md

## Architecture principles
- Files under 500 lines — agents must read the whole file
- One responsibility per file
- All AI calls go through agents/ — never from frontend
- MCP servers handle all external data fetching
- Privacy first — NEVER store raw email, calendar, or task titles
- Only derived signals persisted in Supabase — see docs/schema.md

## Privacy model — critical
- ingest-calendar: stores derived signals only, never attendee names
- ingest-email: stores metadata signals only, never email body or subject
- ingest-tasks: stores category counts only, never task titles
- detect-patterns: reads last 4 snapshots for cross-week severity
- .clarity-cache/: local only, rotated to last 4 weeks, never synced to DB

## Hook system — event order
SessionStart → UserPromptSubmit → PreToolUse → [tool] → PostToolUse → Stop

Active hooks:
- SessionStart: injects today's date, service status, cache state
- PreToolUse (Write): validates agent files in agents/ before writing
- PostToolUse (Write): runs pytest on backend/ Python edits
- PostToolUse (all, async): structured JSONL audit to .clarity-audit.jsonl
- Stop: quality gate with 2-retry budget, then HTTP POST to backend
- SubagentStart/Stop (async): logs agent timing to audit file

## Cache file naming convention
.clarity-cache/{type}-{YYYY-MM-DD}.json
Types: snapshot, calendar, email, tasks, patterns, report
Keep last 4 of each type. Run /cleanup-cache when needed.

## Skill invocation
- Auto: ingest-calendar, ingest-email, detect-patterns
- Manual: /ingest-tasks, /analyze-week [date], /generate-report, /cleanup-cache

## Code conventions
- Python: snake_case, type hints on all functions, docstrings required,
  structlog for logging, never print()
- TypeScript: camelCase, strict mode, no any types ever
- Commits: conventional commits (feat:, fix:, chore:, docs:)
- Tests: TDD — write tests before implementation, always

## Commands
- Backend: cd backend && uvicorn main:app --reload
- Frontend: cd frontend && npm run dev
- Tests: cd backend && pytest
- Supabase: npx supabase start

## What Claude must never do
- Write more than 500 lines in a single file without asking
- Store raw email body, calendar description, or task titles anywhere
- Make direct external API calls from the frontend
- Skip writing tests for agent or backend logic
- Use any TypeScript types
- Leave historical_frequency at 0 in pattern output without checking prior snapshots

## Docs to read
@docs/architecture.md
@docs/schema.md