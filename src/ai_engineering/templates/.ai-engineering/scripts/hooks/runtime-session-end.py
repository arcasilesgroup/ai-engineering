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
import os
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
_NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
_VACUUM_FREELIST_THRESHOLD = 1000
_VACUUM_PAGES_PER_CALL = 1000
# Short busy timeout so a contended DB (active reader during SessionEnd)
# never blocks the hook budget. 250 ms is plenty for the short PRAGMA we
# run; longer waits should fail-open instead.
_VACUUM_BUSY_TIMEOUT_MS = 250

# spec-138 M4.T3 + M4.T4 — events-table SessionEnd rebuild + NDJSON rotation
# trigger. The rebuild is incremental (via audit_index.build_index with
# rebuild=False) so steady-state SessionEnd stays under 5 s. The rotation
# trigger checks size/lines after the rebuild and invokes the rotation
# helper when thresholds are exceeded; the actual rotation throttle lives
# in runtime-rotate-throttled.py (spec-139 M6).
_NDJSON_MAX_LINES_DEFAULT = 100_000
_NDJSON_MAX_BYTES_DEFAULT = 50 * 1024 * 1024  # 50 MB
_REBUILD_BUDGET_SEC = 5.0


def _ndjson_max_lines() -> int:
    raw = (os.environ.get("AIENG_NDJSON_MAX_LINES") or "").strip()
    if not raw:
        return _NDJSON_MAX_LINES_DEFAULT
    try:
        return max(1, int(raw))
    except ValueError:
        return _NDJSON_MAX_LINES_DEFAULT


def _ndjson_max_bytes() -> int:
    raw = (os.environ.get("AIENG_NDJSON_MAX_BYTES") or "").strip()
    if not raw:
        return _NDJSON_MAX_BYTES_DEFAULT
    try:
        return max(1, int(raw))
    except ValueError:
        return _NDJSON_MAX_BYTES_DEFAULT


def _rebuild_events_index(project_root: Path) -> dict[str, int] | None:
    """Rebuild ``state.db.events`` from the NDJSON at SessionEnd.

    spec-138 M4.T3: ``state.db.events`` is a SessionEnd-rebuilt derived
    cache. Incremental indexing via ``audit_index.build_index(rebuild=False)``
    keeps the budget under 5 s on steady-state operator hosts. Returns
    ``{"rows_indexed": N, "rows_total": M, "duration_ms": K}`` on
    success, ``None`` on any failure (fail-open). The hook never blocks
    SessionEnd on this path.

    Invokes ``ai-eng audit index --json`` as a subprocess rather than
    importing the package directly: the hook runs under the system
    ``python3`` shebang where the ``ai_engineering`` package may not be
    importable, while the ``ai-eng`` console entry point (installed by
    ``pip install -e .`` or via ``uv sync``) carries its own venv
    shebang and always resolves the package. Subprocess timeout caps at
    the 5-s SessionEnd budget; on timeout / non-zero exit / missing CLI
    we return None and the SessionEnd path continues.
    """
    import shutil as _shutil
    import subprocess as _subprocess
    import time as _time

    started = _time.monotonic()
    # Resolve ai-eng entry point. PATH first (canonical install via
    # `pip install -e .` or system-wide), then project-local fallback
    # to `.venv/bin/ai-eng` (POSIX) or `.venv\Scripts\ai-eng.exe`
    # (Windows) so the hook still rebuilds the cache on operator hosts
    # that only ran `uv sync` (no PATH activation).
    ai_eng = _shutil.which("ai-eng")
    if ai_eng is None:
        venv_candidates = (
            project_root / ".venv" / "bin" / "ai-eng",
            project_root / ".venv" / "Scripts" / "ai-eng.exe",
            project_root / ".venv" / "Scripts" / "ai-eng",
        )
        for candidate in venv_candidates:
            if candidate.is_file():
                ai_eng = str(candidate)
                break
    if ai_eng is None:
        # CLI not installed — cold-path operators run the rebuild via
        # ``ai-eng audit index --rebuild`` themselves. Fail-open.
        return None
    try:
        proc = _subprocess.run(
            [ai_eng, "audit", "index", "--json"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=_REBUILD_BUDGET_SEC,
            encoding="utf-8",
            errors="replace",
        )
    except (_subprocess.TimeoutExpired, OSError):
        return None
    elapsed = _time.monotonic() - started
    if proc.returncode != 0:
        return None
    try:
        # The audit index --json command emits a single JSON object with
        # rows_indexed + rows_total at minimum. Tolerate framing noise.
        payload_line = next(
            (line for line in proc.stdout.splitlines() if line.strip().startswith("{")),
            "",
        )
        payload = json.loads(payload_line) if payload_line else {}
    except (json.JSONDecodeError, StopIteration):
        return None
    return {
        "rows_indexed": int(payload.get("rows_indexed", 0) or 0),
        "rows_total": int(payload.get("rows_total", 0) or 0),
        "duration_ms": int(elapsed * 1000),
    }


def _ndjson_rotation_needed(project_root: Path) -> dict[str, int] | None:
    """Check NDJSON size/lines and signal rotation when thresholds breached.

    spec-138 M4.T4: returns ``{"lines": N, "bytes": M}`` payload when
    rotation should fire (above the configured thresholds), ``None``
    otherwise. The actual rotation is the responsibility of the
    runtime-rotate-throttled.py wrapper (spec-139 M6) — this helper
    surfaces the signal so the orchestrator can observe.
    """
    ndjson = project_root / _NDJSON_REL
    if not ndjson.is_file():
        return None
    try:
        size = ndjson.stat().st_size
        lines = 0
        with ndjson.open("rb") as fh:
            for _ in fh:
                lines += 1
    except OSError:
        return None
    if lines >= _ndjson_max_lines() or size >= _ndjson_max_bytes():
        return {"lines": lines, "bytes": size}
    return None


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

    # spec-138 M4.T3: SessionEnd rebuild of state.db.events from the
    # NDJSON audit log. Incremental; fail-open; never blocks SessionEnd
    # budget. Operators query the projection via `ai-eng audit query`.
    with contextlib.suppress(Exception):
        rebuild_result = _rebuild_events_index(ctx.project_root)
        if rebuild_result is not None:
            try:
                from _lib.observability import emit_framework_operation

                emit_framework_operation(
                    ctx.project_root,
                    operation="audit_index_rebuilt",
                    component=_COMPONENT,
                    source="hook",
                    correlation_id=get_correlation_id(),
                    metadata=rebuild_result,
                )
            except Exception:
                pass

    # spec-138 M4.T4: NDJSON rotation signal. Emits an event when the
    # configured thresholds are breached; the actual rotation is the
    # responsibility of runtime-rotate-throttled.py (spec-139 M6) which
    # the SessionEnd hook chain invokes via .claude/settings.json.
    with contextlib.suppress(Exception):
        rotation_signal = _ndjson_rotation_needed(ctx.project_root)
        if rotation_signal is not None:
            try:
                from _lib.observability import emit_framework_operation

                emit_framework_operation(
                    ctx.project_root,
                    operation="ndjson_rotation_threshold_breached",
                    component=_COMPONENT,
                    source="hook",
                    correlation_id=get_correlation_id(),
                    metadata=rotation_signal,
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
