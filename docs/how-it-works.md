# How Clarity Works — Complete Guide for New Team Members

This document explains every file in the Clarity project and how they all connect.
No coding experience is assumed. Read this top to bottom before touching anything.

---

## What is Clarity?

Clarity is an AI assistant that connects to your real digital life — your Google Calendar,
Gmail, Todoist task list, and financial data — and every week tells you honestly why you
feel overwhelmed. It is not a productivity app. It does not give you tips or suggest new
systems. It reads your data, finds patterns in your behaviour over time, and writes a
short, honest report in plain English. Think of it as a brutally honest friend who has
access to your schedule and can see what you cannot.

A typical Clarity report looks like this:

> "You had 14 meetings across 5 days. You completed 2 of 11 tasks. Every day you had
> 3 or more meetings, your evening collapsed. The same task — 'reply to mum' — moved
> four times. It takes 3 minutes. You're not forgetting it. You're protecting yourself
> from one more thing that requires you to show up. Thursday had one meeting. You
> completed 4 tasks. Thursday is the template."

That is the end product. Everything in this codebase exists to produce that paragraph
reliably, privately, and automatically every week.

---

## The Big Picture — How Data Flows

Before reading individual files, understand the journey data takes from your calendar
to that report. There are seven stages:

```
1. FETCH      Your calendar, email, and tasks are fetched from Google and Todoist
              via MCP connections (think: secure API bridges)

2. INGEST     Raw data is immediately stripped down to signals only.
              No meeting titles, no email content, no task names are kept.
              Only numbers: "3 meetings Monday", "2 tasks moved twice"

3. CACHE      Those signals are saved as local JSON files on your computer.
              They never go to the internet at this stage.

4. DETECT     An AI agent reads the last 4 weeks of signals and looks for
              patterns: Are you consistently depleted after heavy meeting days?
              Are you avoiding a category of tasks repeatedly?

5. REPORT     A second AI agent writes the weekly report in plain English,
              citing the specific numbers it found.

6. STORE      The report and the signals (never the raw data) are saved to
              a database (Supabase) so you can read them in the web app.

7. DELIVER    The frontend web app shows you the report. You can ask
              follow-up questions in a conversation interface.
```

Every file in this project belongs to one of these seven stages.

---

## The Technology Stack — What Each Tool Does

Before reading specific files, here is what each technology is and why it is used:

**Next.js** — the framework that builds the website you see in your browser.
It runs on a server and sends pages to your browser. We use version 14
with something called the "App Router", which is just a modern way of
organising the website's pages.

**TypeScript** — the programming language used for the website (frontend).
It is like JavaScript but stricter — it catches mistakes before the code runs.

