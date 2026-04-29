#!/usr/bin/env bash
# Copilot telemetry hook: emit skill_invoked on userPromptSubmitted matching /ai-*.
# Called by GitHub Copilot hooks (userPromptSubmitted event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
. "$SCRIPT_DIR/_lib/copilot-common.sh"
. "$SCRIPT_DIR/_lib/copilot-runtime.sh"
COPILOT_COMPONENT="hook.copilot-skill"
export COPILOT_COMPONENT

main() {
    PROMPT="$(read_stdin_payload .prompt)"
    [[ "$PROMPT" =~ ^/ai-([a-zA-Z-]+) ]] || return 0
    SKILL_NAME="ai-$(echo "${BASH_REMATCH[1]}" | tr '[:upper:]' '[:lower:]')"

    PROJECT_DIR="$PROJECT_DIR" SKILL_NAME="$SKILL_NAME" copilot_framework_python_inline "$PROJECT_DIR" <<'PY' >/dev/null 2>&1 || true
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_declared_context_loads, emit_ide_hook_outcome, emit_skill_invoked
from _lib.instincts import extract_instincts

PR = Path(os.environ["PROJECT_DIR"])
SK = os.environ["SKILL_NAME"]
SID = os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID")
TID = os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID")
COMMON = dict(engine="github_copilot", component="hook.copilot-skill", source="hook", session_id=SID, trace_id=TID)

entry = emit_skill_invoked(PR, skill_name=SK, **COMMON)
emit_declared_context_loads(PR, initiator_kind="skill", initiator_name=SK, correlation_id=entry["correlationId"], **COMMON)
emit_ide_hook_outcome(PR, hook_kind="user-prompt-submit", outcome="success", correlation_id=entry["correlationId"], **COMMON)
if SK == "ai-start":
    extract_instincts(PR)
PY
}

main || exit 0
exit 0
