#!/usr/bin/env bash
# Copilot telemetry hook: emit agent_dispatched on postToolUse matching agent tools.
# Called by GitHub Copilot hooks (postToolUse event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    INPUT=$(cat)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

    TOOL_NAME=""
    if command -v jq >/dev/null 2>&1; then
        TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('toolName', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    TOOL_LOWER=$(echo "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')
    case "$TOOL_LOWER" in
        build|explorer|plan|review|verify|guard|guide|simplifier) ;;
        task) ;;
        *agent*) ;;
        *) return 0 ;;
    esac

    AGENT_TYPE=""
    if command -v jq >/dev/null 2>&1; then
        AGENT_TYPE=$(echo "$INPUT" | jq -r '.toolArgs | if type == "string" then fromjson else . end | .agent_type // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        AGENT_TYPE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    args = d.get('toolArgs', {})
    if isinstance(args, str):
        args = json.loads(args)
    print(args.get('agent_type', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    if [ -z "$AGENT_TYPE" ]; then
        AGENT_TYPE="$TOOL_NAME"
    fi
    [ -z "$AGENT_TYPE" ] && return 0

    AGENT_TYPE=$(echo "$AGENT_TYPE" | tr '[:upper:]' '[:lower:]')
    AGENT_TYPE="${AGENT_TYPE#ai-}"
    AGENT_TYPE="${AGENT_TYPE#ai:}"
    AGENT_TYPE="ai-${AGENT_TYPE}"

    if command -v python3 >/dev/null 2>&1; then
        PROJECT_DIR="$PROJECT_DIR" AGENT_TYPE="$AGENT_TYPE" python3 - <<'PY' >/dev/null 2>&1 || true
import os
from pathlib import Path

from ai_engineering.state.observability import emit_agent_dispatched, emit_ide_hook_outcome

emit_agent_dispatched(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    agent_name=os.environ["AGENT_TYPE"],
    component="hook.copilot-agent",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
emit_ide_hook_outcome(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    hook_kind="post-tool-use",
    component="hook.copilot-agent",
    outcome="success",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
PY
    fi
}

main || exit 0
exit 0
