#!/usr/bin/env bash
# Telemetry hook: emit skill_invoked event on PostToolUse(Skill).
# Called by Claude Code and GitHub Copilot hooks.
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

# Read JSON from stdin (PostToolUse event data)
INPUT=$(cat)

# Extract skill name using jq, fallback to python3
extract_skill() {
    if command -v jq >/dev/null 2>&1; then
        echo "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    if isinstance(ti, str):
        import json as j
        ti = j.loads(ti)
    print(ti.get('skill', ''))
except Exception:
    pass
" 2>/dev/null
    fi
}

SKILL_NAME=$(extract_skill)

# Skip if no skill name extracted
[ -z "$SKILL_NAME" ] && exit 0

# Normalize: lowercase + ensure ai- prefix
CANONICAL_NAME=$(echo "$SKILL_NAME" | tr '[:upper:]' '[:lower:]')
CANONICAL_NAME="${CANONICAL_NAME#ai-}"   # strip if already has, to re-add clean
CANONICAL_NAME="${CANONICAL_NAME#ai:}"   # strip colon variant
CANONICAL_NAME="ai-${CANONICAL_NAME}"    # ensure prefix

# Resolve project root
ROOT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
AUDIT_LOG="${ROOT_DIR}/.ai-engineering/state/audit-log.ndjson"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BRANCH=$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
COMMIT=$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo "")

# Write directly to audit log — no CLI dependency
printf '{"actor":"ai","branch":"%s","commit_sha":"%s","detail":{"skill":"%s"},"event":"skill_invoked","source":"hook","timestamp":"%s"}\n' \
    "$BRANCH" "$COMMIT" "$CANONICAL_NAME" "$TIMESTAMP" >> "$AUDIT_LOG" 2>/dev/null || true

# Debug mode
if [ "${AIENG_TELEMETRY_DEBUG:-}" = "1" ]; then
    DEBUG_LOG="${ROOT_DIR}/.ai-engineering/state/telemetry-debug.log"
    printf '[%s] skill_invoked: %s (raw: %s)\n' "$TIMESTAMP" "$CANONICAL_NAME" "$SKILL_NAME" >> "$DEBUG_LOG" 2>/dev/null || true
fi

exit 0
