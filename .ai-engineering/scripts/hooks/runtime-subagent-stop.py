#!/usr/bin/env python3
"""SubagentStop hook: per-subagent observability.

Claude Code emits ``SubagentStop`` after each Agent-tool dispatch
finishes. The new SQLite audit index (spec-120 §4.3) attributes work
per-subagent, so we need a hook that captures ``subagent_type`` (and
``duration_ms`` when present) into a ``framework_operation`` event.

Defensive by contract: missing fields fall back to safe defaults
(``subagent_type='unknown'``, ``duration_ms=None``); any unexpected
exception is swallowed so a misshaped payload never blocks the IDE
shutting down a subagent. Mirrors the safety posture of
``runtime-stop.py`` and ``memory-session-start.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context

_COMPONENT = "hook.runtime-subagent-stop"


def _coerce_int(value: object) -> int | None:
    """Return ``value`` as ``int`` when it looks numeric, else ``None``.

    Defensive: an IDE could ship the duration as ``"123"`` or ``123.4``
    or a stray dict — only the unambiguous numeric forms count.
    """
    if isinstance(value, bool):
        # bool is an int subclass; reject to avoid silent True -> 1.
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(value)
        except (OverflowError, ValueError):
            return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None


def _coerce_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def main() -> None:
    ctx = get_hook_context()
    # Be permissive: Claude Code sends ``SubagentStop``; other engines
    # may not surface this primitive at all. Pass through silently if
    # the event name does not match.
    if ctx.event_name != "SubagentStop":
        passthrough_stdin(ctx.data)
        return

    subagent_type = _coerce_str(ctx.data.get("subagent_type")) or "unknown"
    duration_ms = _coerce_int(ctx.data.get("duration_ms"))
    subagent_run_id = _coerce_str(ctx.data.get("subagent_run_id"))
    session_id = ctx.session_id

    metadata: dict[str, object] = {
        "subagent_type": subagent_type,
        "session_id": session_id,
    }
    if duration_ms is not None:
        metadata["duration_ms"] = duration_ms
    if subagent_run_id:
        metadata["subagent_run_id"] = subagent_run_id

    # Best-effort: import + emit. Any failure (missing optional dep,
    # disk error, schema mismatch) degrades silently so the IDE never
    # blocks on a SubagentStop.
    try:
        from _lib.observability import emit_framework_operation

        emit_framework_operation(
            ctx.project_root,
            operation="subagent_stop",
            component=_COMPONENT,
            source="hook",
            correlation_id=get_correlation_id(),
            metadata=metadata,
        )
    except Exception:
        # Swallow: the hook contract is fail-open.
        pass

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="subagent-stop",
        script_path=__file__,
    )
