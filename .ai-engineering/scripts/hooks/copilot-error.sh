#!/usr/bin/env bash
# Copilot telemetry hook: emit error_occurred on errorOccurred event.
# Called by GitHub Copilot hooks (errorOccurred event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    # Read JSON from stdin (errorOccurred event data)
    INPUT=$(cat)

    # Resolve project root from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    AUDIT_LOG="$PROJECT_DIR/.ai-engineering/state/audit-log.ndjson"

    # Extract error.message and error.name from stdin JSON
    ERROR_NAME=""
    ERROR_MESSAGE=""
    if command -v jq >/dev/null 2>&1; then
        ERROR_NAME=$(echo "$INPUT" | jq -r '.error.name // empty' 2>/dev/null)
        ERROR_MESSAGE=$(echo "$INPUT" | jq -r '.error.message // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        ERROR_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('error', {}).get('name', ''))
except Exception:
    pass
" 2>/dev/null)
        ERROR_MESSAGE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('error', {}).get('message', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    # Default values if not provided
    [ -z "$ERROR_NAME" ] && ERROR_NAME="unknown"
    [ -z "$ERROR_MESSAGE" ] && ERROR_MESSAGE="unknown"

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
            --arg ename "$ERROR_NAME" \
            --arg emsg "$ERROR_MESSAGE" \
            --arg ts "$TIMESTAMP" \
            '{actor:"ai-session",branch:$branch,commit_sha:$commit,detail:{type:"error_occurred",error_name:$ename,error_message:$emsg},event:"error_occurred",source:"hook",timestamp:$ts}' \
            >> "$AUDIT_LOG" 2>/dev/null
    else
        # Escape double quotes in error message for JSON safety
        SAFE_MSG=$(echo "$ERROR_MESSAGE" | tr '"' "'")
        printf '{"actor":"ai-session","branch":"%s","commit_sha":"%s","detail":{"type":"error_occurred","error_name":"%s","error_message":"%s"},"event":"error_occurred","source":"hook","timestamp":"%s"}\n' \
            "$BRANCH" "$COMMIT" "$ERROR_NAME" "$SAFE_MSG" "$TIMESTAMP" >> "$AUDIT_LOG" 2>/dev/null
    fi
}

main || exit 0
exit 0
