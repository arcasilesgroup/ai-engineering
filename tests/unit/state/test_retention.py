"""Tests for the 90-day HOT retention cutoff (spec-123 T-3.8 / D-123-26).

The retention module enforces the per-tier window from D-123-26:

  HOT (state.db events table)   90 days
  WARM (NDJSON archive plain)   12 months
  COLD (zstd archive)           24 months
  PURGE                         > 24 months

This test suite covers the HOT tier only -- the warm/cold cutoffs are
exercised by :mod:`test_compress` and the rotation manifest tests.

Public surface
--------------
* :func:`retention.apply_hot_cutoff(conn, days=90)` -- delete events whose
  ``ts_unix_ms`` is older than ``now - days * 86400_000``. The audit
  retains the original lines via the NDJSON archive (already covered by
  rotation), so deletion is loss-free.
* On non-zero deletions, the module emits a ``framework_event`` with
  ``kind='retention_applied'`` so the audit chain records the prune.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from ai_engineering.state import state_db
from ai_engineering.state.retention import apply_hot_cutoff

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Tmp project root with a bootstrapped state.db."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _insert_event(conn, *, span_id: str, ts_iso: str) -> None:
    conn.execute(
        """
        INSERT INTO events
          (span_id, trace_id, parent_span_id, correlation_id, session_id,
           timestamp, engine, kind, component, outcome, source,
           prev_event_hash, genai_system, genai_model,
           input_tokens, output_tokens, total_tokens, cost_usd, detail_json)
        VALUES (?, NULL, NULL, NULL, NULL, ?, 'claude_code', 'tool_invoked',
                'test', 'success', NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL, '{}')
        """,
        (span_id, ts_iso),
    )


def _ms_now() -> int:
    return int(time.time() * 1000)


def _iso_for_offset_days(days_back: int) -> str:
    """Return an ISO-8601 UTC timestamp ``days_back`` days before now."""
    from datetime import UTC, datetime, timedelta

    when = datetime.now(tz=UTC) - timedelta(days=days_back)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# T-3.8 — RED + GREEN: 90-day HOT cutoff
# ---------------------------------------------------------------------------


class TestApplyHotCutoff:
    """``apply_hot_cutoff`` deletes events older than the cutoff."""

    def test_old_events_deleted_kept_within_cutoff(self, project_root: Path) -> None:
        """Events older than 90d go; events within 90d stay."""
        conn = state_db.connect(project_root)
        try:
            # Insert 3 events: one 200d old, one 30d old, one 1d old.
            _insert_event(conn, span_id="old-1", ts_iso=_iso_for_offset_days(200))
            _insert_event(conn, span_id="mid-1", ts_iso=_iso_for_offset_days(30))
            _insert_event(conn, span_id="new-1", ts_iso=_iso_for_offset_days(1))
            conn.commit()
            assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 3

            verdict = apply_hot_cutoff(conn, days=90)

            remaining = {row[0] for row in conn.execute("SELECT span_id FROM events").fetchall()}
            assert remaining == {"mid-1", "new-1"}
            assert verdict["deleted"] == 1
            assert verdict["cutoff_days"] == 90
        finally:
            conn.close()

    def test_zero_deletions_when_all_recent(self, project_root: Path) -> None:
        """With no old events, the cutoff is a no-op."""
        conn = state_db.connect(project_root)
        try:
            _insert_event(conn, span_id="rec-1", ts_iso=_iso_for_offset_days(2))
            _insert_event(conn, span_id="rec-2", ts_iso=_iso_for_offset_days(5))
            conn.commit()

            verdict = apply_hot_cutoff(conn, days=90)

            assert verdict["deleted"] == 0
            assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 2
        finally:
            conn.close()

    def test_emits_framework_event_on_deletion(self, project_root: Path) -> None:
        """Non-zero deletions emit a ``retention_applied`` framework event."""
        conn = state_db.connect(project_root)
        try:
            _insert_event(conn, span_id="drop-1", ts_iso=_iso_for_offset_days(120))
            conn.commit()

            apply_hot_cutoff(conn, days=90)
        finally:
            conn.close()

        ndjson = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
        assert ndjson.exists(), "expected framework-events.ndjson to be created"
        lines = [
            json.loads(line)
            for line in ndjson.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        kinds = [event.get("kind") for event in lines]
        assert "retention_applied" in kinds, kinds
        retention_events = [event for event in lines if event.get("kind") == "retention_applied"]
        assert retention_events, "no retention_applied event emitted"
        detail = retention_events[-1].get("detail") or {}
        assert detail.get("deleted") == 1
        assert detail.get("cutoff_days") == 90

    def test_no_event_on_zero_deletions(self, project_root: Path) -> None:
        """Zero-deletion calls do NOT spam the audit log."""
        conn = state_db.connect(project_root)
        try:
            _insert_event(conn, span_id="rec-only", ts_iso=_iso_for_offset_days(1))
            conn.commit()

            apply_hot_cutoff(conn, days=90)
        finally:
            conn.close()

        ndjson = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
        if not ndjson.exists():
            return  # no events emitted at all -- acceptable
        events = [
            json.loads(line)
            for line in ndjson.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        retention_events = [event for event in events if event.get("kind") == "retention_applied"]
        assert not retention_events, "retention_applied emitted on zero deletions"
