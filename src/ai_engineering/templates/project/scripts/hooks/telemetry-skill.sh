#!/usr/bin/env bash
# Telemetry hook: emit skill_invoked on UserPromptSubmit matching /ai-*.
# Called by Claude Code hooks (UserPromptSubmit event).
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

# Read JSON from stdin (UserPromptSubmit event data)
INPUT=$(cat)

# Extract prompt from stdin JSON
extract_prompt() {
    if command -v jq >/dev/null 2>&1; then
        echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('prompt', ''))
except Exception:
    pass
" 2>/dev/null
    fi
}

PROMPT=$(extract_prompt)

# Only match /ai-* slash commands (with optional args after space)
[[ "$PROMPT" =~ ^/ai-([a-zA-Z-]+) ]] || exit 0
RAW="${BASH_REMATCH[1]}"
SKILL_NAME="ai-$(echo "$RAW" | tr '[:upper:]' '[:lower:]')"

# Resolve project root
ROOT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
AUDIT_LOG="${ROOT_DIR}/.ai-engineering/state/audit-log.ndjson"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BRANCH=$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
COMMIT=$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo "")

# Write directly to audit log — no CLI dependency
printf '{"actor":"ai","branch":"%s","commit_sha":"%s","detail":{"skill":"%s"},"event":"skill_invoked","source":"hook","timestamp":"%s"}\n' \
    "$(safe_json_string "$BRANCH")" "$(safe_json_string "$COMMIT")" "$(safe_json_string "$SKILL_NAME")" "$(safe_json_string "$TIMESTAMP")" >> "$AUDIT_LOG" 2>/dev/null || true

# Debug mode
if [ "${AIENG_TELEMETRY_DEBUG:-}" = "1" ]; then
    DEBUG_LOG="${ROOT_DIR}/.ai-engineering/state/telemetry-debug.log"
    printf '[%s] skill_invoked: %s (prompt: %s)\n' "$(safe_json_string "$TIMESTAMP")" "$(safe_json_string "$SKILL_NAME")" "$(safe_json_string "$PROMPT")" >> "$DEBUG_LOG" 2>/dev/null || true
fi

exit 0
