"""OTel/OTLP JSON span exporter for the SQLite audit index (spec-120 §4.5).

Translates the per-trace event tree maintained by
:mod:`ai_engineering.state.audit_index` into an OTLP/JSON envelope so
the user can pipe a session into any OpenTelemetry-compatible backend
(Langfuse, Phoenix, Logfire, Tempo, Honeycomb, etc.). Output shape
follows the `OTLP/JSON encoding
<https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding>`_.

Implements OpenTelemetry GenAI Semantic Conventions snapshot v1.27.0
for the ``gen_ai.*`` attribute names. Field mapping per spec-120 §4.5:

============================================  ======================================
NDJSON                                        OTel
============================================  ======================================
``traceId``                                   ``traceId`` (32-hex)
``spanId``                                    ``spanId`` (16-hex)
``parentSpanId``                              ``parentSpanId`` (omitted at root)
``timestamp``                                 ``startTimeUnixNano`` (string)
``kind``                                      ``name``
``component``                                 ``attributes["component"]``
``detail.genai.system``                       ``attributes["gen_ai.system"]``
``detail.genai.request.model``                ``attributes["gen_ai.request.model"]``
``detail.genai.usage.input_tokens``           ``attributes["gen_ai.usage.input_tokens"]``
``detail.genai.usage.output_tokens``          ``attributes["gen_ai.usage.output_tokens"]``
``outcome=failure``                           ``status.code = STATUS_CODE_ERROR``
``outcome=success``                           ``status.code = STATUS_CODE_OK``
(other)                                       ``status.code = STATUS_CODE_UNSET``
(always)                                      ``kind = SPAN_KIND_INTERNAL``
End time                                      ``endTimeUnixNano = startTimeUnixNano + 1``
============================================  ======================================

Per OTLP/JSON the integer-valued attributes (``intValue``) and the time
unix-nano fields are serialised as JSON strings (protobuf JSON
convention). The exporter follows that exactly.

Stdlib-only by design. No third-party dependencies; the OTLP shape is
expressed as plain ``dict`` / ``list`` so callers can ``json.dumps`` /
post directly to a collector endpoint.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# OTLP/JSON status codes (mirrors the protobuf enum names verbatim so the
# wire output is self-describing).
_STATUS_OK = "STATUS_CODE_OK"
_STATUS_ERROR = "STATUS_CODE_ERROR"
_STATUS_UNSET = "STATUS_CODE_UNSET"

# Default span kind. We do not yet distinguish CLIENT / SERVER / PRODUCER
# from the framework events, so every span is INTERNAL until the schema
# carries a richer hint.
_SPAN_KIND_INTERNAL = "SPAN_KIND_INTERNAL"

# ``service.name`` resource attribute. Hard-coded -- the framework is the
# only producer for these spans.
_SERVICE_NAME = "ai-engineering"

# ``scope.name`` for the InstrumentationScope. Same reasoning as above.
_SCOPE_NAME = "ai-engineering"

# Columns selected from the ``events`` table -- mirrors the projection
# used by :mod:`audit_replay` so both consumers stay in lockstep. Only
# the columns the exporter actually maps are included.
_EVENT_COLUMNS = (
    "span_id",
    "trace_id",
    "parent_span_id",
    "timestamp",
    "ts_unix_ms",
    "kind",
    "component",
    "outcome",
    "genai_system",
    "genai_model",
    "input_tokens",
    "output_tokens",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    """Normalise a SQLite row into a column-keyed dict.

    Mirrors :func:`audit_replay._row_to_dict` -- duplicated rather than
    shared to keep the two consumer modules independent (so neither has
    to know the other exists).
    """
    if isinstance(row, dict):
        return dict(row)
    keys_callable = getattr(row, "keys", None)
    if keys_callable is not None:
        # sqlite3.Row exposes column names via ``.keys()`` and indexes by
        # name -- iteration yields values, so we can't use ``key in row``.
        return {key: row[key] for key in keys_callable()}
    return dict(zip(_EVENT_COLUMNS, row, strict=True))


def _iso_to_unix_nano(iso: str) -> int:
    """Convert an ISO-8601 ``timestamp`` to integer unix nanoseconds.

    The audit index already coerces malformed timestamps to
    ``ts_unix_ms = 0``; here we return ``0`` for the same edge cases so
    the exported span still makes it into the OTLP envelope (a fresh
    backend can correct the time later if needed). Supported inputs:

    * ``2026-01-15T12:30:45Z`` (typical ISO + UTC suffix)
    * ``2026-01-15T12:30:45.123456+00:00`` (fractional + offset)
    """
    if not iso:
        return 0
    candidate = iso.replace("Z", "+00:00") if iso.endswith("Z") else iso
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    # ``timestamp()`` returns float seconds; multiply by 1_000_000_000 and
    # round to the nearest int to preserve sub-microsecond precision.
    return int(dt.timestamp() * 1_000_000_000)


def _string_value(value: Any) -> dict[str, str]:
    """Build a OTLP ``stringValue`` attribute payload."""
    return {"stringValue": str(value)}


def _int_value(value: int) -> dict[str, str]:
    """Build a OTLP ``intValue`` attribute payload (string per JSON conv)."""
    return {"intValue": str(int(value))}


def _attribute(key: str, value_payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap a key + value payload in the OTLP attribute envelope."""
    return {"key": key, "value": value_payload}


