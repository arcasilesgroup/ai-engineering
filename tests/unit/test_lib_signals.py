"""Tests for ai_engineering.lib.signals — NDJSON signal read/write/query.

Covers:
- audit_log_path: canonical path construction.
- load_all_events: missing file, empty file, valid NDJSON, corrupt lines,
  blank lines, whitespace handling.
- filter_events: by event_type, since timestamp, limit, combined filters,
  newest-first ordering, invalid timestamps, missing timestamp fields.
- read_events: convenience wrapper delegates correctly.
- _extract_timestamps: valid, invalid, missing, non-string timestamps.
- event_date_range_from / event_date_range: empty, single, multiple events.
- data_quality_from / data_quality_level: LOW/MEDIUM/HIGH thresholds.
- count_events: total count with and without date filtering.
- gate_pass_rate_from / gate_pass_rate: pass/fail counting, most_failed_check
  aggregation, empty gate events, zero-total division safety.
- _detail_field: dict detail, non-dict detail, missing detail.

All I/O uses tmp_path — no real audit-log files touched.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ai_engineering.lib.signals import (
    AUDIT_LOG_REL,
    _detail_field,
    _extract_timestamps,
    audit_log_path,
    count_events,
    data_quality_from,
    data_quality_level,
    event_date_range,
    event_date_range_from,
    filter_events,
    gate_pass_rate,
    gate_pass_rate_from,
    load_all_events,
    read_events,
)

pytestmark = pytest.mark.unit


# ── Helpers ──────────────────────────────────────────────────────────────


def _write_ndjson(path: Path, events: list[dict[str, Any]]) -> None:
    """Write a list of event dicts as NDJSON to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e) for e in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_event(
    event_type: str = "test",
    timestamp: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal event dict."""
    ev: dict[str, Any] = {"event": event_type}
    if timestamp is not None:
        ev["timestamp"] = timestamp
    if detail is not None:
        ev["detail"] = detail
    return ev


def _iso(dt: datetime) -> str:
    """Format a datetime to ISO 8601 with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _setup_audit_log(tmp_path: Path, events: list[dict[str, Any]]) -> Path:
    """Create an audit-log.ndjson under the standard project path."""
    log_path = audit_log_path(tmp_path)
    _write_ndjson(log_path, events)
    return log_path


# ── audit_log_path ───────────────────────────────────────────────────────


class TestAuditLogPath:
    """Tests for audit_log_path."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        result = audit_log_path(tmp_path)
        expected = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        assert result == expected

    def test_uses_module_constant(self, tmp_path: Path) -> None:
        result = audit_log_path(tmp_path)
        assert result == tmp_path / AUDIT_LOG_REL


# ── load_all_events ──────────────────────────────────────────────────────


class TestLoadAllEvents:
    """Tests for load_all_events."""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        events = load_all_events(tmp_path)
        assert events == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        log_path = audit_log_path(tmp_path)
        log_path.parent.mkdir(parents=True)
        log_path.write_text("", encoding="utf-8")
        events = load_all_events(tmp_path)
        assert events == []

    def test_whitespace_only_file_returns_empty(self, tmp_path: Path) -> None:
        log_path = audit_log_path(tmp_path)
        log_path.parent.mkdir(parents=True)
        log_path.write_text("   \n  \n   \n", encoding="utf-8")
        events = load_all_events(tmp_path)
        assert events == []

    def test_valid_ndjson(self, tmp_path: Path) -> None:
        entries = [
            {"event": "install", "actor": "agent"},
            {"event": "build", "actor": "agent"},
        ]
        _setup_audit_log(tmp_path, entries)
        events = load_all_events(tmp_path)
        assert len(events) == 2
        assert events[0]["event"] == "install"
        assert events[1]["event"] == "build"

    def test_preserves_file_order(self, tmp_path: Path) -> None:
        entries = [{"event": f"event-{i}", "seq": i} for i in range(5)]
        _setup_audit_log(tmp_path, entries)
        events = load_all_events(tmp_path)
        for i, ev in enumerate(events):
            assert ev["seq"] == i

    def test_corrupt_lines_skipped(self, tmp_path: Path) -> None:
        log_path = audit_log_path(tmp_path)
        log_path.parent.mkdir(parents=True)
        lines = [
            '{"event": "good1"}',
            "this is not json",
            '{"event": "good2"}',
            "{bad json",
            '{"event": "good3"}',
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        events = load_all_events(tmp_path)
        assert len(events) == 3
        assert events[0]["event"] == "good1"
        assert events[1]["event"] == "good2"
        assert events[2]["event"] == "good3"

    def test_blank_lines_between_entries_skipped(self, tmp_path: Path) -> None:
        log_path = audit_log_path(tmp_path)
        log_path.parent.mkdir(parents=True)
        lines = [
            '{"event": "a"}',
            "",
            '{"event": "b"}',
            "   ",
            '{"event": "c"}',
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        events = load_all_events(tmp_path)
        assert len(events) == 3

    def test_single_event(self, tmp_path: Path) -> None:
        _setup_audit_log(tmp_path, [{"event": "solo"}])
        events = load_all_events(tmp_path)
        assert len(events) == 1
        assert events[0]["event"] == "solo"


# ── filter_events ────────────────────────────────────────────────────────


class TestFilterEvents:
    """Tests for filter_events (in-memory, no I/O)."""

    def test_no_filters_returns_all_reversed(self) -> None:
        events = [_make_event("a"), _make_event("b"), _make_event("c")]
        result = filter_events(events)
        assert len(result) == 3
        # Newest first means reversed from file order
        assert result[0]["event"] == "c"
        assert result[2]["event"] == "a"

    def test_filter_by_event_type(self) -> None:
        events = [
            _make_event("gate_result"),
            _make_event("build"),
            _make_event("gate_result"),
            _make_event("deploy"),
        ]
        result = filter_events(events, event_type="gate_result")
        assert len(result) == 2
        assert all(e["event"] == "gate_result" for e in result)

    def test_filter_by_event_type_no_match(self) -> None:
        events = [_make_event("build"), _make_event("deploy")]
        result = filter_events(events, event_type="nonexistent")
        assert result == []

    def test_filter_by_since(self) -> None:
        now = datetime.now(tz=UTC)
        old = now - timedelta(days=10)
        recent = now - timedelta(hours=1)

        events = [
            _make_event("a", timestamp=_iso(old)),
            _make_event("b", timestamp=_iso(recent)),
        ]
        since = now - timedelta(days=1)
        result = filter_events(events, since=since)
        assert len(result) == 1
        assert result[0]["event"] == "b"

    def test_filter_by_since_excludes_older(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("old", timestamp=_iso(now - timedelta(days=60))),
            _make_event("also-old", timestamp=_iso(now - timedelta(days=31))),
        ]
        since = now - timedelta(days=30)
        result = filter_events(events, since=since)
        assert result == []

    def test_limit_zero_returns_all(self) -> None:
        events = [_make_event(f"e{i}") for i in range(10)]
        result = filter_events(events, limit=0)
        assert len(result) == 10

    def test_limit_truncates(self) -> None:
        events = [_make_event(f"e{i}") for i in range(10)]
        result = filter_events(events, limit=3)
        assert len(result) == 3
        # Should be the 3 newest (i.e., last 3 from file order, reversed)
        assert result[0]["event"] == "e9"
        assert result[1]["event"] == "e8"
        assert result[2]["event"] == "e7"

    def test_limit_larger_than_events(self) -> None:
        events = [_make_event("x"), _make_event("y")]
        result = filter_events(events, limit=100)
        assert len(result) == 2

    def test_combined_type_and_since(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("build", timestamp=_iso(now - timedelta(days=5))),
            _make_event("gate_result", timestamp=_iso(now - timedelta(days=5))),
            _make_event("gate_result", timestamp=_iso(now - timedelta(hours=1))),
            _make_event("build", timestamp=_iso(now - timedelta(hours=1))),
        ]
        since = now - timedelta(days=1)
        result = filter_events(events, event_type="gate_result", since=since)
        assert len(result) == 1
        assert result[0]["event"] == "gate_result"

    def test_combined_type_since_and_limit(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("gate_result", timestamp=_iso(now - timedelta(hours=i)))
            for i in range(10, 0, -1)
        ]
        since = now - timedelta(days=1)
        result = filter_events(events, event_type="gate_result", since=since, limit=3)
        assert len(result) == 3

    def test_invalid_timestamp_skipped_when_since_set(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("a", timestamp="not-a-date"),
            _make_event("b", timestamp=_iso(now - timedelta(hours=1))),
        ]
        since = now - timedelta(days=1)
        result = filter_events(events, since=since)
        assert len(result) == 1
        assert result[0]["event"] == "b"

    def test_missing_timestamp_skipped_when_since_set(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            {"event": "no-ts"},  # no timestamp key
            _make_event("has-ts", timestamp=_iso(now - timedelta(hours=1))),
        ]
        since = now - timedelta(days=1)
        result = filter_events(events, since=since)
        assert len(result) == 1
        assert result[0]["event"] == "has-ts"

    def test_non_string_timestamp_skipped_when_since_set(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            {"event": "bad-ts", "timestamp": 12345},
            _make_event("ok", timestamp=_iso(now - timedelta(hours=1))),
        ]
        since = now - timedelta(days=1)
        result = filter_events(events, since=since)
        assert len(result) == 1
        assert result[0]["event"] == "ok"

    def test_z_suffix_timestamp_parsed(self) -> None:
        now = datetime.now(tz=UTC)
        ts = now - timedelta(hours=1)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        events = [_make_event("a", timestamp=ts_str)]
        since = now - timedelta(days=1)
        result = filter_events(events, since=since)
        assert len(result) == 1

    def test_offset_timestamp_parsed(self) -> None:
        now = datetime.now(tz=UTC)
        ts = now - timedelta(hours=1)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        events = [_make_event("a", timestamp=ts_str)]
        since = now - timedelta(days=1)
        result = filter_events(events, since=since)
        assert len(result) == 1

    def test_empty_events_list(self) -> None:
        result = filter_events([])
        assert result == []

    def test_event_type_none_does_not_filter(self) -> None:
        events = [_make_event("a"), _make_event("b")]
        result = filter_events(events, event_type=None)
        assert len(result) == 2


# ── read_events ──────────────────────────────────────────────────────────


class TestReadEvents:
    """Tests for read_events convenience wrapper."""

    def test_missing_file(self, tmp_path: Path) -> None:
        result = read_events(tmp_path)
        assert result == []

    def test_reads_and_filters(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_event("build", timestamp=_iso(now - timedelta(hours=2))),
            _make_event("gate_result", timestamp=_iso(now - timedelta(hours=1))),
        ]
        _setup_audit_log(tmp_path, entries)
        result = read_events(
            tmp_path,
            event_type="gate_result",
            since=now - timedelta(days=1),
        )
        assert len(result) == 1
        assert result[0]["event"] == "gate_result"

    def test_with_limit(self, tmp_path: Path) -> None:
        entries = [_make_event(f"e{i}") for i in range(10)]
        _setup_audit_log(tmp_path, entries)
        result = read_events(tmp_path, limit=2)
        assert len(result) == 2


# ── _extract_timestamps ─────────────────────────────────────────────────


class TestExtractTimestamps:
    """Tests for _extract_timestamps helper."""

    def test_valid_timestamps_extracted(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("a", timestamp=_iso(now - timedelta(hours=2))),
            _make_event("b", timestamp=_iso(now - timedelta(hours=1))),
        ]
        result = _extract_timestamps(events)
        assert len(result) == 2

    def test_invalid_timestamps_skipped(self) -> None:
        events = [
            _make_event("a", timestamp="not-a-date"),
            _make_event("b", timestamp="2025-01-01T00:00:00Z"),
        ]
        result = _extract_timestamps(events)
        assert len(result) == 1

    def test_missing_timestamps_skipped(self) -> None:
        events = [{"event": "no-ts"}, {"event": "also-no-ts"}]
        result = _extract_timestamps(events)
        assert result == []

    def test_non_string_timestamps_skipped(self) -> None:
        events = [
            {"event": "a", "timestamp": 12345},
            {"event": "b", "timestamp": None},
        ]
        result = _extract_timestamps(events)
        assert result == []

    def test_empty_events(self) -> None:
        result = _extract_timestamps([])
        assert result == []

    def test_z_suffix_replaced(self) -> None:
        events = [_make_event("a", timestamp="2025-06-15T12:00:00Z")]
        result = _extract_timestamps(events)
        assert len(result) == 1
        assert result[0].tzinfo is not None


# ── event_date_range_from / event_date_range ─────────────────────────────


class TestEventDateRange:
    """Tests for event_date_range_from and event_date_range."""

    def test_empty_events_returns_none_none(self) -> None:
        oldest, newest = event_date_range_from([])
        assert oldest is None
        assert newest is None

    def test_no_valid_timestamps_returns_none_none(self) -> None:
        events = [{"event": "a"}, {"event": "b", "timestamp": "bad"}]
        oldest, newest = event_date_range_from(events)
        assert oldest is None
        assert newest is None

    def test_single_event(self) -> None:
        ts = "2025-06-15T12:00:00Z"
        events = [_make_event("a", timestamp=ts)]
        oldest, newest = event_date_range_from(events)
        assert oldest is not None
        assert newest is not None
        assert oldest == newest

    def test_multiple_events_correct_range(self) -> None:
        now = datetime.now(tz=UTC)
        t1 = now - timedelta(days=30)
        t2 = now - timedelta(days=15)
        t3 = now - timedelta(days=1)
        events = [
            _make_event("a", timestamp=_iso(t1)),
            _make_event("b", timestamp=_iso(t2)),
            _make_event("c", timestamp=_iso(t3)),
        ]
        oldest, newest = event_date_range_from(events)
        assert oldest is not None
        assert newest is not None
        assert oldest < newest
        # oldest should be t1, newest should be t3
        assert oldest.day == t1.day
        assert newest.day == t3.day

    def test_event_date_range_reads_from_file(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_event("a", timestamp=_iso(now - timedelta(days=10))),
            _make_event("b", timestamp=_iso(now - timedelta(days=1))),
        ]
        _setup_audit_log(tmp_path, entries)
        oldest, newest = event_date_range(tmp_path)
        assert oldest is not None
        assert newest is not None
        assert oldest < newest

    def test_event_date_range_missing_file(self, tmp_path: Path) -> None:
        oldest, newest = event_date_range(tmp_path)
        assert oldest is None
        assert newest is None


# ── data_quality_from / data_quality_level ───────────────────────────────


class TestDataQuality:
    """Tests for data_quality_from and data_quality_level."""

    def test_empty_events_low(self) -> None:
        assert data_quality_from([]) == "LOW"

    def test_no_valid_timestamps_low(self) -> None:
        events = [{"event": "a"} for _ in range(600)]
        assert data_quality_from(events) == "LOW"

    def test_low_count_low_days(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("a", timestamp=_iso(now - timedelta(days=5))),
            _make_event("b", timestamp=_iso(now)),
        ]
        assert data_quality_from(events) == "LOW"

    def test_medium_threshold(self) -> None:
        now = datetime.now(tz=UTC)
        # 100 events, 14 days span — anchor first and last explicitly
        events = [_make_event("e", timestamp=_iso(now - timedelta(days=14)))]
        for i in range(98):
            ts = now - timedelta(days=13) + timedelta(hours=i * 3)
            events.append(_make_event("e", timestamp=_iso(ts)))
        events.append(_make_event("e", timestamp=_iso(now)))
        assert len(events) == 100
        assert data_quality_from(events) == "MEDIUM"

    def test_high_threshold(self) -> None:
        now = datetime.now(tz=UTC)
        # 500 events, 60 days span — anchor first and last explicitly
        events = [_make_event("e", timestamp=_iso(now - timedelta(days=60)))]
        for i in range(498):
            ts = now - timedelta(days=59) + timedelta(hours=i * 2)
            events.append(_make_event("e", timestamp=_iso(ts)))
        events.append(_make_event("e", timestamp=_iso(now)))
        assert len(events) == 500
        assert data_quality_from(events) == "HIGH"

    def test_many_events_but_short_span_not_high(self) -> None:
        now = datetime.now(tz=UTC)
        # 500 events but only 10 days span
        events = []
        for i in range(500):
            ts = now - timedelta(days=10) + timedelta(minutes=i * 20)
            events.append(_make_event("e", timestamp=_iso(ts)))
        # 500 events >= 500, but 10 days < 60 -> not HIGH
        # 500 events >= 100 and 10 days < 14 -> not MEDIUM
        assert data_quality_from(events) == "LOW"

    def test_many_events_medium_span(self) -> None:
        now = datetime.now(tz=UTC)
        # 500 events, 30 days span (>= 100 events, >= 14 days but < 60)
        events = []
        for i in range(500):
            ts = now - timedelta(days=30) + timedelta(hours=i)
            events.append(_make_event("e", timestamp=_iso(ts)))
        assert data_quality_from(events) == "MEDIUM"

    def test_few_events_long_span(self) -> None:
        now = datetime.now(tz=UTC)
        # 50 events, 90 days span (< 100 events)
        events = [
            _make_event("e", timestamp=_iso(now - timedelta(days=90))),
        ]
        for i in range(49):
            ts = now - timedelta(days=90 - i * 2)
            events.append(_make_event("e", timestamp=_iso(ts)))
        assert data_quality_from(events) == "LOW"

    def test_data_quality_level_reads_from_file(self, tmp_path: Path) -> None:
        result = data_quality_level(tmp_path)
        assert result == "LOW"

    def test_exact_medium_boundary(self) -> None:
        now = datetime.now(tz=UTC)
        # Exactly 100 events, exactly 14 days span
        events = [_make_event("e", timestamp=_iso(now - timedelta(days=14)))]
        for i in range(98):
            ts = now - timedelta(days=13) + timedelta(hours=i * 3)
            events.append(_make_event("e", timestamp=_iso(ts)))
        events.append(_make_event("e", timestamp=_iso(now)))
        assert len(events) == 100
        assert data_quality_from(events) == "MEDIUM"

    def test_exact_high_boundary(self) -> None:
        now = datetime.now(tz=UTC)
        # Exactly 500 events, exactly 60 days span
        events = [_make_event("e", timestamp=_iso(now - timedelta(days=60)))]
        for i in range(498):
            ts = now - timedelta(days=59) + timedelta(hours=i * 2)
            events.append(_make_event("e", timestamp=_iso(ts)))
        events.append(_make_event("e", timestamp=_iso(now)))
        assert len(events) == 500
        assert data_quality_from(events) == "HIGH"


# ── count_events ─────────────────────────────────────────────────────────


class TestCountEvents:
    """Tests for count_events."""

    def test_missing_file_returns_zero(self, tmp_path: Path) -> None:
        assert count_events(tmp_path) == 0

    def test_counts_all_events(self, tmp_path: Path) -> None:
        entries = [_make_event(f"e{i}") for i in range(7)]
        _setup_audit_log(tmp_path, entries)
        assert count_events(tmp_path) == 7

    def test_counts_with_since_filter(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_event("old", timestamp=_iso(now - timedelta(days=60))),
            _make_event("recent1", timestamp=_iso(now - timedelta(hours=2))),
            _make_event("recent2", timestamp=_iso(now - timedelta(hours=1))),
        ]
        _setup_audit_log(tmp_path, entries)
        count = count_events(tmp_path, since=now - timedelta(days=1))
        assert count == 2


# ── gate_pass_rate_from / gate_pass_rate ─────────────────────────────────


class TestGatePassRate:
    """Tests for gate_pass_rate_from and gate_pass_rate."""

    def test_no_gate_events(self) -> None:
        result = gate_pass_rate_from([])
        assert result["total"] == 0
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["pass_rate"] == 0.0
        assert result["most_failed_check"] == "none"
        assert result["most_failed_count"] == 0

    def test_all_pass(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=i)),
                detail={"result": "pass"},
            )
            for i in range(5)
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["total"] == 5
        assert result["passed"] == 5
        assert result["failed"] == 0
        assert result["pass_rate"] == 100.0
        assert result["most_failed_check"] == "none"

    def test_all_fail(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=i)),
                detail={"result": "fail", "failed_checks": ["lint"]},
            )
            for i in range(4)
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["total"] == 4
        assert result["passed"] == 0
        assert result["failed"] == 4
        assert result["pass_rate"] == 0.0
        assert result["most_failed_check"] == "lint"
        assert result["most_failed_count"] == 4

    def test_mixed_pass_fail(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=1)),
                detail={"result": "pass"},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=2)),
                detail={"result": "fail", "failed_checks": ["ruff-lint"]},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=3)),
                detail={"result": "fail", "failed_checks": ["ruff-lint", "gitleaks"]},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=4)),
                detail={"result": "pass"},
            ),
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["total"] == 4
        assert result["passed"] == 2
        assert result["failed"] == 2
        assert result["pass_rate"] == 50.0
        assert result["most_failed_check"] == "ruff-lint"
        assert result["most_failed_count"] == 2

    def test_most_failed_check_picks_highest(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=1)),
                detail={"result": "fail", "failed_checks": ["lint", "test"]},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=2)),
                detail={"result": "fail", "failed_checks": ["test"]},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=3)),
                detail={"result": "fail", "failed_checks": ["test", "format"]},
            ),
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["most_failed_check"] == "test"
        assert result["most_failed_count"] == 3

    def test_old_events_excluded_by_days(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(days=60)),
                detail={"result": "fail", "failed_checks": ["old-check"]},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=1)),
                detail={"result": "pass"},
            ),
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["total"] == 1
        assert result["passed"] == 1
        assert result["most_failed_check"] == "none"

    def test_non_gate_events_excluded(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event("build", timestamp=_iso(now - timedelta(hours=1))),
            _make_event("deploy", timestamp=_iso(now - timedelta(hours=2))),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=3)),
                detail={"result": "pass"},
            ),
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["total"] == 1

    def test_detail_not_dict_no_failed_checks(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=1)),
                detail={"result": "fail"},
            ),
            {
                "event": "gate_result",
                "timestamp": _iso(now - timedelta(hours=2)),
                "detail": "string-detail",
            },
        ]
        result = gate_pass_rate_from(events, days=30)
        # The string-detail event has no "result" field via _detail_field -> not "pass"
        assert result["total"] == 2
        assert result["failed"] == 2
        assert result["most_failed_check"] == "none"

    def test_gate_pass_rate_reads_from_file(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        entries = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=1)),
                detail={"result": "pass"},
            ),
        ]
        _setup_audit_log(tmp_path, entries)
        result = gate_pass_rate(tmp_path, days=30)
        assert result["total"] == 1
        assert result["passed"] == 1

    def test_gate_pass_rate_missing_file(self, tmp_path: Path) -> None:
        result = gate_pass_rate(tmp_path, days=30)
        assert result["total"] == 0
        assert result["pass_rate"] == 0.0

    def test_custom_days_parameter(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(days=5)),
                detail={"result": "pass"},
            ),
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(days=15)),
                detail={"result": "fail", "failed_checks": ["check"]},
            ),
        ]
        result_7 = gate_pass_rate_from(events, days=7)
        assert result_7["total"] == 1
        assert result_7["passed"] == 1

        result_30 = gate_pass_rate_from(events, days=30)
        assert result_30["total"] == 2

    def test_pass_rate_rounding(self) -> None:
        now = datetime.now(tz=UTC)
        events = [
            _make_event(
                "gate_result",
                timestamp=_iso(now - timedelta(hours=i)),
                detail={"result": "pass" if i < 2 else "fail"},
            )
            for i in range(3)
        ]
        result = gate_pass_rate_from(events, days=30)
        assert result["total"] == 3
        assert result["passed"] == 2
        # 2/3 * 100 = 66.666... -> 66.7
        assert result["pass_rate"] == 66.7


# ── _detail_field ────────────────────────────────────────────────────────


class TestDetailField:
    """Tests for _detail_field helper."""

    def test_dict_detail_returns_field(self) -> None:
        event = {"detail": {"result": "pass", "score": 42}}
        assert _detail_field(event, "result") == "pass"
        assert _detail_field(event, "score") == 42

    def test_dict_detail_missing_field_returns_none(self) -> None:
        event = {"detail": {"result": "pass"}}
        assert _detail_field(event, "nonexistent") is None

    def test_non_dict_detail_returns_none(self) -> None:
        event = {"detail": "just a string"}
        assert _detail_field(event, "result") is None

    def test_missing_detail_returns_none(self) -> None:
        event = {"event": "test"}
        assert _detail_field(event, "result") is None

    def test_none_detail_returns_none(self) -> None:
        event = {"detail": None}
        assert _detail_field(event, "result") is None

    def test_list_detail_returns_none(self) -> None:
        event = {"detail": ["a", "b", "c"]}
        assert _detail_field(event, "result") is None

    def test_numeric_detail_returns_none(self) -> None:
        event = {"detail": 42}
        assert _detail_field(event, "result") is None

    def test_empty_dict_detail_returns_none(self) -> None:
        event = {"detail": {}}
        assert _detail_field(event, "result") is None
