"""Replay framework-events.ndjson into the events table (spec-122-b T-2.6).

Idempotent: ``ON CONFLICT(span_id) DO NOTHING`` so re-running the migration
on a populated DB produces zero net inserts. Malformed lines are skipped
with stderr warnings; non-UTF-8 lines also skipped.

Span ID derivation
------------------
Pre-spec-120 events did not always carry ``span_id``. We derive a stable
synthetic id by hashing the full canonical-JSON payload:

    span_id = "synthetic:" + sha256(canonical_json(event))[:24]

Events that DO carry a ``span_id`` (post-spec-120) keep it. The synthetic
prefix lets downstream code distinguish.

Generated columns ``ts_unix_ms`` and ``archive_month`` are populated by
SQLite from the stored ``timestamp`` (column GENERATED ALWAYS AS STORED).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

BODY_SHA256 = "927d82058dad112d2ffd9d1b07e9e38fb53d933574ff0b5db07343be7acca7dd"

_NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"

_INSERT = """
INSERT INTO events
  (span_id, trace_id, parent_span_id, correlation_id, session_id,
   timestamp, engine, kind, component, outcome, source,
   prev_event_hash, genai_system, genai_model,
   input_tokens, output_tokens, total_tokens, cost_usd, detail_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(span_id) DO NOTHING
"""


def _project_root_from_db(conn: sqlite3.Connection) -> Path:
    row = conn.execute("PRAGMA database_list").fetchone()
    if row is None or not row[2]:
        return Path.cwd()
    db_path = Path(row[2])
    return db_path.parent.parent.parent


def _canonical_json(event: dict) -> str:
    """Stable JSON for hashing -- sorted keys + minimal separators."""
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _derive_span_id(event: dict) -> str:
    explicit = event.get("span_id") or event.get("spanId")
    if isinstance(explicit, str) and explicit:
        return explicit
    digest = hashlib.sha256(_canonical_json(event).encode("utf-8")).hexdigest()
    return f"synthetic:{digest[:24]}"


def _columns_for_row(event: dict) -> tuple:
    """Map an event dict onto the events table columns."""
    span_id = _derive_span_id(event)
    detail = event.get("detail")
    detail_json = (
        json.dumps(detail, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if isinstance(detail, (dict, list))
        else "{}"
    )
    # spec-123 D-123-22: genai metadata may live at the event root or
    # nested under ``detail`` depending on whether the line was emitted
    # before or after the spec-120 schema rev. Check root first, fall
    # back to ``detail.genai``.
    root_genai = event.get("genai") if isinstance(event.get("genai"), dict) else None
    detail_genai = (
        detail.get("genai")
        if isinstance(detail, dict) and isinstance(detail.get("genai"), dict)
        else None
    )
    genai = root_genai or detail_genai or {}
    genai_system = genai.get("system") if isinstance(genai, dict) else None
    request = genai.get("request") if isinstance(genai, dict) else None
    genai_model = request.get("model") if isinstance(request, dict) else None
    usage = genai.get("usage") if isinstance(genai, dict) else None
    input_tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    output_tokens = usage.get("output_tokens") if isinstance(usage, dict) else None
    total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
    cost_usd = usage.get("cost_usd") if isinstance(usage, dict) else None

    return (
        span_id,
        event.get("trace_id") or event.get("traceId"),
        event.get("parent_span_id") or event.get("parentSpanId"),
        event.get("correlation_id") or event.get("correlationId"),
        event.get("session_id") or event.get("sessionId"),
        event.get("timestamp") or "",
        event.get("engine") or "unknown",
        event.get("kind") or "unknown",
        event.get("component") or "unknown",
        event.get("outcome") or "success",
        event.get("source"),
        event.get("prev_event_hash") or event.get("prevEventHash"),
        genai_system,
        genai_model,
        _int_or_none(input_tokens),
        _int_or_none(output_tokens),
        _int_or_none(total_tokens),
        _float_or_none(cost_usd),
        detail_json,
    )


def _int_or_none(value: object) -> int | None:
    """Coerce ``value`` to int when possible; otherwise None.

    Accepts integers and integral floats (e.g. ``150.0``). Booleans,
    strings, and non-integral floats become None to keep the column
    forensically clean.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    return None


def _float_or_none(value: object) -> float | None:
    """Coerce to float when possible; otherwise None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def apply(conn: sqlite3.Connection) -> None:
    """Replay every line of framework-events.ndjson into the events table."""
    project_root = _project_root_from_db(conn)
    ndjson_path = project_root / _NDJSON_REL
    if not ndjson_path.exists():
        return

    skipped = 0
    inserted = 0
    with ndjson_path.open("rb") as fh:
        for raw in fh:
            line = raw.rstrip(b"\n").rstrip(b"\r")
            if not line:
                continue
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError:
                skipped += 1
                sys.stderr.write(f"replay_ndjson: skipping non-UTF-8 line ({len(line)} bytes)\n")
                continue
            try:
                event = json.loads(text)
            except json.JSONDecodeError as exc:
                skipped += 1
                sys.stderr.write(f"replay_ndjson: skipping malformed line: {exc.msg}\n")
                continue
            if not isinstance(event, dict):
                skipped += 1
                continue
            try:
                columns = _columns_for_row(event)
                conn.execute(_INSERT, columns)
                inserted += 1
            except Exception as exc:  # pragma: no cover -- defensive
                skipped += 1
                sys.stderr.write(f"replay_ndjson: insert failed: {exc}\n")

    if skipped:
        sys.stderr.write(f"replay_ndjson: inserted={inserted} skipped={skipped}\n")


__all__ = ["BODY_SHA256", "apply"]
