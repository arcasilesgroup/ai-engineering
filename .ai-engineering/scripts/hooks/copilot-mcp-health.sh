#!/usr/bin/env bash
# Copilot wrapper for mcp-health.py: MCP server health monitoring.
# Called by GitHub Copilot hooks (preToolCall and postToolCallFailure events).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# MUST preserve exit code 2 for blocking — non-fail-open.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
. "$SCRIPT_DIR/_lib/copilot-common.sh"
. "$SCRIPT_DIR/_lib/copilot-runtime.sh"

read_stdin_payload >/dev/null

# Detect Copilot event from payload (postToolCallFailure carries error fields).
COPILOT_EVENT="PreToolUse"
if command -v jq >/dev/null 2>&1 && [ -n "$PAYLOAD" ]; then
    if printf '%s' "$PAYLOAD" | jq -e 'has("error") or has("failure") or has("errorMessage")' >/dev/null 2>&1; then
        COPILOT_EVENT="PostToolUseFailure"
    fi
fi

TRANSLATED=$(printf '%s' "$PAYLOAD" | copilot_framework_python_inline "$PROJECT_DIR" <<'PY'
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

export CLAUDE_HOOK_EVENT_NAME="$COPILOT_EVENT"
echo "$TRANSLATED" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/mcp-health.py"
exit $?
