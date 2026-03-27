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

    if command -v python3 >/dev/null 2>&1; then
        PROJECT_DIR="$PROJECT_DIR" ERROR_NAME="$ERROR_NAME" ERROR_MESSAGE="$ERROR_MESSAGE" python3 - <<'PY' >/dev/null 2>&1 || true
import os
from pathlib import Path

from ai_engineering.state.observability import emit_framework_error, emit_ide_hook_outcome

project_root = Path(os.environ["PROJECT_DIR"])
emit_ide_hook_outcome(
    project_root,
    engine="github_copilot",
    hook_kind="error-occurred",
    component="hook.copilot-error",
    outcome="failure",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
emit_framework_error(
    project_root,
    engine="github_copilot",
    component="hook.copilot-error",
    error_code=os.environ["ERROR_NAME"] or "hook_error",
    summary=os.environ["ERROR_MESSAGE"],
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
PY
    fi
}

main || exit 0
exit 0
