---
name: review
description: >
  Run a full Clarity code review before committing. Checks privacy
  rules, architecture violations, missing tests, and type safety.
  Always run before git commit on backend or agent changes.
---

Review all staged and unstaged changes in the Clarity codebase.

Check for in this exact order:

## 1. Privacy violations (CRITICAL — block commit if found)
- Raw email body or subject stored anywhere
- Task titles stored instead of categories
- Calendar attendee names persisted
- Any PII written to .clarity-cache/ or Supabase
- MCP responses logged with raw content

## 2. Architecture violations
- Direct external API calls from frontend/
- Agent files over 300 lines
- AI calls outside the agents/ layer
- Missing type hints on Python functions
- `any` types in TypeScript

## 3. Missing tests
- New backend routes without at least one test
- New agent logic without a corresponding test file
- New skills without example input/output validation

## 4. Security issues
- Hardcoded secrets or API keys
- Missing hook secret validation on new FastAPI endpoints
- Unvalidated inputs on new routes

## 5. Hook and skill consistency
- New skills not registered correctly (name matches filename)
- New hooks not registered in .claude/settings.json

For each issue: state the file, line number, what's wrong, and the fix.
If nothing found in a category, say "clean" and move on.
End with a one-line verdict: READY TO COMMIT or ISSUES FOUND.
