# Agent rules — orchestration layer

## Agent module structure
Every agent file must have:
1. A module docstring explaining what the agent does
2. A typed input dataclass
3. A typed output dataclass
4. A single run() async function
5. Tests in tests/agents/

## Principles
- Agents are stateless — all state goes to Supabase
- Keep agent files under 300 lines
- Never call external APIs directly — use MCP tools
- Always validate and type-check inputs before processing
- Log the start, key decisions, and end of every agent run
