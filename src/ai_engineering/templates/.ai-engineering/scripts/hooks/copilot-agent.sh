#!/usr/bin/env bash
# Copilot telemetry hook: emit agent_dispatched on postToolUse matching agent tools.
# Called by GitHub Copilot hooks (postToolUse event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    . "$SCRIPT_DIR/_lib/copilot-common.sh"
    . "$SCRIPT_DIR/_lib/copilot-runtime.sh"
    COPILOT_COMPONENT="hook.copilot-agent"

    read_stdin_payload >/dev/null
    TOOL_NAME="$(read_stdin_payload .toolName)"
    TOOL_LOWER=$(printf '%s' "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')
    case "$TOOL_LOWER" in
        build|explorer|plan|review|verify|guard|guide|simplifier|task) ;;
        *agent*) ;;
        *) return 0 ;;
    esac

    AGENT_TYPE=""
    if command -v jq >/dev/null 2>&1 && [ -n "${PAYLOAD:-}" ]; then
        AGENT_TYPE=$(printf '%s' "$PAYLOAD" | jq -r '.toolArgs | if type == "string" then fromjson else . end | .agent_type // empty' 2>/dev/null) || AGENT_TYPE=""
    fi
    [ -z "$AGENT_TYPE" ] && AGENT_TYPE="$TOOL_NAME"
    [ -z "$AGENT_TYPE" ] && return 0

    AGENT_TYPE=$(printf '%s' "$AGENT_TYPE" | tr '[:upper:]' '[:lower:]')
    AGENT_TYPE="${AGENT_TYPE#ai-}"
    AGENT_TYPE="${AGENT_TYPE#ai:}"
    AGENT_TYPE="ai-${AGENT_TYPE}"

    PROJECT_DIR="$PROJECT_DIR" AGENT_TYPE="$AGENT_TYPE" copilot_framework_python_inline "$PROJECT_DIR" <<'PY' >/dev/null 2>&1 || true
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_agent_dispatched, emit_ide_hook_outcome

PR = Path(os.environ["PROJECT_DIR"])
SID = os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID")
TID = os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID")
COMMON = dict(engine="github_copilot", component="hook.copilot-agent", source="hook", session_id=SID, trace_id=TID)

emit_agent_dispatched(PR, agent_name=os.environ["AGENT_TYPE"], **COMMON)
emit_ide_hook_outcome(PR, hook_kind="post-tool-use", outcome="success", **COMMON)
PY
}

main || exit 0
exit 0
