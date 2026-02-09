"""Unit tests for decision reuse rules."""

from __future__ import annotations

from ai_engineering.state.decision_logic import evaluate_reuse
from ai_engineering.state.models import DecisionRecord, DecisionScope, DecisionStore, UpdateMetadata


def _store(record: DecisionRecord) -> DecisionStore:
    return DecisionStore(
        updateMetadata=UpdateMetadata(
            rationale="test",
            expectedGain="test",
            potentialImpact="test",
        ),
        decisions=[record],
    )


def test_evaluate_reuse_reports_policy_changed() -> None:
    record = DecisionRecord(
        id="d1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1", policyVersion="1"),
        contextHash="sha256:same",
        severity="medium",
        decision="accept",
        rationale="test",
        createdAt="2026-02-10T00:00:00Z",
    )
    result = evaluate_reuse(
        _store(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:same",
        severity="medium",
        policy_version="2",
    )
    assert result.reusable is False
    assert result.reason == "policy_changed"


def test_evaluate_reuse_reports_context_change() -> None:
    record = DecisionRecord(
        id="d1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1", policyVersion="1"),
        contextHash="sha256:old",
        severity="medium",
        decision="accept",
        rationale="test",
        createdAt="2026-02-10T00:00:00Z",
    )
    result = evaluate_reuse(
        _store(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:new",
        severity="medium",
        policy_version="1",
    )
    assert result.reusable is False
    assert result.reason == "material_context_hash_changed"


def test_evaluate_reuse_is_reused_when_all_match() -> None:
    record = DecisionRecord(
        id="d1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1", policyVersion="1"),
        contextHash="sha256:same",
        severity="high",
        decision="defer-pr",
        rationale="test",
        createdAt="2026-02-10T00:00:00Z",
    )
    result = evaluate_reuse(
        _store(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:same",
        severity="high",
        policy_version="1",
        expected_decision="defer-pr",
    )
    assert result.reusable is True
    assert result.reason == "reused"
