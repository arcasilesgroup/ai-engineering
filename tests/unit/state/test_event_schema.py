"""Tests for src/ai_engineering/state/event_schema.py (spec-112 T-1.4..T-1.6).

Covers G-4: schema validator for the unified `FrameworkEvent` shape.
Required fields, engine enum, and explicit failure (not silent drop) are
the central concerns of the v2 schema validator.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _minimal_event() -> dict:
    return {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "component": "hook.telemetry-skill",
        "outcome": "success",
        "correlationId": "abc123",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"skill": "ai-brainstorm"},
    }


def test_validate_minimal_event() -> None:
    """A minimal but complete event must validate."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    assert validate_event_schema(event) is True


@pytest.mark.parametrize(
    "missing",
    [
        "kind",
        "engine",
        "timestamp",
        "component",
        "outcome",
        "correlationId",
        "schemaVersion",
        "project",
    ],
)
def test_reject_missing_required_field(missing: str) -> None:
    """Each required field is non-optional; absence must produce False."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event.pop(missing)
    assert validate_event_schema(event) is False, (
        f"validator must reject missing required field {missing!r}"
    )


@pytest.mark.parametrize(
    "engine",
    ["bogus", "Claude", "GEMINI", "", None, 42],
)
def test_engine_value_must_be_in_enum(engine) -> None:
    """`engine` field must be one of the v2 allowed values."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["engine"] = engine
    assert validate_event_schema(event) is False, (
        f"validator must reject engine={engine!r} (not in allowed enum)"
    )


@pytest.mark.parametrize(
    "engine",
    ["claude_code", "codex", "gemini", "copilot", "ai_engineering"],
)
def test_engine_enum_accepts_valid_values(engine: str) -> None:
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["engine"] = engine
    assert validate_event_schema(event) is True
