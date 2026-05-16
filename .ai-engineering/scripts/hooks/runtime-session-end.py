#!/usr/bin/env python3
"""SessionEnd hook: emit a session summary into the audit chain.

Claude Code fires ``SessionEnd`` once per session terminus (clean exit
or context-window flush). The Stop hook already handles per-turn
checkpointing; SessionEnd is a separate, lower-frequency primitive
that gives us a single anchor event per session for queryability —
useful for the spec-120 SQLite projection and OTLP export.

Reads ``runtime/checkpoint.json`` (best effort) and emits a
``framework_operation`` with ``operation=session_end_summary``
containing the session id, recent edit count, and the convergence
state captured by Stop. Fail-open; any error is swallowed.

spec-139 M6.T2 additions
------------------------
After the summary emission this hook also runs a short
``PRAGMA incremental_vacuum`` against ``state.db`` when the free-page
count exceeds ``_VACUUM_FREELIST_THRESHOLD`` (1000). Vacuuming inside
SessionEnd keeps the WAL-mode database compact without inflating the
hot-path (the operation is bounded and concurrent reads are unaffected).
The block is wrapped in a broad ``try/except`` so a missing or locked DB
never blocks the SessionEnd budget.

NDJSON rotation note: NDJSON tail-truncation is delegated to the
spec-138 M4 wiring (see ``runtime-rotate-throttled.py`` for the retention
sweep). This hook intentionally does NOT invoke ``runtime_rotate.py`` —
the throttled wrapper does (per D-139-12, no duplicate invocation).
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import RUNTIME_DIR, get_hook_context

_COMPONENT = "hook.runtime-session-end"
_CHECKPOINT_NAME = "checkpoint.json"

# spec-139 M6.T2: ``state.db`` lives at the canonical state-plane path.
# We open in WAL mode (the DB is already configured that way at creation
# per src/ai_engineering/state/state_db.py D-122-16) and reclaim free
# pages only when the freelist meaningfully exceeds the threshold so
# every SessionEnd does not pay a no-op PRAGMA round-trip.
_STATE_DB_REL = Path(".ai-engineering") / "state" / "state.db"
_VACUUM_FREELIST_THRESHOLD = 1000
_VACUUM_PAGES_PER_CALL = 1000
# Short busy timeout so a contended DB (active reader during SessionEnd)
# never blocks the hook budget. 250 ms is plenty for the short PRAGMA we
# run; longer waits should fail-open instead.
_VACUUM_BUSY_TIMEOUT_MS = 250


def _read_checkpoint(project_root: Path) -> dict:
    # spec-125 Wave 2: checkpoint lives at ``.ai-engineering/runtime/checkpoint.json``
    # (canonical), resolved via ``RUNTIME_DIR`` so a future move only touches
    # ``_lib/hook_context.py``.
    path = RUNTIME_DIR(project_root) / _CHECKPOINT_NAME
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _state_db_path(project_root: Path) -> Path:
    return project_root / _STATE_DB_REL


def _incremental_vacuum_if_needed(project_root: Path) -> dict[str, int] | None:
    """Run ``PRAGMA incremental_vacuum`` on ``state.db`` when freelist > threshold.

    Returns a dict ``{"before": N, "after": M, "reclaimed": K}`` on success,
    ``None`` when the DB was absent, the freelist was under the threshold,
    or any error occurred. Fail-open: any exception is swallowed so a
    locked or missing DB never blocks the SessionEnd budget.

    Why WAL + short busy timeout?
    -----------------------------
    The DB is created with ``journal_mode=WAL`` and
    ``auto_vacuum=INCREMENTAL`` (mode 2) per
    :mod:`ai_engineering.state.state_db` D-122-16. WAL means concurrent
    readers are unaffected by our PRAGMA. A 250 ms busy timeout caps the
    worst-case wait when another writer holds the lock — beyond that we
    skip rather than miss the SessionEnd 5 s budget.
    """
    db_path = _state_db_path(project_root)
    if not db_path.is_file():
        return None
    try:
        conn = sqlite3.connect(
            str(db_path),
            timeout=_VACUUM_BUSY_TIMEOUT_MS / 1000.0,
            isolation_level=None,
        )
    except sqlite3.Error:
        return None
    try:
        with contextlib.closing(conn):
            try:
                conn.execute(f"PRAGMA busy_timeout = {_VACUUM_BUSY_TIMEOUT_MS}")
                conn.execute("PRAGMA journal_mode = WAL")
                row = conn.execute("PRAGMA freelist_count").fetchone()
                before = int(row[0] or 0) if row else 0
                if before <= _VACUUM_FREELIST_THRESHOLD:
                    return None
                conn.execute(f"PRAGMA incremental_vacuum({_VACUUM_PAGES_PER_CALL})")
                row = conn.execute("PRAGMA freelist_count").fetchone()
                after = int(row[0] or 0) if row else before
                return {
                    "before": before,
                    "after": after,
                    "reclaimed": max(0, before - after),
                }
            except sqlite3.Error:
                return None
    except sqlite3.Error:
        return None


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "SessionEnd":
        passthrough_stdin(ctx.data)
        return

    checkpoint = _read_checkpoint(ctx.project_root)
    metadata: dict[str, object] = {
        "session_id": ctx.session_id,
    }
    if isinstance(checkpoint.get("recent_edits"), list):
        metadata["recent_edit_count"] = len(checkpoint["recent_edits"])
    if isinstance(checkpoint.get("recent_tool_calls"), list):
        metadata["recent_tool_call_count"] = len(checkpoint["recent_tool_calls"])
    if isinstance(checkpoint.get("convergence"), dict):
        conv = checkpoint["convergence"]
        if isinstance(conv.get("converged"), bool):
            metadata["converged"] = conv["converged"]
    reason = ctx.data.get("reason")
    if isinstance(reason, str) and reason.strip():
        metadata["end_reason"] = reason.strip()[:64]

    try:
        from _lib.observability import emit_framework_operation

        emit_framework_operation(
            ctx.project_root,
            operation="session_end_summary",
            component=_COMPONENT,
            source="hook",
            correlation_id=get_correlation_id(),
            metadata=metadata,
        )
    except Exception:
        pass

    # spec-139 M6.T2: opportunistic incremental_vacuum on state.db. Runs
    # only when freelist_count > 1000 so the steady-state SessionEnd path
    # stays cheap. Wrapped in suppress() at the call site as defence-in-
    # depth — the helper already handles its own errors fail-open.
    with contextlib.suppress(Exception):
        vacuum_result = _incremental_vacuum_if_needed(ctx.project_root)
        if vacuum_result is not None:
            try:
                from _lib.observability import emit_framework_operation

                emit_framework_operation(
                    ctx.project_root,
                    operation="state_db_incremental_vacuum",
                    component=_COMPONENT,
                    source="hook",
                    correlation_id=get_correlation_id(),
                    metadata={
                        "freelist_before": vacuum_result["before"],
                        "freelist_after": vacuum_result["after"],
                        "pages_reclaimed": vacuum_result["reclaimed"],
                    },
                )
            except Exception:
                pass

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="session-end",
        script_path=__file__,
    )