**Tailwind CSS** — a system for styling the website. Instead of writing separate
style files, you add small class names directly to elements (e.g. "make this text
large and blue").

**FastAPI** — the framework that builds the backend server (the part that runs
on a server, not in your browser). It receives requests from the website and
from Claude Code hooks, talks to the database, and manages authentication.
Written in Python.

**Python** — the programming language used for the backend server and all AI agents.

**Pydantic** — a Python library that validates data. If the frontend sends the
backend a user ID that is the wrong format, Pydantic catches it before it
causes problems.

**Supabase** — the database. It stores your user account, your weekly signals,
detected patterns, and your reports. It is built on PostgreSQL (a standard
database). It also stores your OAuth tokens (the credentials that allow Clarity
to read your calendar) in a secure vault.

**Claude API (Anthropic)** — the AI brain. When Clarity needs to detect patterns
or write a report, it sends structured data to Claude and receives analysis back.
We use two models: Claude Haiku (fast, cheap) for pattern detection, and Claude
Sonnet (more capable) for writing the report and answering follow-up questions.

**MCP (Model Context Protocol)** — a system that allows Claude Code to call
external APIs (Google Calendar, Gmail, Todoist) as if they were built-in tools.
MCP servers act as bridges. When Clarity says "fetch my calendar for this week",
it is calling an MCP server which handles the actual Google API communication.

**Vercel** — where the Next.js frontend is deployed (hosted on the internet).

**Railway** — where the FastAPI backend is deployed.

**Structlog** — a Python logging library. Instead of just printing text to a
terminal, it writes structured JSON logs that can be searched and filtered.

---

## The Directory Structure

```
clarity/
├── frontend/          The Next.js website
├── backend/           The FastAPI server
├── agents/            The AI agent code
├── docs/              Architecture documents and database schema
└── .claude/           Configuration for Claude Code (the AI coding assistant)
    ├── skills/        Playbooks for specific tasks Claude can perform
    ├── hooks/         Shell scripts that run automatically at key moments
    ├── rules/         Coding standards Claude must follow
    └── agents/        Subagent definitions (Phase 5, not yet built)
```

---

## Part 1: The Claude Code Configuration (.claude/)

Claude Code is the AI assistant used to build and operate Clarity. The `.claude/`
folder configures how it behaves. This is not the Clarity application itself —
it is the workshop where the application is built and operated.

Think of `.claude/` as a set of standing instructions left on Claude's desk:
"When you start a session, check these things. When you write a file, validate
it first. When you finish writing a report, check its quality."

---

### .claude/settings.json — The Master Hook Configuration

This is the single most important configuration file for Claude Code. It tells
Claude Code which shell scripts (hooks) to run at which moments in its lifecycle.

Think of it like a stage manager's cue sheet at a theatre: "When the curtain
opens (SessionStart), run this script. Before an actor enters (PreToolUse),
check their costume. After they leave (PostToolUse), record what happened."

The file currently has these hooks active:

**SessionStart** — runs `session-start.sh` every time a new Claude Code session
begins. Before Claude reads your message, this script runs and injects live
context: today's date, whether the backend is running, whether the database
is running, and the state of the local data cache.

**PreToolUse (Write)** — before Claude writes any file, runs
`validate-agent-structure.sh`. This acts as a gatekeeper. If Claude is about
to write a Python file to the `agents/` folder, the script checks that the file
meets Clarity's structural requirements. If it does not, the write is cancelled.

**PostToolUse (Write)** — after Claude writes any file, runs
`run-tests-on-edit.sh`. If Claude just wrote a Python file in the `backend/`
folder, this script automatically runs the test suite to check nothing broke.

**PostToolUse (all tools, async)** — after every single tool Claude uses,
runs `audit-logger.sh` in the background. This creates a permanent record
of everything Claude accessed during the session, especially any personal data
fetched via MCP. "Async" means this runs in the background without making
Claude wait for it to finish.

**Stop** — when Claude finishes generating a response, two things happen in order:
1. `quality-gate.sh` checks if the response was a Clarity report, and if so,
   validates it against quality rules (under 400 words, cites real numbers,
   no generic advice). If it fails, Claude is forced to try again (up to 2 times).
2. An HTTP POST is sent to the backend server notifying it the session ended.

**SubagentStart / SubagentStop** — when Claude spawns a subagent (a separate
AI process for heavy work), `agent-timer.sh` records the timing in the audit log.

---

### .claude/hooks/session-start.sh — Session Initialisation

**What it is:** A shell script (a series of terminal commands) that runs
automatically at the start of every Claude Code session.

**What it does:**
1. Gets today's date and the current week's start date
2. Pings the backend server at `http://localhost:8000/health` with a 2-second
   timeout. If the server responds, it prints "Backend: running". If not, it
   prints a reminder of how to start it.
3. Does the same for the Supabase database at `http://localhost:54321`.
4. Checks the `.clarity-cache/` folder for the most recent snapshot file.
   If the snapshot is more than 8 days old, it warns that data may be stale.
   If there are more than 40 cache files, it warns to run `/cleanup-cache`.

**Why the 2-second timeout matters:** Without a timeout, if the backend server
is hung (running but not responding), this script would freeze the entire
session start indefinitely. `--max-time 2` ensures it gives up quickly.

**Why it only warns about bloated cache, not deletes:** An earlier version
auto-deleted old cache files here. This was removed because automatic deletion
is risky — a warning is safer. Deletion is now a deliberate manual action
via `/cleanup-cache`.

---

### .claude/hooks/validate-agent-structure.sh — Agent File Gatekeeper

**What it is:** A PreToolUse hook that fires before Claude writes any file.

**What it does:**
- Reads the proposed file path and content from the JSON data Claude Code
  sends to it via standard input (stdin — the terminal's input channel)
- If the file is NOT in the `agents/` folder, it immediately approves
  (exit code 0) and does nothing
- If the file IS in `agents/`, it checks three things:
  1. Does the content contain a docstring (text between `"""`)? Every agent
     file must have one explaining what it does.
  2. Does the content contain `async def run(`? Every Clarity agent must
     expose a single entry point called `run`.
  3. Is the file under 300 lines? Agents must stay small so other AI agents
     can read the whole file at once.
- If any check fails, it exits with code 2, which cancels the write entirely
  and shows the error message to Claude, forcing it to fix the issue first.

**Why exit code 2 specifically:** Claude Code has a specific convention:
exit 0 = success, exit 1 = hook itself failed, exit 2 = block Claude and
show the error as a reason.

---

### .claude/hooks/run-tests-on-edit.sh — Automatic Test Runner

**What it is:** A PostToolUse hook that fires after Claude writes a file.

**What it does:**
- Reads the file path that was just written
- If the file is NOT in `backend/` and is NOT a `.py` file, does nothing
- If it IS a Python file in `backend/`, runs the full test suite:
  `python3 -m pytest --tb=short -q`
- If tests pass, prints "All tests passed" and exits 0
- If tests fail, prints the pytest output and the failure reason, then
  exits with code 2 — which tells Claude Code the action failed and
  Claude must address the failure before continuing

**Why this is PostToolUse, not PreToolUse:** The file needs to exist on disk
before tests can run against it. PreToolUse fires before the write, so the
file would not exist yet. PostToolUse fires after, so tests run against
the actual saved code.

---

### .claude/hooks/audit-logger.sh — Privacy Audit Trail

**What it is:** An async PostToolUse hook that fires after every single tool
Claude uses. "Async" means Claude does not wait for it — it runs in the
background while Claude continues.

**What it does:**
- Receives a JSON object describing what tool was just used and with what inputs
- Writes stdin to a temporary file (to avoid quoting and escaping issues
  with complex data)
- Runs a Python script that reads that file and extracts:
  - The timestamp (in UTC, the international time standard)
  - The tool name (e.g. "Write", "Read", "mcp__google-calendar__list_events")
  - The resource accessed (file path for Read/Write, MCP service name for
    data fetches, first word of the command for Bash)
  - The session ID
  - Whether this was an MCP data access event (i.e. personal data was fetched)
- Appends one line of structured JSON to `.clarity-audit.jsonl`
- Deletes the temporary file

**What the audit file looks like:**
```
{"ts": "2026-04-07T09:00:01Z", "event": "mcp_data_access", "tool": "mcp__google-calendar__list_events", "resource": "google-calendar", "session_id": "abc123", "user_facing": true}
{"ts": "2026-04-07T09:00:02Z", "event": "tool_use", "tool": "Write", "resource": ".clarity-cache/calendar-2026-03-30.json", "session_id": "abc123", "user_facing": false}
```

**Why this matters:** Clarity reads your most personal data. This log means
you can always answer the question "what exactly did the AI read about me
and when?" The `user_facing: true` flag marks MCP events — real personal
data access — so they can be filtered separately from routine file operations.

**Why stdin goes to a temp file:** The previous version interpolated the raw
JSON into a Python heredoc using `$INPUT`. This broke silently when the JSON
contained quotes, backslashes, or newlines (all common in real tool output).
The temp file approach avoids all string escaping entirely.

---

### .claude/hooks/quality-gate.sh — Report Quality Enforcement

**What it is:** A Stop hook that fires when Claude finishes generating a response.

**What it does:**
1. Reads a retry counter from `.clarity-cache/.quality-retry-count`
   (starts at 0 if the file does not exist)
2. Checks if the response looks like a Clarity report (longer than 200
   characters and contains numbers — a quick heuristic)
3. If it does not look like a report, approves immediately (removes the
   counter file and exits 0)
4. If the retry counter has reached 2, gives up: writes a "degraded" quality
   flag to `.clarity-cache/.quality-flag.json` so the backend knows the report
   passed under duress, then exits 0 to stop the loop
5. If we are within the retry budget, runs three checks on the report text:
   - Is it over 400 words? (Too long)
   - Does it cite fewer than 2 numbers? (Not data-driven enough)
   - Does it contain generic phrases like "try to", "you should", "consider",
     or "productivity"? (Forbidden language in Clarity reports)
6. If any check fails, increments the retry counter, prints the reason,
   and exits 2 — which blocks Claude's response from being shown and
   forces it to regenerate
7. If all checks pass, deletes the counter file and the quality flag file,
   and exits 0

**Why a retry budget:** Without one, a buggy report could loop forever.
Two retries is enough to catch genuine mistakes; if Claude cannot fix it
in two tries, passing with a "degraded" flag is better than an infinite loop.

**Why shell checks instead of an AI quality reviewer:** An earlier version
used a separate Claude API call (a "prompt hook") to review the report.
This was replaced with shell checks because: it costs money (every report
review = another AI inference call), it is slower, and the three quality
rules are specific enough to be checked mechanically. You do not need AI
to count words or grep for "you should".

---

### .claude/hooks/agent-timer.sh — Subagent Timing Log

**What it is:** An async hook that fires when a subagent starts or stops.

**What it does:**
- Reads the event type (SubagentStart or SubagentStop) and the agent ID
  from the JSON input
- Appends a timestamped line to `.clarity-audit.jsonl`

This is simpler than the full audit logger — it just records when AI subagents
(like the pattern detector) spin up and finish, so you can see how long
pattern detection takes and confirm it ran before the report was generated.

---

### .claude/rules/ — Coding Standards

These are three files that Claude Code reads whenever it works on files
matching their glob patterns. Think of them as standing instructions for
how code in this project must be written.

**python.md** (applies to all `.py` files):
- Every function must have type hints: instead of `def process(data)`, you
  write `def process(data: dict) -> list:` so it is always clear what goes
  in and what comes out
- Every public function must have a docstring explaining what it does
- Use `structlog` for logging, never `print()` — so logs are structured and
  searchable, not just text on a terminal
- Raise specific exceptions, never bare `Exception` — so errors are descriptive
- Use `async/await` for all I/O — so the server does not freeze while
  waiting for database or API responses

**typescript.md** (applies to all `.ts` and `.tsx` files):
- Strict mode always on — TypeScript's strictest type checking enabled
- No `any` types — if you do not know the type, use `unknown` and narrow it
  explicitly rather than bypassing the type system
- Export types alongside their implementations
- Use `const` assertions for literal types
- Prefer `type` over `interface` for simple data shapes

**agents.md** (applies to `agents/**/*.py` and `.claude/agents/**/*.md`):
- Every agent must have typed input and output dataclasses — the data
  going in and coming out must be formally defined
- Use the Agent SDK Claude Code client, never raw API calls
- Agents must not exceed 300 lines — keeps them readable by other AI agents
- Always include error handling with specific fallback behaviour
- Log agent decisions with structlog at INFO level

---

### .claude/skills/ — Playbooks for Specific Tasks

Skills are detailed instruction sets for Claude. When a skill is invoked
(either automatically or by typing `/skill-name`), Claude reads the skill's
`SKILL.md` file and follows its instructions precisely. Think of each skill
as a recipe card: it lists the ingredients (allowed tools), the steps in order,
and the rules that must never be broken.

Each skill has a frontmatter section (the block between `---` lines at the top)
that configures how it behaves, and a body that is the actual playbook.

---

#### skill: ingest-calendar

**Invocation:** Auto — fires automatically when Google Calendar JSON appears
in the conversation context.

**What it does:** Takes raw calendar event data (as fetched from Google Calendar
via MCP) and strips it down to signals only. It never stores meeting titles,
attendee names, or descriptions. It only computes numbers:

- Total meeting hours per day
- How many meetings were back-to-back (less than 15 minutes gap)
- How many meetings had 4+ attendees (high cognitive load)
- How many meetings were before 9am or after 6pm (boundary violations)
- The longest uninterrupted block of free time (focus block) each day
- Which days had no free time at all

It also looks for weekly patterns: days with 3+ meetings, weeks with no
free evenings, and recurring meetings that dominate the schedule.

**Output:** Writes `.clarity-cache/calendar-{YYYY-MM-DD}.json` with just
the numerical signals — no personal content.

**Allowed tools:** Read, Write, Bash

---

#### skill: ingest-email

**Invocation:** Auto — fires when Gmail metadata appears in context.

**Critical rule:** Never reads email body content. Only works with metadata.

**What it does:** Takes Gmail message metadata (subject line first 5 words only,
sender domain, timestamp, thread length) and extracts stress signals:

- Total emails received per day
- Emails sent after 9pm (late-night work)
- Unread count at end of week
- Threads with 5+ replies (high cognitive overhead)
- Emails from your manager outside business hours
- Threads unanswered for 3+ days (avoidance signal)
- Days where sent emails spike more than 50% above the weekly average

**Output:** Writes `.clarity-cache/email-{YYYY-MM-DD}.json`

**Allowed tools:** Read, Write (no Bash — email data needs tighter constraints)

---

#### skill: ingest-tasks

**Invocation:** Manual — you must type `/ingest-tasks` explicitly.

**Why manual when the others are auto:** Task data is intentional. You chose
to look at it. Unlike calendar data that arrives unsolicited, your Todoist
tasks carry psychological weight ("call therapist", "pay overdue tax bill").
Running this automatically every time task data appears could surface
uncomfortable patterns at the wrong moment. Manual invocation means
you explicitly chose to look.

**Critical privacy rule:** Never stores task titles or descriptions.
Classifies each task by keyword into a category (financial, personal,
communication, work, admin) and immediately discards the title.

**What it extracts:**
- Completion rate by category
- Tasks moved or rescheduled more than twice (avoidance signal) — count
  and category only, never title
- Tasks unstarted for 7+ days — count and category only
- Days with zero task completions
- Most-avoided category (highest move rate)
- Correlation between high-meeting days and zero-completion days

**Output:** Writes `.clarity-cache/tasks-{YYYY-MM-DD}.json`

---

#### skill: analyze-week

**Invocation:** Manual — type `/analyze-week` or `/analyze-week 2026-04-07`

**What it does:** The coordinator skill. Orchestrates the entire data
collection and ingestion pipeline for one week. Runs five steps in order:

1. **Determines the week range** — defaults to last Monday if no date given
2. **Fetches data via MCP** — calls Google Calendar, Gmail, and Todoist
   APIs directly through the MCP servers configured in Claude Code
3. **Runs all three ingestion skills** — triggers ingest-calendar,
   ingest-email, and ingest-tasks in sequence
4. **Merges cache files** — reads the three `.json` files just written
   and combines them into a single `snapshot-{date}.json` file
5. **Reports a summary** — prints how many meetings, tasks, and emails
   were found, notes anything immediately significant, and confirms
   the snapshot is ready for analysis

**Why never skip a data source:** Even if a source appears empty (no tasks
this week, no late emails), the absence of signals is itself a signal.
An empty category is different from a category that was not checked.

**Allowed tools:** Read, Write, Bash, and the three MCP tools for
Google Calendar, Gmail, and Todoist.

---

#### skill: detect-patterns

**Invocation:** Auto — fires after a snapshot is available.

**Special behaviour:** `run-in-subagent: true` — this skill does not run
inside the main conversation. The harness spawns a completely separate
AI process (a subagent) to do this work. The subagent starts with a clean
context window, does the analysis, writes the output file, and reports back.
The main conversation never sees the intermediate reasoning.

**Model:** Claude Haiku — the fastest and cheapest Claude model, used here
because the pattern detection rules are well-specified and deterministic.
Expensive models (Sonnet, Opus) are not needed for structured signal analysis.

**Why a subagent:** Pattern detection reads 4 weeks of snapshot files and
does extensive cross-week comparison. This generates a lot of intermediate
reasoning. Running it inline would bloat the main conversation context
significantly, making everything slower and more expensive. The subagent
absorbs that cost in isolation.

**What it reads:** The 4 most recent snapshot files (one per week). If fewer
than 4 exist, it works with what is available and notes the limited history.

**Patterns it looks for:**

*Depletion Cascade* — 3+ meetings on a day → evening has no completed tasks →
next morning starts late or shows avoidance. Evidence required: calendar
overload + task completion drop + email timing shift. Severity HIGH if it
happens 2+ times in the week.

*Avoidance Loop* — same task category moved 3+ times in a week. Severity HIGH
if financial or personal category, MEDIUM if work.

*Boundary Erosion* — consistent after-hours work signals across 3+ days.
Evidence: late email sends + out-of-hours meetings. Severity MEDIUM normally,
HIGH if this has persisted 3+ consecutive weeks.

*Social Withdrawal* — personal tasks (calls, messages to friends and family)
consistently uncompleted or moved. Severity always HIGH — this one is always
flagged regardless of other context.

**Severity escalation:** A pattern seen once = LOW. Two consecutive weeks = MEDIUM.
Three or more consecutive weeks = HIGH. This is why reading 4 weeks of history
is essential — a single week cannot determine severity accurately.

**Output:** Writes `.clarity-cache/patterns-{date}.json`

---

#### skill: generate-report

**Invocation:** Manual — type `/generate-report`

**Supporting files:**
- `report-template.md` — the structural template for every section
- `example-output.md` — a complete example report showing the target voice

These files are only loaded into context when this skill runs — they are
not always present in memory. The `@filename.md` syntax in the playbook
tells Claude to read them relative to the skill's directory.

**What it does:** Reads the patterns file and the snapshot file, then writes
the weekly report following strict rules:

- Opens with 2-3 factual sentences: numbers, not impressions
- One paragraph per detected pattern: names the pattern, shows the evidence,
  connects it to how the user probably feels without telling them how they feel
- One sentence connecting all patterns to a single root cause
- One final "honest thing": the single most useful truth in the data

**Hard rules — no exceptions:**
- Never use the word "productivity"
- Never suggest apps, tools, or systems
- Never give generic advice ("try to get more sleep")
- Every claim must cite a specific number from the snapshot data
- The report must be under 400 words

**Output:** Writes both a Markdown version and a JSON version of the report
to `.clarity-cache/`, so the frontend can display it.

---

#### skill: cleanup-cache

**Invocation:** Manual — type `/cleanup-cache`. Only run when warned by
session-start that the cache has more than 40 files.

**Always previews before deleting:** Shows exactly which files will be kept
and which will be deleted, then asks for confirmation. Only deletes after
you confirm.

**What it keeps:** The 4 most recent files of each type (snapshot, patterns,
report, calendar, email, tasks). Never deletes files less than 24 hours old.
Never deletes `.quality-flag.json` or `.quality-retry-count` (these are
state files the quality gate needs).

**After cleanup:** Reports how many files were deleted and the current
remaining cache size.

---

## Part 2: The Documents (docs/)

---

### docs/architecture.md — System Architecture

Describes the data flow and the agent team at a high level. Key content:

**Data flow:** 7 stages from MCP fetch → ingest → cache → detect → report →
store → deliver. (Described in full at the top of this document.)

**Agent team (four agents):**
- `pattern-detector` — uses Haiku, read-only, detects cross-week patterns
- `load-analyzer` — uses Sonnet, has financial MCP access, analyses capacity
  versus demand (e.g. you have 40 hours of meetings against 40 hours of work time)
- `insight-writer` — uses Sonnet, synthesises analysis into the honest narrative
- `conversation` — uses Sonnet, answers follow-up questions using the report
  as context ("why did you say I'm depleted on Wednesdays?")

**Privacy model:** Raw content is never stored. Only derived signals and
final reports go to the database. The user can delete all their data at any time.

---

### docs/schema.md — Database Schema

Defines every table in the Supabase database. This is the contract between
the backend code and the database. Key tables:

**users** — one row per Clarity user. Stores email and which data sources
are connected (calendar, Gmail, Todoist, finance). OAuth tokens themselves
are NOT stored here — they are in Supabase Vault (a secure encrypted store
separate from the main database).

**weekly_snapshots** — one row per user per week. Stores all the derived
signals from calendar, email, tasks, and finance. No raw content.
Has a `UNIQUE(user_id, week_start)` constraint — you cannot have two
snapshots for the same user for the same week.

**pattern_signals** — one row per detected pattern per week. References
the snapshot it was derived from. Stores pattern type, severity, evidence
array, days affected, how many times this pattern has appeared historically,
and how many consecutive weeks it has been seen.

**weekly_reports** — one row per user per week. Stores the full report text,
the JSON version, word count, quality score (passed or passed with degraded flag),
and how many patterns were detected.

**alert_triggers** — stores proactive alerts to be sent to the user.
For example, if Social Withdrawal is detected at HIGH severity, this table
might store a push notification to be sent.

**Authentication pattern:** OAuth tokens for Google and Todoist are in
Supabase Vault, never in environment variables or code. A file at
`backend/src/auth/token_refresh.py` handles refreshing expired tokens.
This file must be built first before any MCP connections can work.

**Hook authentication:** Every HTTP POST from Claude Code hooks to the
backend must include an `X-Clarity-Secret` header. The backend validates
this against an environment variable `CLARITY_HOOK_SECRET`. This prevents
any other process on the machine from spoofing hook events.

---

### docs/how-it-works.md

This file. The complete end-to-end guide.

---

## Part 3: The Application Code

The application code (frontend, backend, agents) is defined but not yet built.
The documents, database schema, coding rules, and Claude Code configuration
are complete. This section describes what will be built in each directory.

---

### frontend/ — The Next.js Web Application

Will contain the website users see. Based on the architecture and tech stack:

- Built with Next.js 14 (App Router), TypeScript, and Tailwind CSS
- Deployed to Vercel
- Key pages:
  - Dashboard — shows the current week's report and patterns
  - Report view — the full weekly report with visualisations
  - Conversation — chat interface for asking follow-up questions
  - Settings — connect/disconnect Google Calendar, Gmail, Todoist, finance

**Important rule:** The frontend never makes direct API calls to Google,
Todoist, or Claude. All AI and external data calls go through the backend.
The frontend only talks to `backend/`.

---

### backend/ — The FastAPI Server

Will contain the Python server. Deployed to Railway.

- Built with FastAPI and Pydantic, Python 3.11
- Connects to Supabase as the database
- Key responsibilities:
  - User authentication (Supabase Auth)
  - OAuth token management (connecting Google, Todoist accounts)
  - Hook endpoints (receives HTTP POSTs from Claude Code hooks)
  - Storing and retrieving snapshots, patterns, and reports from Supabase
  - Serving report data to the frontend

The first file to build is `backend/src/auth/token_refresh.py` — the
OAuth token refresh logic. Nothing else can work until tokens are managed.

**Hook endpoint** (`POST /api/hooks/session-stop`):
- Must validate `X-Clarity-Secret` header against `CLARITY_HOOK_SECRET` env var
- Receives notification when a Claude Code session ends
- Can trigger cleanup tasks, persist session metadata, etc.

---

### agents/ — The AI Agent Code

Will contain the Python orchestration code for the four AI agents.
All agents must follow the rules in `.claude/rules/agents.md`:

- Typed input and output dataclasses
- Single `async def run()` entry point
- Maximum 300 lines per file
- Structlog logging at INFO level for every decision
- Specific error handling with defined fallback behaviour

The agents are coordinated by an orchestrator (not yet built) that:
1. Calls `pattern-detector` and `load-analyzer` in parallel (they can
   run simultaneously since they read the same snapshot independently)
2. Waits for both to finish
3. Passes their results to `insight-writer`
4. Returns the report

---

## Part 4: The Local Cache (.clarity-cache/)

This folder lives on your computer and is never committed to git or
synced to Supabase. It holds intermediate working files that are created
during a session and rotated after 4 weeks.

**File naming:** `{type}-{YYYY-MM-DD}.json`

| Type | Created by | Contents |
|---|---|---|
| `calendar-` | ingest-calendar | Meeting load signals for the week |
| `email-` | ingest-email | Email volume and stress signals |
| `tasks-` | ingest-tasks | Task completion and avoidance signals |
| `snapshot-` | analyze-week | Merged view of all three signal types |
| `patterns-` | detect-patterns | Detected patterns with severity and evidence |
| `report-` | generate-report | The final report in Markdown and JSON |

**Special files (never deleted):**
- `.quality-flag.json` — written when a report passes with a degraded quality flag
- `.quality-retry-count` — tracks how many times the quality gate has retried

---

## Part 5: The Audit Trail (.clarity-audit.jsonl)

This file lives at the project root and is gitignored (never committed to git).
Every tool call Claude makes during a session is appended to this file.

JSONL means "JSON Lines" — each line is a separate, complete JSON object.
This format is designed for append-only logs that grow over time.

**You can read it to answer:** "Did the AI read my email this session?
What exactly did it access? When?" The `user_facing: true` flag marks
every MCP data access event — real personal data — separately from
routine file read/write operations.

---

## How a Complete Weekly Analysis Works — Step by Step

Here is what happens when you type `/analyze-week`:

1. Claude Code receives the command and loads the `analyze-week` skill playbook
2. Claude calculates the most recent completed week (last Monday to Sunday)
3. Claude calls `mcp__google-calendar__list_events` — the MCP server connects
   to Google Calendar and returns your events for the week as raw JSON
4. `audit-logger.sh` fires (async, background) — records this MCP access
5. The raw calendar JSON is now in Claude's context — `ingest-calendar`
   fires automatically (it is an auto skill triggered by this data)
6. ingest-calendar computes signals from the events, writes
   `.clarity-cache/calendar-2026-03-30.json`, discards all raw event data
7. Claude calls `mcp__gmail__list_messages` — gets email metadata
8. `audit-logger.sh` fires again
9. `ingest-email` fires automatically
10. Email signals written to `.clarity-cache/email-2026-03-30.json`
11. Claude calls `mcp__todoist__get_tasks` — gets task data
12. `audit-logger.sh` fires again
13. Claude runs the `ingest-tasks` playbook (manual skill, but being
    coordinated by `analyze-week`)
14. Task signals written to `.clarity-cache/tasks-2026-03-30.json`
15. Claude reads all three cache files and merges them into
    `.clarity-cache/snapshot-2026-03-30.json`
16. Claude prints a summary: "14 meetings, 11 tasks, 340 emails. Snapshot ready."
17. Claude's response finishes
18. The Stop hook fires: `quality-gate.sh` checks if this was a report
    (it is not — it is just a summary) and approves immediately
19. The HTTP POST fires async to the backend

Then you type `/detect-patterns`:

20. Claude Code loads the detect-patterns skill
21. The harness spawns a subagent (a separate Claude Haiku process)
22. `agent-timer.sh` fires, recording the subagent start time
23. The subagent reads the last 4 snapshot files to build cross-week context
24. The subagent analyses signals: finds a Depletion Cascade (3 days with 3+
    meetings and zero evening task completions), an Avoidance Loop (personal
    category moved 3 times this week, 2nd consecutive week)
25. Subagent writes `.clarity-cache/patterns-2026-03-30.json` with severity
    ratings and evidence
26. Subagent finishes
27. `agent-timer.sh` fires again, recording the subagent stop time
28. The main session receives the subagent's result

Then you type `/generate-report`:

29. Claude loads the generate-report skill
30. Claude reads `report-template.md` (voice structure) and
    `example-output.md` (target tone) from the skill's directory
31. Claude reads `patterns-2026-03-30.json` and `snapshot-2026-03-30.json`
32. Claude writes the report: opens with the numbers, one paragraph per
    pattern connecting data to feeling without telling you how to feel,
    one connecting sentence, one honest final observation
33. Report written to `.clarity-cache/report-2026-03-30.md` and
    `.clarity-cache/report-2026-03-30.json`
34. Claude finishes
35. Stop hook fires: `quality-gate.sh` detects this looks like a report
36. Checks: under 400 words ✓, cites numbers ✓, no generic advice ✓
37. Quality gate approves (exits 0), retry counter file deleted
38. HTTP POST fires to backend (with `X-Clarity-Secret` header)
39. Backend receives it, validates the secret, stores the report in Supabase
40. Frontend displays the report in your browser

---

## Key Constraints to Never Violate

These are not preferences — they are structural requirements of the system:

1. **Never store raw personal data.** No email body, no meeting title,
   no task name, no attendee name. Only derived signals survive ingestion.
   Violating this breaks the privacy model the entire product is built on.

2. **Never make AI or external API calls from the frontend.** All Claude
   calls go through `agents/`. All external data fetches go through MCP
   servers called from Claude Code skills or agents. The frontend only
   talks to the FastAPI backend.

3. **Never skip tests.** The `run-tests-on-edit.sh` hook enforces this
   automatically for backend Python files. The rule in `CLAUDE.md` enforces
   it for everything else: write tests before implementation.

4. **Never write agent files over 300 lines.** The `validate-agent-structure.sh`
   hook blocks agent files that exceed 300 lines. Agents must be small enough
   for another AI agent to read and understand the whole file at once.

5. **Never leave `historical_frequency` at 0 in pattern output without
   checking prior snapshots.** This field must reflect real history.
   A pattern that has happened three weeks in a row has severity HIGH,
   not LOW. The detect-patterns skill reads 4 weeks of history specifically
   to compute this correctly.

---

## Environment Variables Required

These must exist before the system can run:

| Variable | Purpose |
|---|---|
| `CLARITY_HOOK_SECRET` | Shared secret between Claude Code and the FastAPI backend, used to authenticate HTTP hook POSTs |
| `ANTHROPIC_API_KEY` | API key for the Claude AI models |
| `SUPABASE_URL` | The URL of the Supabase project |
| `SUPABASE_SERVICE_KEY` | Backend-only Supabase key with full database access |
| `SUPABASE_ANON_KEY` | Frontend-safe Supabase key (limited access) |

OAuth tokens for Google Calendar, Gmail, and Todoist are stored in
Supabase Vault after the user connects their accounts — they are never
environment variables.

---

## How to Start the Development Environment

```bash
# 1. Start the Supabase local database
npx supabase start

# 2. Start the FastAPI backend
cd backend
uvicorn main:app --reload

# 3. Start the Next.js frontend
cd frontend
npm run dev

# 4. Run backend tests
cd backend
pytest
```

When you open a Claude Code session, `session-start.sh` will automatically
check that steps 1 and 2 are running and tell you if they are not.
