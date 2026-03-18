#!/usr/bin/env bash
# Telemetry hook: emit agent_dispatched event on PostToolUse(Agent).
# Called by Claude Code and GitHub Copilot hooks.
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

# Read JSON from stdin (PostToolUse event data)
INPUT=$(cat)

# Extract agent type using jq, fallback to python3
extract_agent() {
    if command -v jq >/dev/null 2>&1; then
        echo "$INPUT" | jq -r '.tool_input.subagent_type // .tool_input.description // empty' 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    if isinstance(ti, str):
        import json as j
        ti = j.loads(ti)
    print(ti.get('subagent_type', ti.get('description', '')))
except Exception:
    pass
" 2>/dev/null
    fi
}

extract_description() {
    if command -v jq >/dev/null 2>&1; then
        echo "$INPUT" | jq -r '.tool_input.description // empty' 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    if isinstance(ti, str):
        import json as j
        ti = j.loads(ti)
    print(ti.get('description', ''))
except Exception:
    pass
" 2>/dev/null
    fi
}

AGENT_TYPE=$(extract_agent)
DESCRIPTION=$(extract_description)

# Skip if no agent type extracted
[ -z "$AGENT_TYPE" ] && exit 0

# Resolve project root
ROOT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Activate venv if present
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate" 2>/dev/null
elif [ -f "$ROOT_DIR/.venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/Scripts/activate" 2>/dev/null
fi

# Emit event — fail-open
ai-eng signals emit agent_dispatched \
    --actor=ai \
    --source=hook \
    --detail="{\"agent\":\"${AGENT_TYPE}\",\"description\":\"${DESCRIPTION}\"}" \
    2>/dev/null || true

exit 0
