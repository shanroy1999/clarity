# Clarity architecture

## Data flow
1. MCP servers fetch raw data (calendar, email, tasks, finance)
2. Ingestion skills normalize raw data into the Clarity schema
3. Orchestrator agent coordinates specialist agents
4. Specialist agents run in parallel: pattern-detector + load-analyzer
5. Insight-writer agent synthesizes results into weekly report
6. Report stored in Supabase, delivered to frontend
7. Conversation agent handles follow-up questions

## Core data model
- LifeLoadSnapshot: normalized week of data (meetings, tasks, emails, spend)
- PatternSignal: a detected pattern with evidence and severity
- WeeklyReport: the final insight document with signals and narrative
- AlertTrigger: a condition that causes a proactive notification

## Agent team
- pattern-detector: Haiku, read-only, detects cross-time behavioral patterns
- load-analyzer: Sonnet, financial MCP access, analyses capacity vs demand
- insight-writer: Sonnet, synthesizes analysis into honest narrative
- conversation: Sonnet, answers follow-up questions using report as context

## Privacy model
- Raw calendar/email content never stored in database
- Only derived signals and insights persisted
- All MCP data processed in-memory within agent context
- User can delete all their data at any time
