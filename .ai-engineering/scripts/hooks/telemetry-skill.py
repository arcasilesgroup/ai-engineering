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
    append_framework_event,
    build_framework_event,
    emit_declared_context_loads,
    emit_ide_hook_outcome,
    emit_skill_invoked,
)

# Spec-112 G-1: regex extracts skill name from `^/ai-([a-zA-Z0-9_-]+)` against
# `payload.prompt`. The character class is intentionally narrowed at the
# emission boundary in observability._normalize_skill_name; the regex itself
# tolerates digits/underscores so unusual user prompts still surface as
# `skill_invoked_malformed` with a clear `detail.reason` rather than being
# dropped silently.
_SKILL_RE = re.compile(r"^\s*/ai-([a-zA-Z0-9_-]+)")


def _emit_malformed(ctx, *, reason: str, trace_id: str | None) -> None:
    """Surface edge cases as `skill_invoked_malformed` (spec-112 G-1)."""
    entry = build_framework_event(
        ctx.project_root,
        engine=ctx.engine,
        kind="skill_invoked_malformed",
        component="hook.telemetry-skill",
        source="hook",
        session_id=ctx.session_id,
        trace_id=trace_id,
        force_outcome="warn",
        detail={"skill": None, "reason": reason},
    )
    append_framework_event(ctx.project_root, entry)


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
    run_hook_safe(main, component="hook.telemetry-skill", hook_kind="user-prompt-submit")
