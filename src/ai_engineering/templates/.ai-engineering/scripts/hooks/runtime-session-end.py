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

spec-148: this hook no longer touches SQLite. The former SessionEnd
``state.db.events`` rebuild and ``PRAGMA incremental_vacuum`` are gone —
the append-only NDJSON audit log is the single source of truth, read
directly by ``ai-eng audit tokens`` / ``audit replay``.

NDJSON rotation note: NDJSON tail-truncation is delegated to the
spec-138 M4 wiring (see ``runtime-rotate-throttled.py`` for the retention
sweep). This hook intentionally does NOT invoke ``runtime_rotate.py`` —
the throttled wrapper does (per D-139-12, no duplicate invocation).
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import RUNTIME_DIR, get_hook_context

_COMPONENT = "hook.runtime-session-end"
_CHECKPOINT_NAME = "checkpoint.json"

_NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"

# spec-138 M4.T4 — NDJSON rotation trigger. Checks size/lines at SessionEnd
# and signals when thresholds are exceeded; the actual rotation throttle
# lives in runtime-rotate-throttled.py (spec-139 M6).
_NDJSON_MAX_LINES_DEFAULT = 100_000
_NDJSON_MAX_BYTES_DEFAULT = 50 * 1024 * 1024  # 50 MB


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

    # spec-148: the SessionEnd state.db.events rebuild is gone — the NDJSON
    # audit log is the single source of truth (no SQLite projection to
    # rebuild). `audit tokens`/`replay` read the NDJSON directly.

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

    # spec-148: no state.db to vacuum (files-only); the NDJSON log is
    # tail-truncated by runtime-rotate-throttled.py, not PRAGMA'd here.

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="session-end",
        script_path=__file__,
    )
