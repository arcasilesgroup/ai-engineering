"""GREEN tests for spec-105 additive Decision fields (`finding_id`, `batch_id`).

Covers:
- Pydantic round-trip with new fields populated.
- Pydantic round-trip with new fields None (default).
- Backward-compat: reading legacy decision-store fixture (no new fields) succeeds
  and yields default-None values for `finding_id` and `batch_id`.
- Alias support (camelCase): `findingId`/`batchId` accepted as input.

This file MUST stay GREEN immediately (no `spec_105_red` marker).
Mitigates spec-105 R-6 (legacy DEC read regression).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_engineering.state.models import (
    Decision,
    DecisionStatus,
    DecisionStore,
    RiskCategory,
    RiskSeverity,
)

FIXTURE_LEGACY = (
    Path(__file__).parent.parent / "fixtures" / "decision_store_legacy_pre_spec105.json"
)


@pytest.mark.unit
def test_decision_round_trip_with_new_fields_populated() -> None:
    """A Decision with `finding_id` + `batch_id` populated round-trips losslessly."""
    payload = {
        "id": "DEC-2026-100",
        "context": "finding:ruff/E501",
        "decision": "Accept; refactoring scheduled.",
        "decidedAt": "2026-04-27T12:00:00Z",
        "spec": "spec-105",
        "riskCategory": "risk-acceptance",
        "severity": "low",
        "acceptedBy": "team-platform",
        "followUpAction": "Refactor in next sprint.",
        "status": "active",
        "findingId": "ruff/E501:src/long.py:120",
        "batchId": "550e8400-e29b-41d4-a716-446655440000",
    }

    decision = Decision.model_validate(payload)

    assert decision.finding_id == "ruff/E501:src/long.py:120"
    assert decision.batch_id == "550e8400-e29b-41d4-a716-446655440000"
    assert decision.risk_category == RiskCategory.RISK_ACCEPTANCE
    assert decision.severity == RiskSeverity.LOW
    assert decision.status == DecisionStatus.ACTIVE

    # Round-trip: serialize back via aliases and re-parse — values preserved.
    dumped = decision.model_dump(by_alias=True)
    assert dumped["findingId"] == "ruff/E501:src/long.py:120"
    assert dumped["batchId"] == "550e8400-e29b-41d4-a716-446655440000"

    redecided = Decision.model_validate(dumped)
    assert redecided.finding_id == decision.finding_id
    assert redecided.batch_id == decision.batch_id


@pytest.mark.unit
def test_decision_round_trip_with_new_fields_none_by_default() -> None:
    """Omitting `finding_id` and `batch_id` yields None defaults (additive contract)."""
    payload = {
        "id": "DEC-2026-101",
        "context": "flow:override",
        "decision": "Permit fast-forward only.",
        "decidedAt": "2026-04-27T12:30:00Z",
        "spec": "spec-105",
        "riskCategory": "flow-decision",
        "status": "active",
    }

    decision = Decision.model_validate(payload)

    assert decision.finding_id is None
    assert decision.batch_id is None

    dumped = decision.model_dump(by_alias=True)
    # Optional fields with None default are still emitted (pydantic default).
    assert dumped.get("findingId") is None
    assert dumped.get("batchId") is None

    redecided = Decision.model_validate(dumped)
    assert redecided.finding_id is None
    assert redecided.batch_id is None


@pytest.mark.unit
def test_decision_accepts_snake_case_input() -> None:
    """`populate_by_name=True` allows snake_case input keys for both new fields."""
    payload = {
        "id": "DEC-2026-102",
        "context": "finding:semgrep/exec",
        "decision": "Accept; sandboxed.",
        "decided_at": "2026-04-27T13:00:00Z",  # snake_case
        "spec": "spec-105",
        "risk_category": "risk-acceptance",  # snake_case
        "status": "active",
        "finding_id": "semgrep/exec:src/loader.py:7",  # snake_case
        "batch_id": "batch-xyz",  # snake_case
    }

    decision = Decision.model_validate(payload)

    assert decision.finding_id == "semgrep/exec:src/loader.py:7"
    assert decision.batch_id == "batch-xyz"
    assert decision.decided_at == datetime(2026, 4, 27, 13, 0, tzinfo=UTC)


@pytest.mark.unit
def test_legacy_decision_store_fixture_reads_without_new_fields() -> None:
    """Pre-spec-105 decision-store fixture reads cleanly; new fields default to None.

    Mitigates spec-105 R-6: confirms backward compatibility with existing
    decision-store entries that lack `finding_id`/`batch_id`.
    """
    assert FIXTURE_LEGACY.exists(), f"Missing fixture: {FIXTURE_LEGACY}"

    raw = json.loads(FIXTURE_LEGACY.read_text(encoding="utf-8"))
    store = DecisionStore.model_validate(raw)

    assert store.schema_version == "1.1"
    assert len(store.decisions) == 3

    # Every legacy entry MUST have new fields default to None — additive guarantee.
    for dec in store.decisions:
        assert dec.finding_id is None, f"{dec.id} unexpectedly populated finding_id"
        assert dec.batch_id is None, f"{dec.id} unexpectedly populated batch_id"

    # Spot-check: existing schema-1.1 fields still parse correctly.
    dec_001 = store.find_by_id("DEC-2026-001")
    assert dec_001 is not None
    assert dec_001.risk_category == RiskCategory.RISK_ACCEPTANCE
    assert dec_001.severity == RiskSeverity.HIGH
    assert dec_001.accepted_by == "team-platform"

    dec_002 = store.find_by_id("DEC-2026-002")
    assert dec_002 is not None
    assert dec_002.risk_category == RiskCategory.FLOW_DECISION
    assert dec_002.severity is None  # not set on flow decisions

    dec_003 = store.find_by_id("DEC-2026-003")
    assert dec_003 is not None
    assert dec_003.severity == RiskSeverity.MEDIUM


@pytest.mark.unit
def test_legacy_store_round_trips_through_dump() -> None:
    """Legacy store → load → dump → reload preserves all values; new fields stay None."""
    raw = json.loads(FIXTURE_LEGACY.read_text(encoding="utf-8"))
    store = DecisionStore.model_validate(raw)

    dumped = store.model_dump(by_alias=True)
    reloaded = DecisionStore.model_validate(dumped)

    assert len(reloaded.decisions) == len(store.decisions)
    for original, reloaded_dec in zip(store.decisions, reloaded.decisions, strict=True):
        assert reloaded_dec.id == original.id
        assert reloaded_dec.finding_id is None
        assert reloaded_dec.batch_id is None
