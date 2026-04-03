#!/usr/bin/env bash
# Copilot wrapper for mcp-health.py: MCP server health monitoring.
# Called by GitHub Copilot hooks (preToolCall and postToolCallFailure events).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# MUST preserve exit code 2 for blocking — non-fail-open.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
source "$SCRIPT_DIR/_lib/copilot-runtime.sh"

# Read Copilot JSON from stdin
INPUT=$(cat)

# Detect Copilot event name from the JSON payload.
# postToolCallFailure includes error/failure indicators; preToolCall does not.
COPILOT_EVENT=$(copilot_framework_python_inline "$PROJECT_DIR" <<'PY'
import json
import sys

try:
    payload = json.load(sys.stdin)
    if "error" in payload or "failure" in payload or "errorMessage" in payload:
        print("PostToolUseFailure")
    else:
        print("PreToolUse")
except Exception:
    print("PreToolUse")
PY
) || COPILOT_EVENT="PreToolUse"

# Translate Copilot field names to Claude Code convention:
#   Copilot: { "toolName": "...", "toolArgs": {...} }
#   Claude:  { "tool_name": "...", "tool_input": {...} }
TRANSLATED=$(copilot_framework_python_inline "$PROJECT_DIR" <<'PY'
import json
import sys

try:
    payload = json.load(sys.stdin)
    out = {}
    for key, value in payload.items():
        if key == "toolName":
            out["tool_name"] = value
        elif key == "toolArgs":
            out["tool_input"] = value if isinstance(value, dict) else json.loads(value) if isinstance(value, str) else value
        elif key == "toolResult":
            out["tool_output"] = value
        else:
            out[key] = value
    json.dump(out, sys.stdout, separators=(",", ":"))
except Exception:
    sys.stdout.write(json.dumps({}))
PY
) || TRANSLATED="{}"

# Map Copilot event to Claude Code event name
export CLAUDE_HOOK_EVENT_NAME="$COPILOT_EVENT"

# Pipe translated input to Python script, preserve exit code (2 = block)
echo "$TRANSLATED" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/mcp-health.py"
exit $?
