#!/usr/bin/env python3
"""Stop hook: durable checkpoint + Ralph Loop resume marker (spec-116 G-3).

Two responsibilities consolidated to keep ``Stop`` cheap (the IDE serialises
shutdown):

* **Checkpoint**: write ``runtime/checkpoint.json`` with the active
  spec/plan paths, recently edited files, recent failures, and the
  outcome of the most recent tool calls. ``/ai-start`` reads this so a
  new session can resume mid-task instead of starting cold.

* **Ralph Loop marker**: scan the recent tool history for "task
  incomplete" signals — failing tests, broken builds, lingering errors,
  or unmerged spec/plan work — and stamp ``runtime/ralph-resume.json``
  with the original prompt + retry count. The next ``/ai-start`` checks
  this file and offers to resume; ``ai-eng ralph status`` (CLI) surfaces
  the same.

The hook never blocks ``Stop``; failures degrade silently.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import emit_event, get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.runtime_state import (
    LOOP_WINDOW,
    checkpoint_path,
    iso_now,
    ralph_resume_path,
    read_json,
    recent_tool_history,
    redact,
    runtime_dir,
    write_json,
)


def _bounded_int_env(name: str, default: int, *, ceiling: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return min(value, ceiling)


# Bounded so a stray AIENG_RALPH_MAX_RETRIES=999999999 cannot keep the Ralph
# Loop alive across many sessions.
_RALPH_MAX_RETRIES = _bounded_int_env("AIENG_RALPH_MAX_RETRIES", 5, ceiling=50)
_FAILURE_PATTERNS = (
    "test failed",
    "tests failed",
    "FAILED",
    "Traceback",
    "build failed",
    "AssertionError",
    "TypeError",
    "ImportError",
)


def _recent_edited_files(
    project_root: Path,
    *,
    session_id: str | None,
    limit: int = 10,
) -> list[str]:
    """Pull recent file paths from `tool-history.ndjson`.

    Earlier versions filtered framework-events for ``component=='hook.auto-format'``
    reading ``detail.file_path``, but auto-format relies on the generic hook
    heartbeat and never emits a ``file_path`` field — so ``recent_edits`` was
    permanently empty. ``ToolHistoryEntry`` now persists ``filePath`` for every
    Edit/Write/MultiEdit, so this is the single source of truth.
    """
    rows = recent_tool_history(project_root, session_id=session_id, limit=200)
    paths: list[str] = []
    for row in rows:
        candidate = row.get("filePath") or row.get("file_path")
        if isinstance(candidate, str) and candidate and candidate not in paths:
            paths.append(candidate)
        if len(paths) >= limit:
            break
    return paths


def _active_work_paths(project_root: Path) -> dict[str, str | None]:
    """Resolve active spec/plan locations from the work-plane pointer."""
    pointer = read_json(project_root / ".ai-engineering" / "specs" / "active-work-plane.json")
    specs_dir_raw = (pointer or {}).get("specsDir")
    specs_dir = (
        project_root / specs_dir_raw
        if isinstance(specs_dir_raw, str) and specs_dir_raw
        else project_root / ".ai-engineering" / "specs"
    )
    spec_md = specs_dir / "spec.md"
    plan_md = specs_dir / "plan.md"
    return {
        "specsDir": str(specs_dir.relative_to(project_root)) if specs_dir.exists() else None,
        "spec": str(spec_md.relative_to(project_root)) if spec_md.exists() else None,
        "plan": str(plan_md.relative_to(project_root)) if plan_md.exists() else None,
    }


def _looks_incomplete(tool_history: list[dict]) -> tuple[bool, str | None]:
    """Heuristic Ralph signal: most-recent call failed or the latest record matches a known marker.

    Earlier versions returned True if **any** call in the window had failed. That
    over-fired for sub-agents running red-phase tests (`pytest -m red` leaves a
    `Traceback` in error_summary) — every Stop after a legitimate red phase
    bumped the Ralph counter. Restricting to the most recent record means a
    single stale failure no longer indicates active thrashing.
    """
    if not tool_history:
        return False, None
    last = tool_history[-1]
    if last.get("outcome") == "failure":
        return True, (
            f"latest tool call failed "
            f"(tool={last.get('tool')}: {last.get('errorSummary') or 'no detail'})"
        )
    summary = (last.get("errorSummary") or "").lower()
    if summary:
        for pat in _FAILURE_PATTERNS:
            if pat.lower() in summary:
                return True, f"failure marker '{pat}' in tool {last.get('tool')}"
    return False, None


def _bump_ralph_state(
    project_root: Path,
    *,
    session_id: str | None,
    reason: str,
    last_prompt: str | None,
) -> dict:
    path = ralph_resume_path(project_root)
    existing = read_json(path) or {}
    retries = int(existing.get("retries", 0)) + 1
    exhausted = retries >= _RALPH_MAX_RETRIES
    payload = {
        "schemaVersion": "1.0",
        "createdAt": existing.get("createdAt") or iso_now(),
        "updatedAt": iso_now(),
        "sessionId": session_id,
        "retries": retries,
        "maxRetries": _RALPH_MAX_RETRIES,
        "exhausted": exhausted,
        "reason": reason,
        "lastPrompt": last_prompt,
        # Stop offering resume once retry budget is exhausted; operator must
        # intervene (clear the file or unset Ralph) to re-arm. Earlier versions
        # set `active: True` unconditionally and `AIENG_RALPH_MAX_RETRIES` had
        # no effect.
        "active": not exhausted,
    }
    write_json(path, payload)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return payload


def _clear_ralph_state(project_root: Path) -> None:
    path = ralph_resume_path(project_root)
    if not path.exists():
        return
    existing = read_json(path) or {}
    if not existing.get("active"):
        return
    existing.update({"active": False, "clearedAt": iso_now()})
    write_json(path, existing)


def _emit_summary_event(
    project_root: Path,
    *,
    session_id: str | None,
    correlation_id: str,
    checkpoint_written: bool,
    ralph_active: bool,
    ralph_reason: str | None,
    ralph_retries: int,
) -> None:
    event: dict = {
        "kind": "ide_hook",
        "engine": "claude_code",
        "timestamp": iso_now(),
        "component": "hook.runtime-stop",
        "outcome": "success",
        "correlationId": correlation_id,
        "schemaVersion": "1.0",
        "project": project_root.name,
        "source": "hook",
        "detail": {
            "hook_kind": "stop",
            "checkpoint_written": checkpoint_written,
            "ralph_active": ralph_active,
            "ralph_reason": ralph_reason,
            "ralph_retries": ralph_retries,
        },
    }
    if session_id:
        event["sessionId"] = session_id
    emit_event(project_root, event)


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "Stop":
        passthrough_stdin(ctx.data)
        return

    project_root = ctx.project_root
    session_id = ctx.session_id
    runtime_dir(project_root).mkdir(parents=True, exist_ok=True)

    history = recent_tool_history(project_root, session_id=session_id, limit=LOOP_WINDOW * 4)
    edited = _recent_edited_files(project_root, session_id=session_id)
    work = _active_work_paths(project_root)

    # Snake_case keys on this checkpoint match the consumer (memory/episodic.py).
    # Earlier camelCase keys (`activeWork`, `recentEdits`, `recentToolCalls`)
    # silently produced empty episodes because the reader looked for snake_case.
    checkpoint_payload = {
        "schemaVersion": "1.0",
        "written_at": iso_now(),
        "session_id": session_id,
        "active_work": work,
        "active_specs": [s for s in (work.get("spec"),) if isinstance(s, str)],
        "recent_edits": edited,
        "recent_tool_calls": [
            {
                "tool": r.get("tool"),
                "outcome": r.get("outcome"),
                "errorSummary": r.get("errorSummary"),
                "timestamp": r.get("timestamp"),
            }
            for r in history[-10:]
        ],
    }
    cp_path = checkpoint_path(project_root)
    write_json(cp_path, checkpoint_payload)
    try:
        cp_path.chmod(0o600)
    except OSError:
        pass

    incomplete, reason = _looks_incomplete(history)
    raw_prompt = ctx.data.get("user_prompt") or ctx.data.get("prompt")
    if isinstance(raw_prompt, str):
        # Redact before truncation: the 1000-char window is enough to leak an
        # accidentally pasted env export or curl command otherwise.
        last_prompt = redact(raw_prompt)[:1000]
    else:
        last_prompt = None

    ralph_state: dict | None = None
    if incomplete and reason:
        ralph_state = _bump_ralph_state(
            project_root,
            session_id=session_id,
            reason=reason,
            last_prompt=last_prompt,
        )
    else:
        _clear_ralph_state(project_root)

    _emit_summary_event(
        project_root,
        session_id=session_id,
        correlation_id=get_correlation_id(),
        checkpoint_written=True,
        ralph_active=bool(ralph_state and ralph_state.get("active")),
        ralph_reason=reason,
        ralph_retries=int((ralph_state or {}).get("retries", 0)),
    )

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(main, component="hook.runtime-stop", hook_kind="stop", script_path=__file__)
