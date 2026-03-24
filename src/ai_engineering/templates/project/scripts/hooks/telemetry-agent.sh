#!/usr/bin/env bash
# Telemetry hook: emit agent_dispatched event on PostToolUse(Agent).
# Called by Claude Code and GitHub Copilot hooks.
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

# Escape a string for safe JSON embedding in printf
safe_json_string() {
    local v="$1"
    v="${v//\\/\\\\}"
    v="${v//\"/\\\"}"
    v="${v//$'\n'/\\n}"
    v="${v//$'\r'/\\r}"
    v="${v//$'\t'/\\t}"
    printf '%s' "$v"
}

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

# Normalize: lowercase + ensure ai- prefix
AGENT_TYPE=$(echo "$AGENT_TYPE" | tr '[:upper:]' '[:lower:]')
AGENT_TYPE="${AGENT_TYPE#ai-}"
AGENT_TYPE="ai-${AGENT_TYPE}"

# Resolve project root
ROOT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
AUDIT_LOG="${ROOT_DIR}/.ai-engineering/state/audit-log.ndjson"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BRANCH=$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
COMMIT=$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo "")

# Write directly to audit log — no CLI dependency
printf '{"actor":"ai","agent":"%s","branch":"%s","commit_sha":"%s","detail":{"agent":"%s","description":"%s"},"event":"agent_dispatched","source":"hook","timestamp":"%s"}\n' \
    "$(safe_json_string "$AGENT_TYPE")" "$(safe_json_string "$BRANCH")" "$(safe_json_string "$COMMIT")" "$(safe_json_string "$AGENT_TYPE")" "$(safe_json_string "$DESCRIPTION")" "$(safe_json_string "$TIMESTAMP")" >> "$AUDIT_LOG" 2>/dev/null || true

# Debug mode
if [ "${AIENG_TELEMETRY_DEBUG:-}" = "1" ]; then
    DEBUG_LOG="${ROOT_DIR}/.ai-engineering/state/telemetry-debug.log"
    printf '[%s] agent_dispatched: %s (desc: %s)\n' "$(safe_json_string "$TIMESTAMP")" "$(safe_json_string "$AGENT_TYPE")" "$(safe_json_string "$DESCRIPTION")" >> "$DEBUG_LOG" 2>/dev/null || true
fi

exit 0
