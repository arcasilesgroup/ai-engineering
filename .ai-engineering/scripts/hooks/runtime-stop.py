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

import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.convergence import ConvergenceResult, check_convergence
from _lib.hook_common import emit_event, get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.observability import emit_framework_error, emit_framework_operation
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
from _lib.transcript_usage import aggregate_session_usage, find_active_transcript

# Spec-120 §4.3: SQLite projection of framework-events.ndjson. Path is
# inlined here (mirrors `ai_engineering.state.audit_index.INDEX_REL`) so
# the hook stays stdlib-only and never imports from the pkg.
_AUDIT_INDEX_REL = Path(".ai-engineering") / "state" / "audit-index.sqlite"
_HOOK_COMPONENT = "hook.runtime-stop"


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

# Escape hatch for the convergence-driven reinjection block. When set the
# Stop hook still writes the checkpoint and the legacy heuristic Ralph
# state, but never invokes ``check_convergence`` and never writes a
# ``decision: block`` JSON to stdout.
_RALPH_DISABLED = (os.environ.get("AIENG_RALPH_DISABLED") or "").strip() == "1"
# Reinjection is enabled by default (harness gap closure 2026-05-04). The
# convergence sweep is fast (~5s ruff + pytest --collect-only) and fail-open
# on missing tools, so the previous opt-in default left ~200 lines of dead
# code in production. Repos with pre-existing lint or test debt opt out
# via ``AIENG_RALPH_BLOCK=0`` (or the broader ``AIENG_RALPH_DISABLED=1``
# escape that also short-circuits convergence entirely). Telemetry
# (ralph_converged / ralph_reinject) still emits in both modes.
_RALPH_BLOCK_ENABLED = (os.environ.get("AIENG_RALPH_BLOCK", "1") or "").strip() != "0"
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


def _ralph_retry_count(project_root: Path) -> int:
    """Read the current Ralph retry count from ralph-resume.json."""
    existing = read_json(ralph_resume_path(project_root)) or {}
    try:
        return int(existing.get("retries", 0))
    except (TypeError, ValueError):
        return 0


def _ralph_increment_retry(
    project_root: Path,
    *,
    session_id: str | None,
    failures: list[str],
    last_prompt: str | None,
) -> int:
    """Bump the Ralph retry counter using the convergence-failure summary.

    Distinct from ``_bump_ralph_state`` (which keys on the legacy
    heuristic in ``_looks_incomplete``) — this path is reached only when
    :func:`check_convergence` reports unmet criteria, so the persisted
    ``reason`` records the actual failing checks rather than a tool-history
    grep. Returns the new retry count.
    """
    path = ralph_resume_path(project_root)
    existing = read_json(path) or {}
    retries = int(existing.get("retries", 0)) + 1
    exhausted = retries >= _RALPH_MAX_RETRIES
    reason = "convergence_failed: " + "; ".join(failures[:3]) if failures else "convergence_failed"
    payload = {
        "schemaVersion": "1.0",
        "createdAt": existing.get("createdAt") or iso_now(),
        "updatedAt": iso_now(),
        "sessionId": session_id,
        "retries": retries,
        "maxRetries": _RALPH_MAX_RETRIES,
        "exhausted": exhausted,
        "reason": reason,
        "failures": failures[:5],
        "lastPrompt": last_prompt,
        "active": not exhausted,
        "source": "convergence",
    }
    write_json(path, payload)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return retries


def _delete_ralph_state(project_root: Path) -> None:
    """Remove ralph-resume.json entirely.

    Used on convergence success (work done) and on max-retries-exceeded
    (give up). Distinct from :func:`_clear_ralph_state`, which keeps the
    file as a tombstone with ``active: false`` for the legacy heuristic
    path so ``ai-eng ralph status`` can still see the prior history.
    """
    path = ralph_resume_path(project_root)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _emit_reinjection(
    *,
    retries: int,
    max_retries: int,
    failures: list[str],
) -> None:
    """Write a ``decision: block`` JSON to stdout (Claude Code Stop hook contract).

    Claude Code interprets the JSON object as a directive: ``decision:
    block`` keeps the agent loop alive and ``additionalContext`` is
    reinjected as the next user-turn context. The hook MUST flush
    before exit because ``run_hook_safe`` calls ``sys.exit(0)``.
    """
    body_lines = [
        f"Ralph Loop iteration {retries}/{max_retries} — convergence not reached.",
        "Failures:",
    ]
    for failure in failures[:5]:
        body_lines.append(f" - {failure}")
    body_lines.append("Continue work until tests pass and lint is clean.")
    payload = {
        "decision": "block",
        "additionalContext": "\n".join(body_lines),
    }
    sys.stdout.write(json.dumps(payload, separators=(",", ":")))
    sys.stdout.flush()


