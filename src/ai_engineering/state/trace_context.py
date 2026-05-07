"""Trace-context lifecycle for spec-120 §4.1 (pkg side).

Maintains a tiny per-project state file
(`.ai-engineering/runtime/trace-context.json`) that records the
active W3C-style trace identifier and a stack of nested span IDs. The
file is local-only (gitignored under `runtime/`) and rebuildable -- if
it goes missing or corrupts, the next read returns a fresh trace_id and
the chain re-anchors.

Public API (mirrored byte-for-byte by the stdlib-only
`_lib/trace_context.py` hook-side companion):

* :func:`new_trace_id` -- 32-hex UUID4 hex
* :func:`new_span_id` -- 16-hex (UUID4 hex truncated)
* :func:`read_trace_context` -- read or None on miss/corruption
* :func:`write_trace_context` -- atomic write via tempfile + os.replace
* :func:`push_span` / :func:`pop_span` -- in-file span stack mutators
* :func:`current_trace_context` -- (trace_id, parent_span_id) reader
  with fresh-fallback (does NOT persist; caller decides)
* :func:`clear_trace_context` -- remove the file (no-op if absent)

Stdlib-only by design (json + os + uuid + datetime + pathlib +
tempfile). The corruption-fallback `framework_error` emission imports
``ai_engineering.state.observability.emit_framework_error`` lazily; if
that import fails (circular / pre-install), we degrade to a stdlib-only
NDJSON line written directly to ``framework-events.ndjson`` matching
the wire format produced by `_lib/observability.append_framework_event`.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

# ---------------------------------------------------------------------------
# Paths + constants
# ---------------------------------------------------------------------------

# spec-125 Wave 2 (T-2.21): canonical runtime dir is ``.ai-engineering/runtime``
# (per ``hook_context.RUNTIME_DIR`` SSOT). Literal duplicated here to avoid
# CLI/state→hook-lib import boundary violation; same pattern as
# ``cli_commands/gate.py`` cache_dir resolution (T-2.13).
TRACE_CONTEXT_REL = Path(".ai-engineering") / "runtime" / "trace-context.json"
FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
SCHEMA_VERSION = "1.0"


def trace_context_path(project_root: Path) -> Path:
    """Return the canonical trace-context state file path."""
    return project_root / TRACE_CONTEXT_REL


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def new_trace_id() -> str:
    """Return a fresh 32-hex W3C-style trace identifier."""
    return uuid4().hex


def new_span_id() -> str:
    """Return a fresh 16-hex span identifier.

    Per spec-120 §4.1 spans are half the length of a trace ID. We
    truncate ``uuid4().hex`` (32 hex chars) to its first 16 chars; the
    distribution remains uniform.
    """
    return uuid4().hex[:16]


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write `payload` to `path` atomically via sibling tempfile + replace.

    Mirrors the policy/orchestrator atomic publish pattern: write to a
    `.tmp` sibling, fsync, then os.replace. If anything fails before
    replace, the tempfile is unlinked so no `.tmp` leaks remain.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(line)
            tmp.flush()
            os.fsync(tmp.fileno())
    except BaseException:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        raise
    os.replace(tmp_path, str(path))


def _emit_corruption_event(project_root: Path, summary: str) -> None:
    """Best-effort emission of a `framework_error` for corruption.

    First path: import the canonical pkg helper. Second path
    (circular-import / pre-install fallback): write a single NDJSON line
    directly to `framework-events.ndjson`, matching the schema produced
    by `_lib/observability.append_framework_event`.
    """
    try:
        from ai_engineering.state.observability import emit_framework_error

        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component="state.trace_context",
            error_code="trace_context_corrupted",
            summary=summary,
        )
        return
    except Exception:
        # Fallback path must absorb every failure (BLE001 silenced intentionally:
        # this is the recovery branch -- raising here would defeat its purpose).
        pass

    _emit_corruption_event_stdlib(project_root, summary)


def _emit_corruption_event_stdlib(project_root: Path, summary: str) -> None:
    """Stdlib-only NDJSON fallback. Wire-shape parity with
    `_lib/observability.append_framework_event`.
    """
    events_path = project_root / FRAMEWORK_EVENTS_REL
    try:
        events_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    entry: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": project_root.name,
        "engine": "ai_engineering",
        "kind": "framework_error",
        "outcome": "failure",
        "component": "state.trace_context",
        "correlationId": uuid4().hex,
        "detail": {
            "error_code": "trace_context_corrupted",
            "summary": summary[:200],
        },
    }
    entry["prev_event_hash"] = _compute_prev_event_hash(events_path)
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    try:
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        return


def _compute_prev_event_hash(path: Path) -> str | None:
    """Mirror of `_lib/observability._compute_prev_event_hash` (stdlib-only).

    SHA256 of the canonical-JSON of the last NDJSON entry, excluding the
    `prev_event_hash` / `prevEventHash` fields. Returns None for missing
    / empty / malformed-tail files (chain re-anchors).
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip():
        return None
    last_line = text.strip().splitlines()[-1].strip()
    if not last_line:
        return None
    try:
        prior = json.loads(last_line)
    except ValueError:
        return None
    if not isinstance(prior, dict):
        return None
    stripped = {k: v for k, v in prior.items() if k not in ("prev_event_hash", "prevEventHash")}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------


