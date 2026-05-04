"""Unified framework-event schema validator (spec-112 T-1.5).

Provides the canonical `FrameworkEvent` TypedDict and a stdlib-only
`validate_event_schema(dict) -> bool` validator. Aligns with the wire
format produced by `state.observability.append_framework_event` and the
hook-local `_lib/observability.append_framework_event` mirror, both of
which stamp `prev_event_hash` at the **root** of the JSON payload per
spec-110 D-110-03.

The validator is **fail-closed**: malformed events return False so the
caller can log to stderr and refuse to write the line. Silently dropping
is a bug; explicit error is a feature (per spec-112 G-4).
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

_ENGINE_ALIASES: dict[str, str] = {"github_copilot": "copilot"}

# Spec-120 §4.1: optional OTel-mirroring identifiers at the event root.
# `traceId` is 32 lowercase hex chars (W3C trace-context spec).
# `spanId` and `parentSpanId` are 16 lowercase hex chars; `parentSpanId`
# may also be None (root span has no logical parent). Compiled once at
# module load to avoid regex re-compilation on every validate call.
_TRACE_ID_RE: re.Pattern[str] = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID_RE: re.Pattern[str] = re.compile(r"^[0-9a-f]{16}$")

# Spec-112 D-112-02: `engine` is required at the root and must be one of
# the values below. Adding a 5th IDE means appending here AND adding the
# adapter; the validator keeps the surface honest.
ALLOWED_ENGINES: frozenset[str] = frozenset(
    {"claude_code", "codex", "gemini", "copilot", "ai_engineering"}
)

ALLOWED_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "skill_invoked",
        "agent_dispatched",
        "context_load",
        "ide_hook",
        "framework_error",
        "git_hook",
        "control_outcome",
        "framework_operation",
        "task_trace",
        # spec-118 memory layer (parity repair: canonical hook had this kind
        # but the Python validator did not, so memory_event events emitted by
        # the canonical hook would fail validate_event_schema in callers that
        # used the Python library path)
        "memory_event",
        # spec-119 evaluation layer
        "eval_run",
    }
)

# Spec-112 G-4: required-at-root keys for every event written to NDJSON.
# `sessionId`, `source`, `prev_event_hash` are optional metadata and
# `detail` may be empty (e.g. control_outcome with no metadata) -- but
# `detail` must still be present as a dict to keep readers schema-stable.
_REQUIRED_KEYS: tuple[str, ...] = (
    "kind",
    "engine",
    "timestamp",
    "component",
    "outcome",
    "correlationId",
    "schemaVersion",
    "project",
)


class FrameworkEvent(TypedDict, total=False):
    """Canonical wire format for `framework-events.ndjson`.

    All required fields live at the root. `detail` carries
    event-specific payload (e.g. `{skill: str}` for skill_invoked or
    `{hook_kind: str}` for ide_hook). `prev_event_hash` is a sibling of
    `kind` (spec-110 D-110-03), not nested under `detail`.

    The TypedDict uses `total=False` so older readers tolerate missing
    optional keys; the runtime validator below enforces the required
    subset and the `engine` enum independently.
    """

    kind: str
    engine: str
    timestamp: str
    prev_event_hash: str | None
    component: str
    outcome: str
    correlationId: str
    sessionId: str | None
    schemaVersion: str
    project: str
    source: str | None
    detail: dict[str, Any]
    # Spec-120 §4.1: optional OTel-mirroring trace identifiers. All three
    # are absent on legacy events; when present they must match the
    # canonical hex shapes enforced by `validate_event_schema`.
    traceId: str
    spanId: str
    parentSpanId: str | None


def normalize_engine_id(engine: str) -> str:
    """Return the canonical engine identifier for framework events."""
    return _ENGINE_ALIASES.get(engine, engine)


def validate_event_schema(event: Any) -> bool:
    """Return True iff `event` matches the unified schema.

    Required: dict shape, all required keys present and non-empty, `engine`
    in `ALLOWED_ENGINES`, `detail` is a dict (may be empty). Returns False
    for any deviation. Does **not** raise -- the caller decides how to
    surface the failure (stderr log, dropped write, etc.).
    """
    if not isinstance(event, dict):
        return False
    for key in _REQUIRED_KEYS:
        if key not in event:
            return False
        value = event[key]
        if value is None or value == "":
            return False
    engine = event.get("engine")
    if not isinstance(engine, str) or engine not in ALLOWED_ENGINES:
        return False
    kind = event.get("kind")
    if not isinstance(kind, str) or kind not in ALLOWED_EVENT_KINDS:
        return False
    detail = event.get("detail", {})
    if not isinstance(detail, dict):
        return False
    # Spec-120 §4.1: ACCEPT-WHEN-PRESENT on optional trace identifiers.
    # Absence is fine (legacy events have none); presence triggers a
    # fail-closed shape check so malformed values cannot enter the stream.
    if "traceId" in event:
        trace_id = event["traceId"]
        if not isinstance(trace_id, str) or not _TRACE_ID_RE.match(trace_id):
            return False
    if "spanId" in event:
        span_id = event["spanId"]
        if not isinstance(span_id, str) or not _SPAN_ID_RE.match(span_id):
            return False
    if "parentSpanId" in event:
        parent_span_id = event["parentSpanId"]
        # `parentSpanId` is allowed to be None (root span); otherwise it
        # must match the same 16-hex shape as `spanId`.
        if parent_span_id is not None:
            if not isinstance(parent_span_id, str) or not _SPAN_ID_RE.match(parent_span_id):
                return False
    return True


__all__ = [
    "ALLOWED_ENGINES",
    "ALLOWED_EVENT_KINDS",
    "FrameworkEvent",
    "normalize_engine_id",
    "validate_event_schema",
]
