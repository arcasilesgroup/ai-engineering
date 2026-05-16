"""Stdlib-only trace-context lifecycle for hook scripts (spec-120 §4.1).

Drop-in mirror of ``ai_engineering.state.trace_context`` for use by
hooks that run before ``pip install`` lands the package. Imports
nothing from ``ai_engineering.*`` -- only Python stdlib.

Wire output (the ``runtime/trace-context.json`` file written) is
byte-for-byte identical to the pkg version when given identical
inputs: same JSON serialization (``sort_keys=True``,
``separators=(",", ":")``), same ID generation
(``uuid.uuid4().hex`` / ``uuid.uuid4().hex[:16]``), same atomic
publish via tempfile + ``os.replace``.

The corruption-fallback ``framework_error`` emission writes a single
NDJSON line directly to ``framework-events.ndjson`` mirroring the
format produced by ``_lib/observability.append_framework_event``.
We do not import the canonical ``observability.emit_framework_error``
helper here because hook scripts deliberately keep their dependency
graph empty -- everything they need is stdlib + this directory.
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
# Paths + constants (parity with pkg ai_engineering.state.trace_context)
# ---------------------------------------------------------------------------

TRACE_CONTEXT_REL = Path(".ai-engineering") / "state" / "runtime" / "trace-context.json"
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
    """Return a fresh 16-hex span identifier (uuid4().hex truncated)."""
    return uuid4().hex[:16]


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Atomic publish via sibling tempfile + ``os.replace``.

    On exception before replace, the tempfile is unlinked so no
    leftover ``.tmp`` files remain after a successful return path.
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


def _compute_prev_event_hash(path: Path) -> str | None:
    """SHA256 of canonical-JSON of the last NDJSON entry (excluding chain pointer).

    Mirrors ``_lib/observability._compute_prev_event_hash`` so the
    NDJSON line we write here links back into the existing audit chain
    without spurious re-anchoring.
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


def _emit_corruption_event(project_root: Path, summary: str) -> None:
    """Write a single ``framework_error`` NDJSON line for corruption.

    Stdlib-only fallback (no observability import). Keeps the same
    schema fields produced by ``_lib/observability.append_framework_event``
    so downstream consumers (audit_chain reader, schema validator) treat
    the line uniformly.
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


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------


def read_trace_context(project_root: Path) -> dict | None:
    """Return the parsed trace-context dict or None on miss/corruption.

    Corruption emits a ``framework_error`` event with
    ``error_code = trace_context_corrupted`` (best-effort write) and
    returns None. Empty files are treated as missing without an error
    emission -- they're the legitimate intermediate state of an aborted
    publish.
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
    """Persist `ctx` atomically. Caller owns shape; we only stamp metadata."""
    path = trace_context_path(project_root)
    payload = dict(ctx)
    payload.setdefault("schemaVersion", SCHEMA_VERSION)
    payload["updatedAt"] = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _atomic_write_json(path, payload)


# ---------------------------------------------------------------------------
# Span stack
# ---------------------------------------------------------------------------


def push_span(project_root: Path, span_id: str) -> None:
    """Append ``span_id`` to the in-file span stack.

    Missing or corrupted file: create a fresh context with a new
    trace_id and ``span_stack=[span_id]``.
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

    Side-effect free: when no usable context exists, returns a fresh
    trace_id with no parent and does NOT persist anything. Callers that
    want to materialise the trace call ``push_span`` or
    ``write_trace_context`` themselves.
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
