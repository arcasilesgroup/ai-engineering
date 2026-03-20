#!/usr/bin/env bash
# Copilot telemetry hook: emit skill_invoked on userPromptSubmitted matching /ai-*.
# Called by GitHub Copilot hooks (userPromptSubmitted event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    # Read JSON from stdin (userPromptSubmitted event data)
    INPUT=$(cat)

    # Resolve project root from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
    AUDIT_LOG="$PROJECT_DIR/.ai-engineering/state/audit-log.ndjson"

    # Extract prompt from stdin JSON
    PROMPT=""
    if command -v jq >/dev/null 2>&1; then
        PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        PROMPT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('prompt', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    # Only match /ai-* slash commands (with optional args after space)
    [[ "$PROMPT" =~ ^/ai-([a-zA-Z-]+) ]] || return 0
    RAW="${BASH_REMATCH[1]}"

    # Normalize: lowercase, ensure ai- prefix
    SKILL_NAME="ai-$(echo "$RAW" | tr '[:upper:]' '[:lower:]')"

    # Git metadata (fail gracefully if not in a repo)
    BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    COMMIT=$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    # Timestamp: use stdin JSON timestamp if available, otherwise generate ISO-8601
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Emit NDJSON event to audit log
    if command -v jq >/dev/null 2>&1; then
        jq -n -c \
            --arg branch "$BRANCH" \
            --arg commit "$COMMIT" \
            --arg skill "$SKILL_NAME" \
            --arg ts "$TIMESTAMP" \
            '{actor:"ai",branch:$branch,commit_sha:$commit,detail:{skill:$skill},event:"skill_invoked",source:"hook",timestamp:$ts}' \
            >> "$AUDIT_LOG" 2>/dev/null
    else
        printf '{"actor":"ai","branch":"%s","commit_sha":"%s","detail":{"skill":"%s"},"event":"skill_invoked","source":"hook","timestamp":"%s"}\n' \
            "$BRANCH" "$COMMIT" "$SKILL_NAME" "$TIMESTAMP" >> "$AUDIT_LOG" 2>/dev/null
    fi
}

main || exit 0
exit 0
