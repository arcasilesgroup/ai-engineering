#!/usr/bin/env bash
# Copilot telemetry hook: emit session_start on sessionStart event.
# Called by GitHub Copilot hooks (sessionStart event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    # Read JSON from stdin (sessionStart event data)
    INPUT=$(cat)

    # Resolve project root from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    AUDIT_LOG="$PROJECT_DIR/.ai-engineering/state/audit-log.ndjson"

    # Extract source from stdin JSON (new/resume/startup)
    SOURCE=""
    if command -v jq >/dev/null 2>&1; then
        SOURCE=$(echo "$INPUT" | jq -r '.source // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        SOURCE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('source', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    # Default source if not provided
    [ -z "$SOURCE" ] && SOURCE="unknown"

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
            --arg source "$SOURCE" \
            --arg ts "$TIMESTAMP" \
            '{actor:"ai-session",branch:$branch,commit_sha:$commit,detail:{type:"session_start",source:$source},event:"session_start",source:"hook",timestamp:$ts}' \
            >> "$AUDIT_LOG" 2>/dev/null
    else
        printf '{"actor":"ai-session","branch":"%s","commit_sha":"%s","detail":{"type":"session_start","source":"%s"},"event":"session_start","source":"hook","timestamp":"%s"}\n' \
            "$BRANCH" "$COMMIT" "$SOURCE" "$TIMESTAMP" >> "$AUDIT_LOG" 2>/dev/null
    fi
}

main || exit 0
exit 0