def read_trace_context(project_root: Path) -> dict | None:
    """Return the parsed trace-context dict or None if missing / corrupted.

    On corruption we emit a `framework_error` with
    `error_code = trace_context_corrupted` (best-effort; degrades to the
    stdlib NDJSON fallback if the canonical helper is unavailable) and
    return None so callers fall back to a fresh trace.
    """
    path = trace_context_path(project_root)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _emit_corruption_event(project_root, f"read failed: {exc!s}")
        return None
    if not text.strip():
        # Empty file is treated as missing; do not log as corruption -- a
        # zero-length file is often the legitimate "between-write" state
        # of an aborted publish, and the next call writes fresh content.
        return None
    try:
        payload = json.loads(text)
    except ValueError as exc:
        _emit_corruption_event(project_root, f"json parse failed: {exc!s}")
        return None
    if not isinstance(payload, dict):
        _emit_corruption_event(project_root, "payload is not a JSON object")
        return None
    return payload


def write_trace_context(project_root: Path, ctx: dict) -> None:
    """Persist `ctx` atomically. Caller owns the dict shape; we do not validate."""
    path = trace_context_path(project_root)
    payload = dict(ctx)
    payload.setdefault("schemaVersion", SCHEMA_VERSION)
    payload["updatedAt"] = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _atomic_write_json(path, payload)


# ---------------------------------------------------------------------------
# Span stack
# ---------------------------------------------------------------------------


def push_span(project_root: Path, span_id: str) -> None:
    """Append `span_id` to the in-file span stack.

    If the file is missing or corrupted, a fresh context is created with
    a new trace_id and the given span_id as the sole stack entry.
    """
    ctx = read_trace_context(project_root)
    if not ctx or not isinstance(ctx.get("traceId"), str):
        ctx = {
            "traceId": new_trace_id(),
            "span_stack": [span_id],
            "schemaVersion": SCHEMA_VERSION,
        }
        write_trace_context(project_root, ctx)
        return

    stack = ctx.get("span_stack")
    if not isinstance(stack, list):
        stack = []
    stack.append(span_id)
    ctx["span_stack"] = stack
    write_trace_context(project_root, ctx)


def pop_span(project_root: Path) -> str | None:
    """Pop and return the top span_id, or None if the stack is empty / absent."""
    ctx = read_trace_context(project_root)
    if not ctx:
        return None
    stack = ctx.get("span_stack")
    if not isinstance(stack, list) or not stack:
        return None
    popped = stack.pop()
    ctx["span_stack"] = stack
    write_trace_context(project_root, ctx)
    if not isinstance(popped, str):
        return None
    return popped


def current_trace_context(project_root: Path) -> tuple[str, str | None]:
    """Return ``(trace_id, parent_span_id)`` for the active context.

    If no context exists or the existing one is unusable, a fresh
    trace_id is generated and ``(trace_id, None)`` is returned WITHOUT
    persisting the file. Callers that want to materialise the trace
    must call `push_span` or `write_trace_context` themselves -- this
    keeps read paths side-effect free.
    """
    ctx = read_trace_context(project_root)
    if not ctx:
        return new_trace_id(), None

    trace_id = ctx.get("traceId")
    if not isinstance(trace_id, str) or not trace_id:
        return new_trace_id(), None

    stack = ctx.get("span_stack")
    parent: str | None = None
    if isinstance(stack, list) and stack:
        last = stack[-1]
        if isinstance(last, str):
            parent = last
    return trace_id, parent


def clear_trace_context(project_root: Path) -> None:
    """Remove the trace-context state file. No-op if absent."""
    path = trace_context_path(project_root)
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        # Best-effort cleanup: a permission error or stale-handle case
        # should not crash the caller. Surface it via the same corruption
        # channel so it's at least observable.
        _emit_corruption_event(project_root, f"failed to unlink {path!s}")


__all__ = [
    "FRAMEWORK_EVENTS_REL",
    "SCHEMA_VERSION",
    "TRACE_CONTEXT_REL",
    "clear_trace_context",
    "current_trace_context",
    "new_span_id",
    "new_trace_id",
    "pop_span",
    "push_span",
    "read_trace_context",
    "trace_context_path",
    "write_trace_context",
]
