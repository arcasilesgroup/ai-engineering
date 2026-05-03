#!/usr/bin/env python3
"""PreCompact + PostCompact hook (spec-116 G-4).

Anthropic's harness research warned: "never rely on compaction for
critical rules — move them to CLAUDE.md where they live in the system
prompt and survive any compression". This hook implements the runtime
side of that contract:

* On ``PreCompact`` it snapshots the high-value runtime state that
  context compression would otherwise erase: active spec/plan, recent
  edits, last tool calls, current Ralph status.

* On ``PostCompact`` it emits telemetry confirming compaction landed
  and references the snapshot path so operators can diff what was kept.

Same script handles both events; dispatch on ``hook_event_name``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import emit_event, get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.runtime_state import (
    LOOP_WINDOW,
    iso_now,
    precompact_snapshot_path,
    ralph_resume_path,
    read_json,
    recent_tool_history,
    runtime_dir,
    write_json,
)


def _build_snapshot(project_root: Path, session_id: str | None) -> dict:
    history = recent_tool_history(project_root, session_id=session_id, limit=LOOP_WINDOW * 2)
    pointer = read_json(project_root / ".ai-engineering" / "specs" / "active-work-plane.json")
    ralph = read_json(ralph_resume_path(project_root))
    return {
        "schemaVersion": "1.0",
        "capturedAt": iso_now(),
        "sessionId": session_id,
        "activeWorkPointer": pointer,
        "ralph": ralph,
        "recentToolCalls": history,
    }


def _emit(
    project_root: Path,
    *,
    session_id: str | None,
    correlation_id: str,
    event_name: str,
    detail: dict,
) -> None:
    payload: dict = {
        "kind": "ide_hook",
        "engine": "claude_code",
        "timestamp": iso_now(),
        "component": "hook.runtime-compact",
        "outcome": "success",
        "correlationId": correlation_id,
        "schemaVersion": "1.0",
        "project": project_root.name,
        "source": "hook",
        "detail": {
            "hook_kind": "pre-compact" if event_name == "PreCompact" else "post-compact",
            "compact_event": event_name,
            **detail,
        },
    }
    if session_id:
        payload["sessionId"] = session_id
    emit_event(project_root, payload)


def main() -> None:
    ctx = get_hook_context()
    project_root = ctx.project_root
    runtime_dir(project_root).mkdir(parents=True, exist_ok=True)
    correlation_id = get_correlation_id()

    if ctx.event_name == "PreCompact":
        snapshot = _build_snapshot(project_root, ctx.session_id)
        path = precompact_snapshot_path(project_root)
        write_json(path, snapshot)
        _emit(
            project_root,
            session_id=ctx.session_id,
            correlation_id=correlation_id,
            event_name="PreCompact",
            detail={
                "snapshot_path": str(path.relative_to(project_root)),
                "history_size": len(snapshot["recentToolCalls"]),
            },
        )
    elif ctx.event_name in ("PostCompact",):
        snapshot = read_json(precompact_snapshot_path(project_root)) or {}
        _emit(
            project_root,
            session_id=ctx.session_id,
            correlation_id=correlation_id,
            event_name="PostCompact",
            detail={
                "snapshot_present": bool(snapshot),
                "snapshot_capturedAt": snapshot.get("capturedAt"),
            },
        )

    passthrough_stdin(ctx.data)


def _entry() -> None:
    """Resolve hook_kind from the actual event so PostCompact telemetry is not
    mislabelled as ``pre-compact``. Earlier versions pinned ``hook_kind`` at
    the wrapper, so every PostCompact event was telemetered with the wrong
    kind and audit queries filtering on ``hook_kind=post-compact`` returned
    nothing."""
    try:
        ctx = get_hook_context()
        kind = "pre-compact" if ctx.event_name == "PreCompact" else "post-compact"
    except Exception:
        kind = "pre-compact"
    run_hook_safe(
        main, component="hook.runtime-compact", hook_kind=kind, script_path=Path(__file__)
    )


if __name__ == "__main__":
    _entry()
