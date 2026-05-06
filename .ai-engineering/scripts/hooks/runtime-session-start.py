#!/usr/bin/env python3
"""SessionStart enrichment hook (spec-120 follow-up).

Adds three lightweight responsibilities on top of
``memory-session-start.py`` (which stays the canonical SessionStart
runner — this hook runs alongside it, not as a replacement):

1. Stamp a ``framework_operation`` event with
   ``operation=session_started`` so the audit chain has an explicit
   anchor at the start of every IDE session.
2. Initialise ``.ai-engineering/state/runtime/trace-context.json`` with
   a fresh ``traceId`` (via the spec-120 helper
   ``_lib/trace_context.write_trace_context``) so subsequent emit
   calls inside the session inherit a stable context.
3. Best-effort load + log how many KO entries (corrections, recoveries,
   workflows) currently live in the instincts cache. Informational —
   logged into ``metadata.instincts_count`` so a downstream session
   trace can show "session started with N learned instincts".

Stdlib-only contract. Fail-open: any error degrades silently so a
broken trace-context or instincts file never blocks the IDE from
booting a new session.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context

_COMPONENT = "hook.runtime-session-start"


def _safe_count_instincts(project_root: Path) -> int | None:
    """Return total KO count (corrections + recoveries + workflows) or None."""
    try:
        from _lib.instincts import _load_instincts_document

        document = _load_instincts_document(project_root)
    except Exception:
        return None
    if not isinstance(document, dict):
        return None
    total = 0
    for key in ("corrections", "recoveries", "workflows"):
        value = document.get(key)
        if isinstance(value, list):
            total += len(value)
    return total


def _safe_init_trace_context(project_root: Path) -> str | None:
    """Best-effort fresh-trace stamping. Returns the new traceId or None."""
    try:
        from _lib.trace_context import new_trace_id, write_trace_context

        trace_id = new_trace_id()
        write_trace_context(
            project_root,
            {
                "traceId": trace_id,
                "span_stack": [],
            },
        )
    except Exception:
        return None
    else:
        return trace_id


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "SessionStart":
        passthrough_stdin(ctx.data)
        return

    project_root = ctx.project_root
    session_id = ctx.session_id
    correlation_id = get_correlation_id()

    trace_id = _safe_init_trace_context(project_root)
    instincts_count = _safe_count_instincts(project_root)

    metadata: dict[str, object] = {
        "engine": ctx.engine,
        "session_id": session_id,
    }
    if trace_id is not None:
        metadata["trace_id_initialized"] = trace_id
    if instincts_count is not None:
        metadata["instincts_count"] = instincts_count

    try:
        from _lib.observability import emit_framework_operation

        emit_framework_operation(
            project_root,
            operation="session_started",
            component=_COMPONENT,
            source="hook",
            correlation_id=correlation_id,
            metadata=metadata,
        )
    except Exception:
        # Fail-open: never block the IDE booting a session.
        pass

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="session-start",
        script_path=__file__,
    )
