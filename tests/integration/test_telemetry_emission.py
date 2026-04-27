"""RED skeleton for spec-105 Phase 2 — telemetry event structure.

Covers spec-105 G-11: every risk-acceptance flow emits a canonical
`framework_event` with shape `{category=risk-acceptance, control=<verb>, metadata=...}`.

Status: RED (emission code does not exist; events file empty after invocation).
Marker: `@pytest.mark.spec_105_red` — excluded by default CI run.
Will be unmarked in Phase 2 (no specific task — the body lives in this skeleton
once the lookup module emits via `emit_control_outcome`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def test_risk_acceptance_emits_canonical_framework_event(tmp_path: Path) -> None:
    """Accepting a finding emits one event with category=risk-acceptance."""
    # Will be filled in Phase 2 once apply_risk_acceptances is wired.
    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")

    # Trigger a risk acceptance — placeholder until module exists.
    raise NotImplementedError("Phase 2 will implement telemetry trigger")


def test_accept_all_emits_batch_event_with_dec_count(tmp_path: Path) -> None:
    """Bulk accept emits one batch event including `dec_count` and `batch_id` metadata."""
    raise NotImplementedError("Phase 2 will implement batch telemetry trigger")


def test_telemetry_event_includes_finding_metadata(tmp_path: Path) -> None:
    """Per-finding telemetry includes rule_id, severity, dec_id, expires_at."""
    raise NotImplementedError("Phase 2 will populate metadata fields")


def test_telemetry_event_well_formed_json_lines(tmp_path: Path) -> None:
    """Each line in framework-events.ndjson is valid JSON with mandatory keys."""
    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")

    # After Phase 2, an event will be written; for now this proves the contract.
    lines = [ln for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) > 0, "Expected at least one telemetry event"
    for line in lines:
        event = json.loads(line)
        assert "category" in event
        assert "control" in event
        assert event["category"] == "risk-acceptance"