def _status_for(outcome: str | None) -> dict[str, str]:
    """Return the OTLP ``status`` block for an outcome string."""
    lower = outcome.lower() if isinstance(outcome, str) else ""
    if lower == "failure":
        return {"code": _STATUS_ERROR}
    if lower == "success":
        return {"code": _STATUS_OK}
    return {"code": _STATUS_UNSET}


def _build_attributes(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Map an event row to its OTLP ``attributes`` list.

    ``component`` always emits when present. The ``gen_ai.*`` attributes
    only emit when the corresponding column is populated -- legacy events
    without a genai block produce a span with just ``component``.
    """
    attrs: list[dict[str, Any]] = []
    component = event.get("component")
    if isinstance(component, str) and component:
        attrs.append(_attribute("component", _string_value(component)))

    system = event.get("genai_system")
    if isinstance(system, str) and system:
        attrs.append(_attribute("gen_ai.system", _string_value(system)))

    model = event.get("genai_model")
    if isinstance(model, str) and model:
        attrs.append(_attribute("gen_ai.request.model", _string_value(model)))

    in_tokens = event.get("input_tokens")
    if isinstance(in_tokens, int) and not isinstance(in_tokens, bool):
        attrs.append(_attribute("gen_ai.usage.input_tokens", _int_value(in_tokens)))

    out_tokens = event.get("output_tokens")
    if isinstance(out_tokens, int) and not isinstance(out_tokens, bool):
        attrs.append(_attribute("gen_ai.usage.output_tokens", _int_value(out_tokens)))

    return attrs


def _build_span(event: dict[str, Any]) -> dict[str, Any]:
    """Build one OTLP span dict from a single audit_index row."""
    timestamp = event.get("timestamp")
    iso = timestamp if isinstance(timestamp, str) else ""
    start_nano = _iso_to_unix_nano(iso)
    # End time defaults to start+1 ns -- the framework does not record
    # span duration today. Spec-120 §4.5 explicitly accepts this.
    end_nano = start_nano + 1

    span: dict[str, Any] = {
        "traceId": event.get("trace_id") or "",
        "spanId": event.get("span_id") or "",
        "name": event.get("kind") or "",
        "kind": _SPAN_KIND_INTERNAL,
        "startTimeUnixNano": str(start_nano),
        "endTimeUnixNano": str(end_nano),
        "attributes": _build_attributes(event),
        "status": _status_for(event.get("outcome")),
    }

    parent_span_id = event.get("parent_span_id")
    if isinstance(parent_span_id, str) and parent_span_id:
        span["parentSpanId"] = parent_span_id

    return span


def _fetch_rows(conn: sqlite3.Connection, *, trace_id: str) -> list[dict[str, Any]]:
    """Return every row in the index that matches ``trace_id``.

    Sorted by ``ts_unix_ms`` ascending so the resulting span list reads
    in chronological order -- not strictly required by OTLP (collectors
    sort on ingest) but it makes the output predictable for tests.
    """
    columns = ", ".join(_EVENT_COLUMNS)
    sql = f"SELECT {columns} FROM events WHERE trace_id = ? ORDER BY ts_unix_ms ASC"
    cur = conn.execute(sql, (trace_id,))
    return [_row_to_dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_otlp_spans(
    conn: sqlite3.Connection,
    *,
    trace_id: str,
    pkg_version: str = "spec-120",
) -> dict[str, Any]:
    """Return an OTLP/JSON envelope for every event under ``trace_id``.

    Parameters
    ----------
    conn:
        Live :class:`sqlite3.Connection` -- typically returned by
        :func:`audit_index.open_index_readonly`.
    trace_id:
        32-hex trace id to filter on. Empty result is fine -- the
        envelope still serialises with an empty ``spans`` list, which
        is a valid OTLP payload.
    pkg_version:
        Value passed through as ``scope.version``. Defaults to the spec
        identifier so the receiving backend can tell which framework
        revision produced the spans.

    Returns
    -------
    dict
        The full OTLP envelope, ready for ``json.dumps``.

    Notes
    -----
    Per OTLP/JSON the ``startTimeUnixNano`` / ``endTimeUnixNano`` and
    ``intValue`` fields are serialised as JSON strings (protobuf JSON
    convention). This builder does that conversion in
    :func:`_build_span` / :func:`_int_value` so the dict is ready to
    write directly without further massaging.
    """
    rows = _fetch_rows(conn, trace_id=trace_id)
    spans = [_build_span(row) for row in rows]
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [_attribute("service.name", _string_value(_SERVICE_NAME))],
                },
                "scopeSpans": [
                    {
                        "scope": {"name": _SCOPE_NAME, "version": pkg_version},
                        "spans": spans,
                    }
                ],
            }
        ]
    }


__all__ = [
    "build_otlp_spans",
]
