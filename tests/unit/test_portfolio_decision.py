"""Tests for portfolio decision records (spec-199 T-4)."""

from __future__ import annotations

import json

import pytest

from ai_engineering.portfolio.decision import emit_decision


class TestDecisionRecord:
    """DecisionRecord tests."""

    def test_create_decision(self):
        record = emit_decision(
            candidate_name="gh",
            decision="adopt",
            rationale="Well-established GitHub CLI",
            evidence=["installed", "authenticated"],
        )
        assert record.candidate_name == "gh"
        assert record.decision == "adopt"

    def test_to_json(self):
        record = emit_decision(
            candidate_name="test",
            decision="reject",
            rationale="Not installed",
            evidence=["binary not found"],
        )
        json_str = record.to_json()
        parsed = json.loads(json_str)
        assert parsed["candidate_name"] == "test"
        assert parsed["decision"] == "reject"

    def test_invalid_decision(self):
        with pytest.raises(ValueError):
            emit_decision(
                candidate_name="test",
                decision="invalid",
                rationale="test",
                evidence=[],
            )

    def test_all_valid_decisions(self):
        for decision in ["adopt", "adapt", "reject", "blocked"]:
            record = emit_decision(
                candidate_name="test",
                decision=decision,
                rationale="test",
                evidence=[],
            )
            assert record.decision == decision

    def test_pilot_brief(self):
        record = emit_decision(
            candidate_name="gh",
            decision="adopt",
            rationale="test",
            evidence=[],
            pilot_brief=".ai-engineering/specs/drafts/pilot-gh-brief.md",
        )
        assert record.pilot_brief == ".ai-engineering/specs/drafts/pilot-gh-brief.md"
