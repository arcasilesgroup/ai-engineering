"""Unit tests for spec-044: skill & agent telemetry aggregators and dashboard wiring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.lib.signals import agent_dispatch_from, skill_usage_from

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(days_ago: int = 0) -> str:
    dt = datetime.now(tz=UTC) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _skill_event(name: str, days_ago: int = 0) -> dict:
    return {
        "timestamp": _ts(days_ago),
        "event": "skill_invoked",
        "actor": "ai",
        "detail": {"skill": name},
    }


def _agent_event(name: str, days_ago: int = 0) -> dict:
    return {
        "timestamp": _ts(days_ago),
        "event": "agent_dispatched",
        "actor": "ai",
        "detail": {"agent": name},
    }


# ---------------------------------------------------------------------------
# skill_usage_from
# ---------------------------------------------------------------------------


class TestSkillUsageFrom:
    def test_empty_events(self) -> None:
        result = skill_usage_from([])
        assert result["total_invocations"] == 0
        assert result["by_skill"] == {}
        assert result["top_skill"] == "none"
        assert result["least_skill"] == "none"

    def test_single_skill(self) -> None:
        events = [_skill_event("build")]
        result = skill_usage_from(events)
        assert result["total_invocations"] == 1
        assert result["by_skill"] == {"build": 1}
        assert result["top_skill"] == "build"

    def test_multiple_skills_sorted(self) -> None:
        events = [
            _skill_event("build"),
            _skill_event("build"),
            _skill_event("build"),
            _skill_event("test"),
            _skill_event("test"),
            _skill_event("commit"),
        ]
        result = skill_usage_from(events)
        assert result["total_invocations"] == 6
        assert result["top_skill"] == "build"
        assert result["least_skill"] == "commit"
        keys = list(result["by_skill"].keys())
        assert keys == ["build", "test", "commit"]

    def test_respects_time_window(self) -> None:
        events = [
            _skill_event("build", days_ago=0),
            _skill_event("test", days_ago=60),  # outside 30-day window
        ]
        result = skill_usage_from(events, days=30)
        assert result["total_invocations"] == 1
        assert "test" not in result["by_skill"]

    def test_ignores_non_skill_events(self) -> None:
        events = [
            _skill_event("build"),
            {"timestamp": _ts(), "event": "gate_result", "detail": {"gate": "pre-commit"}},
        ]
        result = skill_usage_from(events)
        assert result["total_invocations"] == 1

    def test_handles_missing_detail_field(self) -> None:
        events = [
            {"timestamp": _ts(), "event": "skill_invoked", "detail": {}},
            {"timestamp": _ts(), "event": "skill_invoked", "detail": {"skill": ""}},
        ]
        result = skill_usage_from(events)
        assert result["total_invocations"] == 0


# ---------------------------------------------------------------------------
# agent_dispatch_from
# ---------------------------------------------------------------------------


class TestAgentDispatchFrom:
    def test_empty_events(self) -> None:
        result = agent_dispatch_from([])
        assert result["total_dispatches"] == 0
        assert result["by_agent"] == {}

    def test_single_agent(self) -> None:
        events = [_agent_event("build")]
        result = agent_dispatch_from(events)
        assert result["total_dispatches"] == 1
        assert result["by_agent"] == {"build": 1}

    def test_multiple_agents_sorted(self) -> None:
        events = [
            _agent_event("build"),
            _agent_event("build"),
            _agent_event("scan"),
            _agent_event("plan"),
            _agent_event("plan"),
            _agent_event("plan"),
        ]
        result = agent_dispatch_from(events)
        assert result["total_dispatches"] == 6
        keys = list(result["by_agent"].keys())
        assert keys == ["plan", "build", "scan"]

    def test_respects_time_window(self) -> None:
        events = [
            _agent_event("build", days_ago=0),
            _agent_event("scan", days_ago=60),
        ]
        result = agent_dispatch_from(events, days=30)
        assert result["total_dispatches"] == 1
        assert "scan" not in result["by_agent"]

    def test_handles_missing_detail_field(self) -> None:
        events = [
            {"timestamp": _ts(), "event": "agent_dispatched", "detail": {}},
            {"timestamp": _ts(), "event": "agent_dispatched", "detail": {"agent": ""}},
        ]
        result = agent_dispatch_from(events)
        assert result["total_dispatches"] == 0


# ---------------------------------------------------------------------------
# Dashboard wiring (observe_team, observe_ai)
# ---------------------------------------------------------------------------


class TestObserveTeamSkillAgent:
    def test_team_includes_skill_usage(self) -> None:
        from ai_engineering.cli_commands.observe import observe_team

        with patch("ai_engineering.cli_commands.observe.load_all_events") as mock_load:
            mock_load.return_value = [
                _skill_event("build"),
                _skill_event("test"),
            ]
            with patch("ai_engineering.cli_commands.observe.decision_store_health") as mock_dsh:
                mock_dsh.return_value = {
                    "total": 0,
                    "active": 0,
                    "expired": 0,
                    "resolved": 0,
                    "avg_age_days": 0,
                }
                with patch("ai_engineering.cli_commands.observe.adoption_metrics") as mock_adopt:
                    mock_adopt.return_value = {
                        "stacks": [],
                        "providers": {"primary": "unknown", "enabled": []},
                        "ides": [],
                        "hooks_installed": False,
                        "hooks_verified": False,
                    }
                    data = observe_team(Path("/tmp/fake"))

        assert "skill_usage" in data
        assert data["skill_usage"]["total_invocations"] == 2
        assert "agent_dispatch" in data

    def test_ai_includes_skill_agent_efficiency(self) -> None:
        from ai_engineering.cli_commands.observe import observe_ai

        with patch("ai_engineering.cli_commands.observe.load_all_events") as mock_load:
            mock_load.return_value = [
                _skill_event("build"),
                _agent_event("execute"),
            ]
            with patch("ai_engineering.cli_commands.observe.checkpoint_status") as mock_cp:
                mock_cp.return_value = {"has_checkpoint": False}
                data = observe_ai(Path("/tmp/fake"))

        assert "skill_agent_efficiency" in data
        assert data["skill_agent_efficiency"]["skill_invocations"] == 1
        assert data["skill_agent_efficiency"]["agent_dispatches"] == 1
