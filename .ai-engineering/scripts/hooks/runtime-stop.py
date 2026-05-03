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
    read_ndjson_tail,
    recent_tool_history,
    runtime_dir,
    write_json,
)

_RALPH_MAX_RETRIES = int(os.environ.get("AIENG_RALPH_MAX_RETRIES", "5") or 5)
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


def _recent_edited_files(project_root: Path, limit: int = 10) -> list[str]:
    """Pull recent file paths from framework-events ``Edit|Write`` hooks."""
    events_path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    rows = read_ndjson_tail(events_path, 200)
    paths: list[str] = []
    for row in rows:
        component = row.get("component", "")
        if component != "hook.auto-format":
            continue
        detail = row.get("detail", {}) or {}
        candidate = detail.get("file_path") or detail.get("path")
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
    """Heuristic Ralph signal: recent failures or known failure markers."""
    if not tool_history:
        return False, None
    failures = [r for r in tool_history if r.get("outcome") == "failure"]
    if failures:
        last = failures[-1]
        return True, (
            f"{len(failures)} of last {len(tool_history)} tool calls failed "
            f"(last={last.get('tool')}: {last.get('errorSummary') or 'no detail'})"
        )
    for record in tool_history:
        summary = (record.get("errorSummary") or "").lower()
        if not summary:
            continue
        for pat in _FAILURE_PATTERNS:
            if pat.lower() in summary:
                return True, f"failure marker '{pat}' in tool {record.get('tool')}"
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
    payload = {
        "schemaVersion": "1.0",
        "createdAt": existing.get("createdAt") or iso_now(),
        "updatedAt": iso_now(),
        "sessionId": session_id,
        "retries": retries,
        "maxRetries": _RALPH_MAX_RETRIES,
        "exhausted": retries >= _RALPH_MAX_RETRIES,
        "reason": reason,
        "lastPrompt": last_prompt,
        "active": True,
    }
    write_json(path, payload)
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
    edited = _recent_edited_files(project_root)
    work = _active_work_paths(project_root)

    checkpoint_payload = {
        "schemaVersion": "1.0",
        "writtenAt": iso_now(),
        "sessionId": session_id,
        "activeWork": work,
        "recentEdits": edited,
        "recentToolCalls": [
            {
                "tool": r.get("tool"),
                "outcome": r.get("outcome"),
                "errorSummary": r.get("errorSummary"),
                "timestamp": r.get("timestamp"),
            }
            for r in history[-10:]
        ],
    }
    write_json(checkpoint_path(project_root), checkpoint_payload)

    incomplete, reason = _looks_incomplete(history)
    last_prompt = ctx.data.get("user_prompt") or ctx.data.get("prompt")
    if isinstance(last_prompt, str):
        last_prompt = last_prompt[:1000]
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
    run_hook_safe(main, component="hook.runtime-stop", hook_kind="stop")
