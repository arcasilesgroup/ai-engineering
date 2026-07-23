"""Tests for session ticket generator (spec-196 T-4/T-5)."""

from __future__ import annotations

import json

from ai_engineering.bootstrap.ticket import (
    _classify_risk,
    _recommend_workflow,
    generate_ticket,
)


class TestSessionTicket:
    """SessionTicket dataclass tests."""

    def test_to_json_roundtrip(self):
        ticket = generate_ticket(task_type="bug", changed_paths=["src/foo.py"])
        json_str = ticket.to_json()
        restored = json.loads(json_str)
        assert restored["task_type"] == "bug"
        assert restored["risk_level"] == "low"

    def test_truncate_to_budget(self):
        ticket = generate_ticket(task_type="bug")
        truncated = ticket.truncate_to_budget(max_bytes=200)
        assert len(truncated.encode("utf-8")) <= 200
        parsed = json.loads(truncated)
        assert "truncated" in parsed

    def test_deterministic_hash(self):
        ticket1 = generate_ticket(task_type="bug", changed_paths=["a.py"])
        ticket2 = generate_ticket(task_type="bug", changed_paths=["a.py"])
        assert ticket1.ticket_hash == ticket2.ticket_hash

    def test_different_paths_different_hash(self):
        ticket1 = generate_ticket(task_type="bug", changed_paths=["a.py"])
        ticket2 = generate_ticket(task_type="bug", changed_paths=["b.py"])
        assert ticket1.ticket_hash != ticket2.ticket_hash


class TestRiskClassification:
    """Risk classification tests."""

    def test_low_risk(self):
        assert _classify_risk(["src/foo.py"]) == "low"

    def test_medium_risk(self):
        assert _classify_risk(["config/settings.yaml"]) == "medium"

    def test_high_risk(self):
        assert _classify_risk(["src/auth/credential.py"]) == "high"


class TestWorkflowRecommendation:
    """Workflow recommendation tests."""

    def test_bug_low(self):
        assert _recommend_workflow("bug", "low") == "/ai-debug"

    def test_feature_medium(self):
        assert _recommend_workflow("feature", "medium") == "/ai-build"

    def test_security_high(self):
        assert _recommend_workflow("security", "high") == "/ai-security"

    def test_unknown_defaults(self):
        assert _recommend_workflow("unknown", "low") == "/ai-brainstorm"


class TestGenerateTicket:
    """Integration tests for ticket generation."""

    def test_default_ticket(self):
        ticket = generate_ticket()
        assert ticket.task_type == "general"
        assert ticket.risk_level == "low"
        assert ticket.context_budget_tokens == 500

    def test_high_risk_includes_security(self):
        ticket = generate_ticket(
            task_type="security",
            changed_paths=["src/auth/secret.py"],
        )
        assert ticket.risk_level == "high"
        assert "SECURITY.md" in ticket.includes

    def test_ticket_stays_under_budget(self):
        ticket = generate_ticket(
            task_type="feature",
            changed_paths=[f"file{i}.py" for i in range(50)],
        )
        json_str = ticket.to_json()
        assert len(json_str.encode("utf-8")) <= 8192  # well under 2 KiB
