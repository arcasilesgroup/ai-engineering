#!/usr/bin/env bash
# Copilot telemetry hook: emit error_occurred on errorOccurred event.
# Called by GitHub Copilot hooks (errorOccurred event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    . "$SCRIPT_DIR/_lib/copilot-common.sh"
    . "$SCRIPT_DIR/_lib/copilot-runtime.sh"
    COPILOT_COMPONENT="hook.copilot-error"

    read_stdin_payload >/dev/null
    ERROR_NAME="$(read_stdin_payload .error.name)"
    ERROR_MESSAGE="$(read_stdin_payload .error.message)"
    [ -z "$ERROR_NAME" ] && ERROR_NAME="unknown"
    [ -z "$ERROR_MESSAGE" ] && ERROR_MESSAGE="unknown"

    PROJECT_DIR="$PROJECT_DIR" ERROR_NAME="$ERROR_NAME" ERROR_MESSAGE="$ERROR_MESSAGE" copilot_framework_python_inline "$PROJECT_DIR" <<'PY' >/dev/null 2>&1 || true
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_framework_error, emit_ide_hook_outcome

PR = Path(os.environ["PROJECT_DIR"])
SID = os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID")
TID = os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID")
COMMON = dict(engine="github_copilot", component="hook.copilot-error", source="hook", session_id=SID, trace_id=TID)

emit_ide_hook_outcome(PR, hook_kind="error-occurred", outcome="failure", **COMMON)
emit_framework_error(PR, error_code=os.environ["ERROR_NAME"] or "hook_error", summary=os.environ["ERROR_MESSAGE"], **COMMON)
PY
}

main || exit 0
exit 0
