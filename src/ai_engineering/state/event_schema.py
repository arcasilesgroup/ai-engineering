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

from typing import Any, TypedDict

_ENGINE_ALIASES: dict[str, str] = {"github_copilot": "copilot"}

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
    return isinstance(detail, dict)


__all__ = [
    "ALLOWED_ENGINES",
    "ALLOWED_EVENT_KINDS",
    "FrameworkEvent",
    "normalize_engine_id",
    "validate_event_schema",
]
