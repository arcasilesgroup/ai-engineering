#!/usr/bin/env python3
"""Telemetry hook: emit skill_invoked on UserPromptSubmit matching /ai-*.

Called by IDE hooks (UserPromptSubmit event).
Fail-open: exit 0 always -- never blocks IDE.
Replaces former telemetry-skill.sh.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.instincts import extract_instincts
from _lib.observability import (
    emit_declared_context_loads,
    emit_ide_hook_outcome,
    emit_skill_invoked,
)

_SKILL_RE = re.compile(r"^\s*/ai-([a-zA-Z0-9_-]+)")


def _emit_malformed(ctx, *, reason: str, trace_id: str | None) -> None:
    """Surface unmatched prompts through the canonical ide_hook contract."""
    emit_ide_hook_outcome(
        ctx.project_root,
        engine=ctx.engine,
        hook_kind="user-prompt-submit",
        component="hook.telemetry-skill",
        outcome="warn",
        source="hook",
        session_id=ctx.session_id,
        trace_id=trace_id,
        metadata={"skill": None, "reason": reason},
    )


def main() -> None:
    ctx = get_hook_context()
    prompt = ctx.data.get("prompt", "")
    trace_id = os.environ.get("CLAUDE_TRACE_ID")
    if not prompt:
        _emit_malformed(ctx, reason="empty_prompt", trace_id=trace_id)
        return

    match = _SKILL_RE.search(prompt)
    if not match:
        _emit_malformed(ctx, reason="no_ai_prefix", trace_id=trace_id)
        return

    skill_name = f"ai-{match.group(1).lower()}"
    entry = emit_skill_invoked(
        ctx.project_root,
        engine=ctx.engine,
        skill_name=skill_name,
        component="hook.telemetry-skill",
        source="hook",
        session_id=ctx.session_id,
        trace_id=trace_id,
    )
    emit_declared_context_loads(
        ctx.project_root,
        engine=ctx.engine,
        initiator_kind="skill",
        initiator_name=skill_name,
        component="hook.telemetry-skill",
        source="hook",
        session_id=ctx.session_id,
        trace_id=trace_id,
        correlation_id=entry["correlationId"],
    )
    emit_ide_hook_outcome(
        ctx.project_root,
        engine=ctx.engine,
        hook_kind="user-prompt-submit",
        component="hook.telemetry-skill",
        outcome="success",
        source="hook",
        session_id=ctx.session_id,
        trace_id=trace_id,
        correlation_id=entry["correlationId"],
    )
    if skill_name == "ai-start":
        extract_instincts(ctx.project_root)


if __name__ == "__main__":
    run_hook_safe(
        main, component="hook.telemetry-skill", hook_kind="user-prompt-submit", script_path=__file__
    )
