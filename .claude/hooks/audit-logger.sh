#!/bin/bash

# PostToolUse async hook — structured JSONL audit trail
# Logs all tool calls; flags MCP data-access events separately
# Schema: {ts, event, tool, resource, session_id, user_facing}

AUDIT_FILE=".clarity-audit.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Read stdin into a temp file — avoids all quoting issues
TMPFILE=$(mktemp)
cat > "$TMPFILE"

python3 - "$TMPFILE" "$TIMESTAMP" "$AUDIT_FILE" << 'PYEOF'
import json, sys

tmpfile   = sys.argv[1]
timestamp = sys.argv[2]
audit     = sys.argv[3]

try:
    with open(tmpfile) as f:
        data = json.load(f)
except Exception:
    data = {}

tool_name  = data.get("tool_name", "unknown")
tool_input = data.get("tool_input", {})
session_id = data.get("session_id", "unknown")

is_mcp     = tool_name.startswith("mcp__")
event_type = "mcp_data_access" if is_mcp else "tool_use"

# Resource: never store content, only the identifier
if is_mcp:
    parts    = tool_name.split("__")
    resource = parts[1] if len(parts) > 1 else "unknown"
elif tool_name in ("Write", "Read"):
    resource = tool_input.get("file_path", "unknown")
elif tool_name == "Bash":
    cmd      = tool_input.get("command", "")
    resource = cmd.split()[0] if cmd else "unknown"
else:
    resource = None

entry = {
    "ts":          timestamp,
    "event":       event_type,
    "tool":        tool_name,
    "resource":    resource,
    "session_id":  session_id,
    "user_facing": is_mcp,
}

with open(audit, "a") as f:
    f.write(json.dumps(entry) + "\n")

PYEOF

rm -f "$TMPFILE"
exit 0
