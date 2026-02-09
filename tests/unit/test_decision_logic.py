"""Unit tests for decision reuse logic."""

from __future__ import annotations

from ai_engineering.state.decision_logic import evaluate_reuse
from ai_engineering.state.models import (
    DecisionRecord,
    DecisionScope,
    DecisionStore,
    UpdateMetadata,
)


def _store_with(record: DecisionRecord) -> DecisionStore:
    return DecisionStore(
        updateMetadata=UpdateMetadata(
            rationale="test",
            expectedGain="test",
            potentialImpact="test",
        ),
        decisions=[record],
    )


def test_evaluate_reuse_reports_material_context_change() -> None:
    record = DecisionRecord(
        id="1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1"),
        contextHash="sha256:old",
        severity="medium",
        decision="defer-pr",
        rationale="test",
        createdAt="2026-02-09T00:00:00Z",
    )
    result = evaluate_reuse(
        _store_with(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:new",
        severity="medium",
    )
    assert not result.reusable
    assert result.reason == "material_context_hash_changed"


def test_evaluate_reuse_reports_severity_change() -> None:
    record = DecisionRecord(
        id="1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1"),
        contextHash="sha256:same",
        severity="low",
        decision="accept",
        rationale="test",
        createdAt="2026-02-09T00:00:00Z",
    )
    result = evaluate_reuse(
        _store_with(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:same",
        severity="high",
    )
    assert not result.reusable
    assert result.reason == "severity_changed"


def test_evaluate_reuse_reports_scope_change() -> None:
    record = DecisionRecord(
        id="1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1", pathPattern="src/**"),
        contextHash="sha256:same",
        severity="medium",
        decision="accept",
        rationale="test",
        createdAt="2026-02-09T00:00:00Z",
    )
    result = evaluate_reuse(
        _store_with(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:same",
        severity="medium",
        path_pattern="tests/**",
    )
    assert not result.reusable
    assert result.reason == "scope_changed"


def test_evaluate_reuse_reuses_when_inputs_match() -> None:
    record = DecisionRecord(
        id="1",
        scope=DecisionScope(repo="ai-engineering", policyId="P1"),
        contextHash="sha256:same",
        severity="medium",
        decision="defer-pr",
        rationale="test",
        createdAt="2026-02-09T00:00:00Z",
    )
    result = evaluate_reuse(
        _store_with(record),
        policy_id="P1",
        repo_name="ai-engineering",
        context_hash_value="sha256:same",
        severity="medium",
        expected_decision="defer-pr",
    )
    assert result.reusable
    assert result.reason == "reused"
