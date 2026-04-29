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

from datetime import UTC

from _lib.hook_context import get_hook_context
from _lib.instincts import extract_instincts
from _lib.observability import (
    append_framework_event,
    build_framework_event,
    emit_declared_context_loads,
    emit_framework_error,
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
    """Spec-112 G-1: surface edge cases as `skill_invoked_malformed`.

    Empty prompt or prompt without `/ai-` prefix used to be dropped
    silently. We now emit a structured event so audits can quantify the
    rate of malformed invocations and act on it.
    """
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

    raw = match.group(1)
    skill_name = f"ai-{raw.lower()}"

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

    from _lib.audit import is_debug_mode

    if is_debug_mode():
        from datetime import datetime

        debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
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
            from _lib.audit import get_project_root

            project_root = get_project_root()
            engine = os.environ.get("AIENG_HOOK_ENGINE", "claude_code")
            session_id = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("GEMINI_SESSION_ID")
            trace_id = os.environ.get("CLAUDE_TRACE_ID")
            emit_ide_hook_outcome(
                project_root,
                engine=engine,
                hook_kind="user-prompt-submit",
                component="hook.telemetry-skill",
                outcome="failure",
                source="hook",
                session_id=session_id,
                trace_id=trace_id,
            )
            emit_framework_error(
                project_root,
                engine=engine,
                component="hook.telemetry-skill",
                error_code="hook_execution_failed",
                summary=str(exc),
                source="hook",
                session_id=session_id,
                trace_id=trace_id,
            )
        except Exception:
            pass
    sys.exit(0)
