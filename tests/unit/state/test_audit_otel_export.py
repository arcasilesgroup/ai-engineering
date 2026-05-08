"""Unit tests for ``ai_engineering.state.audit_otel_export`` (spec-120 T-C5).

Covers the §4.5 field mapping for every documented row, the OTLP/JSON
envelope shape, and the protobuf JSON conventions for ``intValue`` and
``startTimeUnixNano`` (both serialised as JSON strings).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ai_engineering.state.audit_index import (
    NDJSON_REL,
    build_index,
    open_index_readonly,
)
from ai_engineering.state.audit_otel_export import build_otlp_spans

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex16(seed: str) -> str:
    """Return a deterministic 16-hex span_id derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def _hex32(seed: str) -> str:
    """Return a deterministic 32-hex trace_id derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def _make_event(
    *,
    index: int,
    span_id: str,
    trace_id: str = "trace-default",
    parent_span_id: str | None = None,
    kind: str = "skill_invoked",
    component: str = "hook.telemetry-skill",
    outcome: str = "success",
    detail: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a synthetic NDJSON event."""
    base_ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
    iso_ts = timestamp if timestamp is not None else base_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    event: dict[str, Any] = {
        "kind": kind,
        "engine": "claude_code",
        "timestamp": iso_ts,
        "component": component,
        "outcome": outcome,
        "correlationId": f"corr-{index:04d}",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "spanId": span_id,
        "traceId": _hex32(trace_id),
        "sessionId": "session-otel",
        "detail": detail if detail is not None else {"skill": "ai-brainstorm"},
    }
    if parent_span_id is not None:
        event["parentSpanId"] = parent_span_id
    return event


def _genai_detail(
    *,
    system: str = "anthropic",
    model: str = "claude-sonnet-4-5",
    input_tokens: int = 1234,
    output_tokens: int = 567,
    total_tokens: int = 1801,
    cost_usd: float = 0.0143,
) -> dict[str, Any]:
    """Build a ``detail`` dict with a populated ``genai`` block."""
    return {
        "skill": "ai-brainstorm",
        "genai": {
            "system": system,
            "request": {"model": model},
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
            },
        },
    }


def _seed_db(project_root: Path, events: list[dict[str, Any]]) -> sqlite3.Connection:
    """Write ``events`` as NDJSON, build the SQLite index, return read-only conn."""
    target = project_root / NDJSON_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    target.write_text(body, encoding="utf-8")
    build_index(project_root, rebuild=True)
    return open_index_readonly(project_root)


