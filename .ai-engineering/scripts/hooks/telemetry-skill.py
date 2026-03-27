#!/usr/bin/env python3
"""Telemetry hook: emit skill_invoked on UserPromptSubmit matching /ai-*.

Called by Claude Code hooks (UserPromptSubmit event).
Fail-open: exit 0 always -- never blocks IDE.
Replaces former telemetry-skill.sh.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from datetime import UTC

from _lib.audit import (
    get_project_root,
    is_debug_mode,
    read_stdin,
)
from _lib.instincts import extract_instincts, maybe_refresh_instinct_context
from _lib.observability import (
    emit_declared_context_loads,
    emit_framework_error,
    emit_ide_hook_outcome,
    emit_skill_invoked,
)

_SKILL_RE = re.compile(r"/ai-([a-zA-Z-]+)")


def main() -> None:
    data = read_stdin()
    prompt = data.get("prompt", "")
    if not prompt:
        return

    match = _SKILL_RE.search(prompt)
    if not match:
        return

    raw = match.group(1)
    skill_name = f"ai-{raw.lower()}"

    project_root = get_project_root()
    entry = emit_skill_invoked(
        project_root,
        engine="claude_code",
        skill_name=skill_name,
        component="hook.telemetry-skill",
        source="hook",
        session_id=os.environ.get("CLAUDE_SESSION_ID"),
        trace_id=os.environ.get("CLAUDE_TRACE_ID"),
    )
    emit_declared_context_loads(
        project_root,
        engine="claude_code",
        initiator_kind="skill",
        initiator_name=skill_name,
        component="hook.telemetry-skill",
        source="hook",
        session_id=os.environ.get("CLAUDE_SESSION_ID"),
        trace_id=os.environ.get("CLAUDE_TRACE_ID"),
        correlation_id=entry["correlationId"],
    )
    emit_ide_hook_outcome(
        project_root,
        engine="claude_code",
        hook_kind="user-prompt-submit",
        component="hook.telemetry-skill",
        outcome="success",
        source="hook",
        session_id=os.environ.get("CLAUDE_SESSION_ID"),
        trace_id=os.environ.get("CLAUDE_TRACE_ID"),
        correlation_id=entry["correlationId"],
    )
    if skill_name == "ai-onboard":
        extract_instincts(project_root)
        maybe_refresh_instinct_context(project_root)

    if is_debug_mode():
        from datetime import datetime

        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] skill_invoked: {skill_name}\n")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            project_root = get_project_root()
            emit_ide_hook_outcome(
                project_root,
                engine="claude_code",
                hook_kind="user-prompt-submit",
                component="hook.telemetry-skill",
                outcome="failure",
                source="hook",
                session_id=os.environ.get("CLAUDE_SESSION_ID"),
                trace_id=os.environ.get("CLAUDE_TRACE_ID"),
            )
            emit_framework_error(
                project_root,
                engine="claude_code",
                component="hook.telemetry-skill",
                error_code="hook_execution_failed",
                summary=str(exc),
                source="hook",
                session_id=os.environ.get("CLAUDE_SESSION_ID"),
                trace_id=os.environ.get("CLAUDE_TRACE_ID"),
            )
        except Exception:
            pass
    sys.exit(0)
