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
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    source "$SCRIPT_DIR/_lib/copilot-runtime.sh"

    # Extract prompt from stdin JSON
    PROMPT=""
    if command -v jq >/dev/null 2>&1; then
        PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
    else
        PROMPT=$(copilot_framework_python_inline "$PROJECT_DIR" <<'PY'
import json
import sys

try:
    print(json.load(sys.stdin).get("prompt", ""))
except Exception:
    pass
PY
) || PROMPT=""
    fi

    # Only match /ai-* slash commands (with optional args after space)
    [[ "$PROMPT" =~ ^/ai-([a-zA-Z-]+) ]] || return 0
    RAW="${BASH_REMATCH[1]}"

    # Normalize: lowercase, ensure ai- prefix
    SKILL_NAME="ai-$(echo "$RAW" | tr '[:upper:]' '[:lower:]')"

    PROJECT_DIR="$PROJECT_DIR" SKILL_NAME="$SKILL_NAME" copilot_framework_python_inline "$PROJECT_DIR" <<'PY' >/dev/null 2>&1 || true
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import (
    emit_declared_context_loads,
    emit_ide_hook_outcome,
    emit_skill_invoked,
)
from _lib.instincts import extract_instincts, maybe_refresh_instinct_context

entry = emit_skill_invoked(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    skill_name=os.environ["SKILL_NAME"],
    component="hook.copilot-skill",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
emit_declared_context_loads(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    initiator_kind="skill",
    initiator_name=os.environ["SKILL_NAME"],
    component="hook.copilot-skill",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
    correlation_id=entry["correlationId"],
)
emit_ide_hook_outcome(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    hook_kind="user-prompt-submit",
    component="hook.copilot-skill",
    outcome="success",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
    correlation_id=entry["correlationId"],
)
if os.environ["SKILL_NAME"] == "ai-start":
    extract_instincts(Path(os.environ["PROJECT_DIR"]))
    maybe_refresh_instinct_context(Path(os.environ["PROJECT_DIR"]))
PY
}

main || exit 0
exit 0
