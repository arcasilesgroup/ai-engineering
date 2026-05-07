"""Tests for spec-120 §4.1 trace-context fields on FrameworkEvent.

Covers the ACCEPT-WHEN-PRESENT contract added to
`validate_event_schema`: optional `traceId` / `spanId` / `parentSpanId`
must either be absent or match their hex patterns. Existing required
fields and engine enum behaviour live in `test_event_schema.py` and
must remain green alongside these additions.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _minimal_event() -> dict:
    """Mirror of the helper in test_event_schema.py; kept local to avoid
    cross-module fixture imports and to make this file standalone."""
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


# ---------------------------------------------------------------------------
# traceId
# ---------------------------------------------------------------------------


def test_valid_trace_id_accepted() -> None:
    """A 32-hex traceId is accepted when present."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["traceId"] = "0123456789abcdef0123456789abcdef"
    assert validate_event_schema(event) is True


@pytest.mark.parametrize(
    "trace_id",
    [
        "",  # empty
        "0123456789abcdef0123456789abcde",  # 31 chars
        "0123456789abcdef0123456789abcdef0",  # 33 chars
        "0123456789ABCDEF0123456789ABCDEF",  # uppercase rejected
        "0123456789abcdef0123456789abcdeg",  # non-hex char
        "0123456789abcdef-123456789abcdef",  # dash
        None,
        12345,
        ["0123456789abcdef0123456789abcdef"],
    ],
)
def test_invalid_trace_id_rejected(trace_id) -> None:
    """Malformed traceId fails closed."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["traceId"] = trace_id
    assert validate_event_schema(event) is False, f"validator must reject traceId={trace_id!r}"


# ---------------------------------------------------------------------------
# spanId
# ---------------------------------------------------------------------------


def test_valid_span_id_accepted() -> None:
    """A 16-hex spanId is accepted when present."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["spanId"] = "abcdef0123456789"
    assert validate_event_schema(event) is True


@pytest.mark.parametrize(
    "span_id",
    [
        "",  # empty
        "abcdef012345678",  # 15 chars
        "abcdef01234567890",  # 17 chars
        "ABCDEF0123456789",  # uppercase rejected
        "zbcdef0123456789",  # non-hex char
        None,
        42,
    ],
)
def test_invalid_span_id_rejected(span_id) -> None:
    """Malformed spanId fails closed."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["spanId"] = span_id
    assert validate_event_schema(event) is False, f"validator must reject spanId={span_id!r}"


# ---------------------------------------------------------------------------
# parentSpanId (allowed to be None for root spans)
# ---------------------------------------------------------------------------


def test_valid_parent_span_id_accepted() -> None:
    """A 16-hex parentSpanId is accepted when present."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["parentSpanId"] = "0011223344556677"
    assert validate_event_schema(event) is True


def test_null_parent_span_id_accepted() -> None:
    """parentSpanId=None is the legal root-span signal and must validate."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["parentSpanId"] = None
    assert validate_event_schema(event) is True


@pytest.mark.parametrize(
    "parent_span_id",
    [
        "",
        "001122334455667",  # 15 chars
        "00112233445566778",  # 17 chars
        "00112233ZZ556677",  # non-hex char
        7,
        ["0011223344556677"],
    ],
)
def test_invalid_parent_span_id_rejected(parent_span_id) -> None:
    """Malformed parentSpanId fails closed (None remains accepted)."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["parentSpanId"] = parent_span_id
    assert validate_event_schema(event) is False, (
        f"validator must reject parentSpanId={parent_span_id!r}"
    )


# ---------------------------------------------------------------------------
# Absence + mixed presence -- additive, backward compatible
# ---------------------------------------------------------------------------


def test_all_three_absent_is_still_valid() -> None:
    """Legacy events without any trace context must keep validating."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    # Sanity: none of the new keys are present.
    assert "traceId" not in event
    assert "spanId" not in event
    assert "parentSpanId" not in event
    assert validate_event_schema(event) is True


def test_trace_id_only_no_span_id_accepted() -> None:
    """Mixed presence (traceId without spanId) is permitted; the validator
    only enforces the shape of fields that are present."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["traceId"] = "00112233445566778899aabbccddeeff"
    assert "spanId" not in event
    assert "parentSpanId" not in event
    assert validate_event_schema(event) is True


def test_full_trace_context_round_trip_accepted() -> None:
    """All three fields present and well-formed: accepted."""
    from ai_engineering.state.event_schema import validate_event_schema

    event = _minimal_event()
    event["traceId"] = "ffeeddccbbaa99887766554433221100"
    event["spanId"] = "1122334455667788"
    event["parentSpanId"] = "8877665544332211"
    assert validate_event_schema(event) is True
