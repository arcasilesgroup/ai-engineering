#!/usr/bin/env bash
# Copilot telemetry hook: emit agent_dispatched on postToolUse matching agent tools.
# Called by GitHub Copilot hooks (postToolUse event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    # Read JSON from stdin (postToolUse event data)
    INPUT=$(cat)

    # Resolve project root from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    source "$SCRIPT_DIR/_lib/copilot-runtime.sh"

    # Extract toolName from stdin JSON
    TOOL_NAME=""
    if command -v jq >/dev/null 2>&1; then
        TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // empty' 2>/dev/null)
    else
        TOOL_NAME=$(copilot_framework_python_inline "$PROJECT_DIR" <<'PY'
import sys
import json

try:
    print(json.load(sys.stdin).get("toolName", ""))
except Exception:
    pass
PY
) || TOOL_NAME=""
    fi

    # Detect agent dispatch: match registered agent names OR generic "task"/"agent" patterns.
    # Copilot sends the agent's registered `name` as toolName (e.g., "Build", "Explorer").
    # Claude sends "task" or tools containing "agent" in the name.
    TOOL_LOWER=$(echo "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')

    # Registered agent names from .github/agents/*.agent.md
    case "$TOOL_LOWER" in
        build|explorer|plan|review|verify|guard|guide|simplifier) ;;
        task) ;;
        *agent*) ;;
        *) return 0 ;;
    esac

    # Extract agent type: try toolArgs.agent_type first (Claude pattern),
    # then fall back to toolName itself (Copilot pattern).
    AGENT_TYPE=""
    if command -v jq >/dev/null 2>&1; then
        AGENT_TYPE=$(echo "$INPUT" | jq -r '.toolArgs | if type == "string" then fromjson else . end | .agent_type // empty' 2>/dev/null)
    else
        AGENT_TYPE=$(copilot_framework_python_inline "$PROJECT_DIR" <<'PY'
import json
import sys

try:
    payload = json.load(sys.stdin)
    args = payload.get("toolArgs", {})
    if isinstance(args, str):
        args = json.loads(args)
    print(args.get("agent_type", ""))
except Exception:
    pass
PY
) || AGENT_TYPE=""
    fi

    # Fallback: use toolName as agent type (Copilot sends agent name directly)
    if [ -z "$AGENT_TYPE" ]; then
        AGENT_TYPE="$TOOL_NAME"
    fi


    # Skip if no agent type extracted
    [ -z "$AGENT_TYPE" ] && return 0

    # Normalize: lowercase, strip existing ai-/ai: prefix, re-add ai- prefix
    AGENT_TYPE=$(echo "$AGENT_TYPE" | tr '[:upper:]' '[:lower:]')
    AGENT_TYPE="${AGENT_TYPE#ai-}"
    AGENT_TYPE="${AGENT_TYPE#ai:}"
    AGENT_TYPE="ai-${AGENT_TYPE}"

    PROJECT_DIR="$PROJECT_DIR" AGENT_TYPE="$AGENT_TYPE" copilot_framework_python_inline "$PROJECT_DIR" <<'PY' >/dev/null 2>&1 || true
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_agent_dispatched, emit_ide_hook_outcome

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
}

main || exit 0
exit 0
