#!/usr/bin/env bash
# Copilot telemetry hook: emit session_end on sessionEnd event.
# Called by GitHub Copilot hooks (sessionEnd event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    # Read JSON from stdin (sessionEnd event data)
    INPUT=$(cat)

    # Resolve project root from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    AUDIT_LOG="$PROJECT_DIR/.ai-engineering/state/audit-log.ndjson"

    # Extract reason from stdin JSON (complete/error/abort/timeout/user_exit)
    REASON=""
    if command -v jq >/dev/null 2>&1; then
        REASON=$(echo "$INPUT" | jq -r '.reason // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        REASON=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('reason', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    # Default reason if not provided
    [ -z "$REASON" ] && REASON="unknown"

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
            --arg reason "$REASON" \
            --arg ts "$TIMESTAMP" \
            '{actor:"ai-session",branch:$branch,commit_sha:$commit,detail:{type:"session_end",reason:$reason},event:"session_end",source:"hook",timestamp:$ts}' \
            >> "$AUDIT_LOG" 2>/dev/null
    else
        printf '{"actor":"ai-session","branch":"%s","commit_sha":"%s","detail":{"type":"session_end","reason":"%s"},"event":"session_end","source":"hook","timestamp":"%s"}\n' \
            "$BRANCH" "$COMMIT" "$REASON" "$TIMESTAMP" >> "$AUDIT_LOG" 2>/dev/null
    fi
}

main || exit 0
exit 0
