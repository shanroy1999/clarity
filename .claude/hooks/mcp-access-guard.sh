#!/bin/bash

# PreToolUse hook — intercepts MCP data access events
# Logs what data is being fetched and enforces read-only access
# Fires before any mcp__ tool call

TMPFILE=$(mktemp)
cat > "$TMPFILE"

python3 - "$TMPFILE" << 'PYEOF'
import json, sys
from datetime import datetime, timezone

tmpfile = sys.argv[1]

try:
    with open(tmpfile) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

tool_name  = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "unknown")

# Only process MCP tool calls
if not tool_name.startswith("mcp__"):
    sys.exit(0)

# Extract the MCP server and tool
parts = tool_name.split("__")
server = parts[1] if len(parts) > 1 else "unknown"
tool   = parts[2] if len(parts) > 2 else "unknown"

# Block any MCP tool that writes or deletes
dangerous_verbs = ["create", "delete", "update", "modify",
                   "write", "send", "insert", "patch", "post"]
if any(v in tool.lower() for v in dangerous_verbs):
    print(f"BLOCKED: {tool_name} — Clarity only reads data, never writes to external services.")
    sys.exit(2)

# Log the access
log_entry = {
    "ts":         datetime.now(timezone.utc).isoformat(),
    "event":      "mcp_access_approved",
    "server":     server,
    "tool":       tool,
    "session_id": session_id,
}

with open(".clarity-audit.jsonl", "a") as f:
    f.write(json.dumps(log_entry) + "\n")

sys.exit(0)
PYEOF

rm -f "$TMPFILE"
exit 0
