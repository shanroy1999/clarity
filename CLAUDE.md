# Clarity — AI life load intelligence

## What this project is
Clarity reads a user's calendar, email, tasks, and financial data,
detects patterns across time, and tells them honestly why they feel
overwhelmed. It is not a productivity tool. It surfaces insight, not
tasks. The core output is a weekly report written in the voice of a
brutally honest friend.

## Tech stack
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS
- Backend: FastAPI, Python 3.11, Pydantic
- Database: Supabase (PostgreSQL)
- AI: Anthropic Claude API (claude-sonnet-4-6)
- Data connections: MCP servers (Google Calendar, Gmail, Todoist, custom financial)
- Deployment: Vercel (frontend), Railway (backend)

## Project structure
- frontend/ — Next.js web app (report view, dashboard, conversation UI)
- backend/ — FastAPI server (API routes, Supabase client, auth)
- agents/ — Agent orchestration code (Python, uses Agent SDK)
- docs/ — Architecture decisions, PRDs, specs
- .claude/skills/ — SKILL.md files for data ingestion and analysis
- .claude/hooks/ — Hook scripts for quality gates and automation
- .claude/agents/ — Subagent definition files
- .claude/rules/ — Path-scoped rules per directory

## Architecture principles
- Keep every file under 500 lines — agents must read the whole file
- One responsibility per file — no god files
- All AI calls go through agents/ — never directly from frontend
- MCP servers handle all external data fetching
- Privacy first — never store raw email or calendar content

## Code conventions
- Python: snake_case, type hints on all functions, docstrings required
- TypeScript: camelCase, strict mode on, no any types ever
- Commits: conventional commits (feat:, fix:, chore:, docs:)
- Tests: write tests before implementation (TDD)
- Never skip writing tests for agent logic

## Commands
- Backend: cd backend && uvicorn main:app --reload
- Frontend: cd frontend && npm run dev
- Tests: cd backend && pytest
- Type check: cd frontend && npx tsc --noEmit

## What Claude must never do
- Write more than 500 lines in a single file without asking first
- Make direct external API calls from the frontend
- Store raw email or calendar content in the database
- Skip writing tests for any agent or backend logic
- Use any types in TypeScript

## Docs to know
@README.md
@docs/architecture.md