def _ralph_convergence_loop(
    project_root: Path,
    *,
    session_id: str | None,
    correlation_id: str,
    last_prompt: str | None,
) -> bool:
    """Run convergence + Ralph retry/reinjection orchestration.

    Returns ``True`` when the hook wrote the ``decision: block`` JSON to
    stdout (caller MUST NOT call ``passthrough_stdin`` afterwards).
    Returns ``False`` for every other terminal state (converged, max
    retries exceeded, fail-open) so the caller continues with the
    normal stdout passthrough.
    """
    if _RALPH_DISABLED:
        return False

    try:
        result: ConvergenceResult = check_convergence(project_root, fast=True)
    except Exception as exc:
        # Belt-and-braces: convergence helpers already swallow per-tool
        # failures, but a stray import error or path bug must never trap
        # the user in a fake-failure loop.
        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component=_HOOK_COMPONENT,
            error_code="ralph_convergence_error",
            source="hook",
            session_id=session_id,
            correlation_id=correlation_id,
            metadata={"reason": f"{type(exc).__name__}: {str(exc)[:200]}"},
        )
        return False

    # Fail-open: empty failures means "no checks ran" OR "everything
    # passed". Either way we treat it as converged so a sandbox without
    # python/ruff doesn't loop forever on synthetic failures.
    if result.converged:
        _delete_ralph_state(project_root)
        emit_framework_operation(
            project_root,
            operation="ralph_converged",
            component=_HOOK_COMPONENT,
            source="hook",
            correlation_id=correlation_id,
            metadata={
                "duration_ms": result.duration_ms,
                "session_id": session_id,
            },
        )
        return False

    current_retries = _ralph_retry_count(project_root)
    if current_retries >= _RALPH_MAX_RETRIES:
        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component=_HOOK_COMPONENT,
            error_code="ralph_max_retries_exceeded",
            source="hook",
            session_id=session_id,
            correlation_id=correlation_id,
            metadata={
                "retries": current_retries,
                "max_retries": _RALPH_MAX_RETRIES,
                "failures": result.failures[:5],
            },
        )
        _delete_ralph_state(project_root)
        return False

    new_retry_count = _ralph_increment_retry(
        project_root,
        session_id=session_id,
        failures=result.failures,
        last_prompt=last_prompt,
    )
    emit_framework_operation(
        project_root,
        operation="ralph_reinject",
        component=_HOOK_COMPONENT,
        source="hook",
        correlation_id=correlation_id,
        metadata={
            "retries": new_retry_count,
            "max_retries": _RALPH_MAX_RETRIES,
            "failures": result.failures[:5],
            "duration_ms": result.duration_ms,
        },
    )
    if not _RALPH_BLOCK_ENABLED:
        # Default observe-only path: telemetry already emitted above; do
        # not write decision:block to stdout. Caller continues with the
        # normal stdout passthrough.
        return False
    _emit_reinjection(
        retries=new_retry_count,
        max_retries=_RALPH_MAX_RETRIES,
        failures=result.failures,
    )
    return True


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