def _spans_from(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the spans list out of an OTLP envelope (one resource, one scope)."""
    return envelope["resourceSpans"][0]["scopeSpans"][0]["spans"]


def _attrs_to_dict(attributes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Convert OTLP attribute list to ``{key: value_payload}`` dict."""
    return {attr["key"]: attr["value"] for attr in attributes}


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Anchor a fresh project root with the standard state dir."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Field mapping (spec-120 §4.5)
# ---------------------------------------------------------------------------


def test_field_mapping_per_spec_4_5(project_root: Path) -> None:
    """Synthetic event with full genai block; assert each §4.5 row maps."""
    span_id = _hex16("primary")
    parent_id = _hex16("root")
    iso_ts = "2026-01-15T12:30:45Z"

    event = _make_event(
        index=0,
        span_id=span_id,
        parent_span_id=parent_id,
        kind="skill_invoked",
        component="skill.ai-build",
        outcome="success",
        detail=_genai_detail(
            system="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=1234,
            output_tokens=567,
        ),
        timestamp=iso_ts,
    )
    # Add the parent so the span is not orphaned when we filter (parent
    # not strictly needed for OTel export -- parent_span_id passes
    # through regardless).
    parent_event = _make_event(
        index=-1,
        span_id=parent_id,
        kind="agent_dispatched",
        component="agent.dispatcher",
        outcome="success",
    )
    conn = _seed_db(project_root, [parent_event, event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()

    spans = _spans_from(envelope)
    assert len(spans) == 2
    primary = next(s for s in spans if s["spanId"] == span_id)

    # traceId / spanId / parentSpanId pass through.
    assert primary["traceId"] == _hex32("trace-default")
    assert primary["spanId"] == span_id
    assert primary["parentSpanId"] == parent_id
    # kind -> name.
    assert primary["name"] == "skill_invoked"
    # default span kind.
    assert primary["kind"] == "SPAN_KIND_INTERNAL"
    # status from outcome.
    assert primary["status"] == {"code": "STATUS_CODE_OK"}
    # Attributes map.
    attrs = _attrs_to_dict(primary["attributes"])
    assert attrs["component"] == {"stringValue": "skill.ai-build"}
    assert attrs["gen_ai.system"] == {"stringValue": "anthropic"}
    assert attrs["gen_ai.request.model"] == {"stringValue": "claude-sonnet-4-5"}
    assert attrs["gen_ai.usage.input_tokens"] == {"intValue": "1234"}
    assert attrs["gen_ai.usage.output_tokens"] == {"intValue": "567"}


def test_failure_outcome_flips_status_error(project_root: Path) -> None:
    """``outcome=failure`` translates to STATUS_CODE_ERROR."""
    event = _make_event(index=0, span_id=_hex16("fail"), outcome="failure")
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert spans[0]["status"] == {"code": "STATUS_CODE_ERROR"}


def test_success_outcome_status_ok(project_root: Path) -> None:
    """``outcome=success`` translates to STATUS_CODE_OK."""
    event = _make_event(index=0, span_id=_hex16("ok"), outcome="success")
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert spans[0]["status"] == {"code": "STATUS_CODE_OK"}


def test_other_outcome_status_unset(project_root: Path) -> None:
    """Outcomes other than success/failure map to STATUS_CODE_UNSET."""
    event = _make_event(index=0, span_id=_hex16("other"), outcome="degraded")
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert spans[0]["status"] == {"code": "STATUS_CODE_UNSET"}


def test_iso_to_unix_nano_exact(project_root: Path) -> None:
    """A known ISO timestamp converts to a known unix-nano value."""
    # 2026-01-15T12:30:45Z = unix seconds 1768523445.
    iso_ts = "2026-01-15T12:30:45Z"
    expected_seconds = int(datetime(2026, 1, 15, 12, 30, 45, tzinfo=UTC).timestamp())
    expected_nano = expected_seconds * 1_000_000_000

    event = _make_event(index=0, span_id=_hex16("ts"), timestamp=iso_ts)
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert spans[0]["startTimeUnixNano"] == str(expected_nano)
    assert spans[0]["endTimeUnixNano"] == str(expected_nano + 1)


def test_iso_to_unix_nano_subsecond(project_root: Path) -> None:
    """Sub-second ISO timestamp preserved through the conversion."""
    iso_ts = "2026-01-15T12:30:45.123456+00:00"
    expected_seconds = datetime(2026, 1, 15, 12, 30, 45, 123456, tzinfo=UTC).timestamp()
    expected_nano = int(expected_seconds * 1_000_000_000)

    event = _make_event(index=0, span_id=_hex16("frac"), timestamp=iso_ts)
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert spans[0]["startTimeUnixNano"] == str(expected_nano)


def test_missing_genai_leaves_attrs_empty(project_root: Path) -> None:
    """No genai block -> only ``component`` attribute remains."""
    event = _make_event(index=0, span_id=_hex16("plain"))  # default detail has no genai
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    attrs = _attrs_to_dict(spans[0]["attributes"])
    assert "component" in attrs
    assert "gen_ai.system" not in attrs
    assert "gen_ai.request.model" not in attrs
    assert "gen_ai.usage.input_tokens" not in attrs
    assert "gen_ai.usage.output_tokens" not in attrs


def test_root_span_omits_parent_span_id(project_root: Path) -> None:
    """Spans without parent_span_id omit the field entirely."""
    event = _make_event(index=0, span_id=_hex16("root"))
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert "parentSpanId" not in spans[0]


# ---------------------------------------------------------------------------
# Envelope shape
# ---------------------------------------------------------------------------


def test_envelope_shape(project_root: Path) -> None:
    """resourceSpans -> scopeSpans -> spans structure intact."""
    event = _make_event(index=0, span_id=_hex16("e"))
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()

    assert "resourceSpans" in envelope
    rs = envelope["resourceSpans"]
    assert isinstance(rs, list) and len(rs) == 1
    assert "resource" in rs[0]
    assert "scopeSpans" in rs[0]
    ss = rs[0]["scopeSpans"]
    assert isinstance(ss, list) and len(ss) == 1
    assert "scope" in ss[0]
    assert ss[0]["scope"]["name"] == "ai-engineering"
    assert "spans" in ss[0]
    # Resource attributes carry service.name.
    resource_attrs = _attrs_to_dict(rs[0]["resource"]["attributes"])
    assert resource_attrs["service.name"] == {"stringValue": "ai-engineering"}


def test_envelope_uses_pkg_version(project_root: Path) -> None:
    """``pkg_version`` is forwarded into the InstrumentationScope."""
    event = _make_event(index=0, span_id=_hex16("e"))
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(
            conn,
            trace_id=_hex32("trace-default"),
            pkg_version="custom-1.2.3",
        )
    finally:
        conn.close()
    assert envelope["resourceSpans"][0]["scopeSpans"][0]["scope"]["version"] == "custom-1.2.3"


def test_int_value_serialized_as_string(project_root: Path) -> None:
    """Per protobuf JSON, intValue must be serialised as a string."""
    event = _make_event(
        index=0,
        span_id=_hex16("int"),
        detail=_genai_detail(input_tokens=42, output_tokens=7),
    )
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    attrs = _attrs_to_dict(spans[0]["attributes"])
    assert attrs["gen_ai.usage.input_tokens"]["intValue"] == "42"
    assert isinstance(attrs["gen_ai.usage.input_tokens"]["intValue"], str)
    assert attrs["gen_ai.usage.output_tokens"]["intValue"] == "7"
    assert isinstance(attrs["gen_ai.usage.output_tokens"]["intValue"], str)


def test_envelope_serialises_to_json(project_root: Path) -> None:
    """json.dumps round-trips the envelope without surprises."""
    event = _make_event(index=0, span_id=_hex16("ser"), detail=_genai_detail())
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    serialised = json.dumps(envelope)
    parsed = json.loads(serialised)
    assert parsed == envelope


def test_envelope_empty_when_no_matching_trace(project_root: Path) -> None:
    """A trace_id with no matching events yields an empty spans list."""
    event = _make_event(index=0, span_id=_hex16("a"), trace_id="trace-A")
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("not-this-one"))
    finally:
        conn.close()
    assert _spans_from(envelope) == []


def test_iso_unparseable_falls_back_to_zero(project_root: Path) -> None:
    """Malformed timestamps degrade gracefully to 0 ns."""
    event = _make_event(index=0, span_id=_hex16("bad-ts"), timestamp="not-a-timestamp")
    conn = _seed_db(project_root, [event])
    try:
        envelope = build_otlp_spans(conn, trace_id=_hex32("trace-default"))
    finally:
        conn.close()
    spans = _spans_from(envelope)
    assert spans[0]["startTimeUnixNano"] == "0"
    assert spans[0]["endTimeUnixNano"] == "1"
