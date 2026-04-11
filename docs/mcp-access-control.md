# MCP access control — Clarity

## Principle
Each agent only gets access to the MCP servers it needs.
Least privilege applied at the agent level.

## Access matrix

| Agent              | google-calendar | gmail | todoist | clarity-financial |
|--------------------|:---------:|:-----:|:-------:|:-----------------:|
| pattern-detector   | read      | read  | read    | —                 |
| load-analyzer      | read      | —     | —       | read              |
| insight-writer     | —         | —     | —       | —                 |
| conversation       | —         | —     | —       | —                 |

## How to enforce in subagent frontmatter
```yaml
---
name: load-analyzer
allowed-mcp-servers:
  - clarity-financial
  - google-calendar
denied-mcp-servers:
  - gmail
  - todoist
---
```

## Why
- insight-writer and conversation read only from .clarity-cache/
  They never touch raw data sources — only derived signals
- load-analyzer owns financial data — no other agent needs it
- pattern-detector reads all signal types but not financial
  (financial signals already in the snapshot by the time it runs)