def _emit_session_token_rollup(
    project_root: Path,
    *,
    session_id: str | None,
    correlation_id: str,
) -> None:
    """Spec-120 T-E1: stamp a session-end token rollup from the SQLite index.

    Best-effort: SQLite missing, locked, or any exception → emit a
    ``framework_error`` (``error_code = session_rollup_skipped``) and
    continue. ``session_id is None`` → silent skip (no error event;
    nothing meaningful to roll up).
    """
    if not session_id:
        return

    index_path = project_root / _AUDIT_INDEX_REL
    if not index_path.exists():
        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component=_HOOK_COMPONENT,
            error_code="session_rollup_skipped",
            source="hook",
            session_id=session_id,
            correlation_id=correlation_id,
            metadata={"reason": "audit_index_missing"},
        )
        return

    try:
        # Read-only URI: the OS rejects writes even if the view query
        # is somehow rewritten downstream.
        uri = f"file:{index_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            row = conn.execute(
                "SELECT session_id, started_at, ended_at, events, "
                "input_tokens, output_tokens, total_tokens, cost_usd "
                "FROM session_token_rollup WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component=_HOOK_COMPONENT,
            error_code="session_rollup_skipped",
            source="hook",
            session_id=session_id,
            correlation_id=correlation_id,
            metadata={"reason": f"sqlite_error: {type(exc).__name__}"},
        )
        return
    except Exception as exc:
        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component=_HOOK_COMPONENT,
            error_code="session_rollup_skipped",
            source="hook",
            session_id=session_id,
            correlation_id=correlation_id,
            metadata={"reason": f"unexpected_error: {type(exc).__name__}"},
        )
        return

    # Transcript usage is the source of truth for token counts: the SQLite
    # index aggregates `usage` blocks emitted by the hook stream, but no hook
    # emits per-call usage today (spec-120 T-E2 was a NO-OP for that exact
    # reason). Read directly from the Claude Code transcript and merge.
    transcript_payload = _safe_transcript_aggregate(project_root, session_id=session_id)

    if row is None and transcript_payload is None:
        # Neither source has anything to roll up. Stay silent rather than
        # emitting a zeroed event.
        return

    if row is not None:
        metadata = {
            "session_id": row[0],
            "started_at": row[1],
            "ended_at": row[2],
            "events": row[3],
            "input_tokens": row[4],
            "output_tokens": row[5],
            "total_tokens": row[6],
            "cost_usd": row[7],
        }
        usage_source = "index"
    else:
        # Synthesise the rollup from the transcript only.
        metadata = {
            "session_id": session_id,
            "started_at": None,
            "ended_at": None,
            "events": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": None,
        }
        usage_source = "transcript"

    if transcript_payload is not None:
        # Merge: index numbers are usually zero today, so transcript wins on
        # token counts. If the index ever starts carrying real numbers we
        # take the larger of the two so we never undercount.
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            transcript_val = transcript_payload.get(key, 0)
            current = metadata.get(key) or 0
            metadata[key] = max(current, transcript_val)
        if transcript_payload.get("model"):
            metadata["genai_model"] = transcript_payload["model"]
        metadata["genai_system"] = transcript_payload.get("system", "anthropic")
        if usage_source == "index":
            usage_source = "merged"

    metadata["usage_source"] = usage_source

    emit_framework_operation(
        project_root,
        operation="session_token_rollup",
        component=_HOOK_COMPONENT,
        source="hook",
        correlation_id=correlation_id,
        metadata=metadata,
    )


def _safe_transcript_aggregate(project_root: Path, *, session_id: str | None) -> dict | None:
    """Best-effort wrapper around ``aggregate_session_usage``.

    Returns the aggregated usage dict when a transcript is found AND it
    contains at least one assistant ``usage`` block. Returns ``None`` if no
    transcript is available or the transcript carried zero usage data --
    callers treat ``None`` as "transcript silent" rather than "zero tokens".
    """
    try:
        transcript = find_active_transcript(project_root, session_id=session_id)
        if transcript is None:
            return None
        payload = aggregate_session_usage(transcript)
    except Exception:
        # Transcript reading is purely advisory; never let it break the
        # rollup emission contract.
        return None
    if (
        not payload.get("input_tokens")
        and not payload.get("output_tokens")
        and not payload.get("model")
    ):
        return None
    return payload


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

    correlation_id = get_correlation_id()
    _emit_summary_event(
        project_root,
        session_id=session_id,
        correlation_id=correlation_id,
        checkpoint_written=True,
        ralph_active=bool(ralph_state and ralph_state.get("active")),
        ralph_reason=reason,
        ralph_retries=int((ralph_state or {}).get("retries", 0)),
    )

    # Spec-120 T-E1: stamp the session token rollup last so the rollup
    # event lands after the summary in the NDJSON stream and includes
    # the summary itself in any future re-run that re-indexes.
    _emit_session_token_rollup(
        project_root,
        session_id=session_id,
        correlation_id=correlation_id,
    )

    # Spec-120 R-2: convergence-driven Ralph reinjection. When the
    # convergence checker reports failures and the retry budget is not
    # exhausted, write a ``decision: block`` JSON to stdout so Claude
    # Code reinjects ``additionalContext`` as the next turn. The
    # passthrough_stdin call below is skipped in that branch — Claude
    # Code reads exactly one JSON object per Stop hook.
    reinjected = _ralph_convergence_loop(
        project_root,
        session_id=session_id,
        correlation_id=correlation_id,
        last_prompt=last_prompt,
    )
    if not reinjected:
        passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(main, component="hook.runtime-stop", hook_kind="stop", script_path=__file__)
