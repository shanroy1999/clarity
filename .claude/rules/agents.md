---
globs: ["agents/**/*.py", ".claude/agents/**/*.md"]
---
# Agent-specific rules

- Every agent must have typed input and output dataclasses
- Use the Agent SDK ClaudeCode client, never raw API calls
- Agents must not exceed 300 lines
- Always include error handling with specific fallback behavior
- Log agent decisions with structlog at INFO level
