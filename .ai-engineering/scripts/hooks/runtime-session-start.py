#!/usr/bin/env python3
"""SessionStart enrichment hook (spec-120 follow-up).

Adds three lightweight responsibilities on top of
``memory-session-start.py`` (which stays the canonical SessionStart
runner — this hook runs alongside it, not as a replacement):

1. Stamp a ``framework_operation`` event with
   ``operation=session_started`` so the audit chain has an explicit
   anchor at the start of every IDE session.
2. Initialise ``RUNTIME_DIR(project_root) / "trace-context.json"`` (canonical
   ``.ai-engineering/runtime/trace-context.json``) with a fresh ``traceId``
   (via the spec-120 helper ``_lib/trace_context.write_trace_context``) so
   subsequent emit calls inside the session inherit a stable context.
3. Best-effort load + log how many KO entries (corrections, recoveries,
   workflows) currently live in the instincts cache. Informational —
   logged into ``metadata.instincts_count`` so a downstream session
   trace can show "session started with N learned instincts".

Stdlib-only contract. Fail-open: any error degrades silently so a
broken trace-context or instincts file never blocks the IDE from
booting a new session.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context

_COMPONENT = "hook.runtime-session-start"

# spec-186 D-186-05: one-shot Client-Value Lens contract, injected at session
# boot so the sponsor-framing discipline is established before the first turn.
# The ``reference/value-lens.md`` citation is the load-bearing adoption marker.
_VALUE_LENS_CONTRACT_TEMPLATE = (
    "[client-value-lens] Active. Reports + questions use the value block "
    "(reference/value-lens.md); default level {level}. Carve-outs "
    "(code/commits/security/verdicts) stay precise."
)


def _value_lens_contract() -> str:
    """Return the Client-Value Lens contract with the active level interpolated.

    The resolver is imported lazily and guarded so a bare-``python3`` host
    without the ``ai_engineering`` package degrades to ``full`` rather than
    breaking session start.
    """
    try:
        from ai_engineering.value_lens import resolve_level

        level = resolve_level()
    except Exception:
        level = "full"
    return _VALUE_LENS_CONTRACT_TEMPLATE.format(level=level)


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


def _safe_write_session_pointer(project_root: Path, session_id: str | None) -> None:
    """Persist a durable ``session-pointer.json`` for hot-path hooks (D-190-01).

    ``CLAUDE_SESSION_ID`` is usually unset on the hot path, so downstream
    hooks that call ``get_session_id`` recover only ~1.3% coverage from
    env. Stamping ``.ai-engineering/state/runtime/session-pointer.json`` at
    SessionStart gives them a stable fallback pointer for the whole session.

    Best-effort only: on a worktree shared by concurrent sessions the pointer
    names whichever session started last, so it is a shared-worktree FALLBACK
    (FINDING 3) — a hook's own stdin/ctx/env session id always wins over it.
    The record is stamped with ``{session_id, pid, ts}`` so an operator can
    tell which process last claimed the pointer.

    Fail-open: any error (unwritable runtime dir, encoding issue) degrades
    silently so a broken pointer never blocks session boot. A missing /
    empty ``session_id`` writes nothing — a null pointer is worse than none.
    """
    if not isinstance(session_id, str) or not session_id:
        return
    try:
        path = project_root / ".ai-engineering" / "state" / "runtime" / "session-pointer.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "pid": os.getpid(),
            "ts": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        # Unique temp per writer (FINDING 7): a fixed ``.tmp`` name races
        # concurrent writers and can corrupt/lose the pointer. mkstemp mints a
        # per-writer temp in the target dir; os.replace makes the swap atomic.
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(payload))
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                with contextlib.suppress(OSError):
                    tmp.unlink()
    except Exception:
        # Fail-open: never block the IDE booting a session.
        return


def _storm_banner(project_root: Path) -> str | None:
    """Return a bounded one-line error-storm warning, or None when clean.

    spec-190 D-190-02: reads the coalescer sidecar and, if any fingerprint has
    an active storm in the current window, names the loudest one (count +
    component + error_code). Fail-open — any error returns None so a broken
    sidecar never blocks session boot.
    """
    try:
        from _lib.runtime_state import active_error_storms

        storms = active_error_storms(project_root)
    except Exception:
        return None
    if not storms:
        return None
    top = max(storms, key=lambda s: s.get("count", 0))
    line = (
        f"[error-storm] {top.get('count')} repeated errors "
        f"(component={top.get('component')} error_code={top.get('error_code')}) "
        "in the last window — run 'ai-eng doctor'"
    )
    return line[:240]


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

    _safe_write_session_pointer(project_root, session_id)
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

    # spec-186: inject the one-shot Client-Value Lens contract as plain-text
    # additionalContext. Guarded + fail-open — a resolver hiccup must never
    # block session start.
    with contextlib.suppress(Exception):
        sys.stdout.write(_value_lens_contract() + "\n")

    # spec-190 D-190-02: surface an active error/integrity storm so the
    # operator sees it at session boot without running ``ai-eng doctor``.
    # Suppressed (nothing printed) when clean. Fail-open: never raise.
    with contextlib.suppress(Exception):
        banner = _storm_banner(project_root)
        if banner:
            sys.stdout.write(banner + "\n")

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="session-start",
        script_path=__file__,
    )
