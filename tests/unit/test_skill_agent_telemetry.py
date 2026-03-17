"""Unit tests for spec-044: skill & agent telemetry aggregators and dashboard wiring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.lib.signals import (
    agent_dispatch_from,
    guard_advisory_from,
    guard_drift_from,
    skill_usage_from,
)

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
            _agent_event("verify"),
            _agent_event("plan"),
            _agent_event("plan"),
            _agent_event("plan"),
        ]
        result = agent_dispatch_from(events)
        assert result["total_dispatches"] == 6
        keys = list(result["by_agent"].keys())
        assert keys == ["plan", "build", "verify"]

    def test_respects_time_window(self) -> None:
        events = [
            _agent_event("build", days_ago=0),
            _agent_event("verify", days_ago=60),
        ]
        result = agent_dispatch_from(events, days=30)
        assert result["total_dispatches"] == 1
        assert "verify" not in result["by_agent"]

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


_EMPTY_ADOPTION: dict = {
    "stacks": [],
    "providers": {"primary": "unknown", "enabled": []},
    "ides": [],
    "hooks_installed": False,
    "hooks_verified": False,
}

_EMPTY_DECISION: dict = {
    "total": 0,
    "active": 0,
    "expired": 0,
    "resolved": 0,
    "avg_age_days": 0,
}

_MODULE = "ai_engineering.cli_commands.observe"


class TestObserveTeamSkillAgent:
    def test_team_includes_skill_usage(self) -> None:
        from ai_engineering.cli_commands.observe import observe_team

        with (
            patch(f"{_MODULE}.load_all_events") as mock_load,
            patch(f"{_MODULE}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{_MODULE}.adoption_metrics", return_value=_EMPTY_ADOPTION),
        ):
            mock_load.return_value = [
                _skill_event("build"),
                _skill_event("test"),
            ]
            data = observe_team(Path("/tmp/fake"))

        assert "skill_usage" in data
        assert data["skill_usage"]["total_invocations"] == 2
        assert "agent_dispatch" in data

    def test_team_skill_usage_with_data(self) -> None:
        from ai_engineering.cli_commands.observe import observe_team

        events = [
            _skill_event("build"),
            _skill_event("build"),
            _skill_event("build"),
            _skill_event("test"),
            _agent_event("plan"),
            _agent_event("build"),
            _agent_event("build"),
        ]
        with (
            patch(f"{_MODULE}.load_all_events", return_value=events),
            patch(f"{_MODULE}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{_MODULE}.adoption_metrics", return_value=_EMPTY_ADOPTION),
        ):
            data = observe_team(Path("/tmp/fake"))

        su = data["skill_usage"]
        assert su["total_invocations"] == 4
        assert su["top_skill"] == "build"
        assert su["by_skill"]["build"] == 3

        ad = data["agent_dispatch"]
        assert ad["total_dispatches"] == 3
        assert ad["by_agent"]["build"] == 2

    def test_ai_includes_skill_agent_efficiency(self) -> None:
        from ai_engineering.cli_commands.observe import observe_ai

        with (
            patch(f"{_MODULE}.load_all_events") as mock_load,
            patch(f"{_MODULE}.checkpoint_status", return_value={"has_checkpoint": False}),
        ):
            mock_load.return_value = [
                _skill_event("build"),
                _agent_event("plan"),
            ]
            data = observe_ai(Path("/tmp/fake"))

        assert "skill_agent_efficiency" in data
        assert data["skill_agent_efficiency"]["skill_invocations"] == 1
        assert data["skill_agent_efficiency"]["agent_dispatches"] == 1

    def test_ai_skill_agent_with_multiple_events(self) -> None:
        from ai_engineering.cli_commands.observe import observe_ai

        events = [
            _skill_event("build"),
            _skill_event("test"),
            _skill_event("plan"),
            _agent_event("plan"),
            _agent_event("build"),
        ]
        with (
            patch(f"{_MODULE}.load_all_events", return_value=events),
            patch(f"{_MODULE}.checkpoint_status", return_value={"has_checkpoint": False}),
        ):
            data = observe_ai(Path("/tmp/fake"))

        sae = data["skill_agent_efficiency"]
        assert sae["skill_invocations"] == 3
        assert sae["unique_skills_used"] == 3
        assert sae["agent_dispatches"] == 2
        assert sae["unique_agents_used"] == 2


class TestRenderSkillAgentSections:
    """Test rendering covers new skill/agent sections."""

    def test_render_team_with_skill_data(self) -> None:
        from ai_engineering.cli_commands.observe import _render_team

        data = {
            "data_quality": "LOW",
            "total_events": 10,
            "event_distribution": {
                "gate_events": 5,
                "scan_events": 0,
                "build_events": 0,
                "session_events": 0,
                "deploy_events": 0,
            },
            "gate_health": {"pass_rate": 100.0, "most_friction": "none"},
            "decision_store": _EMPTY_DECISION,
            "adoption": {
                "stacks": [],
                "primary_provider": "unknown",
                "ides": [],
                "hooks_status": "not installed",
            },
            "scan_health": {"total_scans": 0, "avg_quality_score": 0},
            "token_economy": {
                "sessions_analyzed": 0,
                "total_tokens": 0,
                "utilization_pct": 0,
                "skills_loaded": [],
            },
            "noise_ratio": {
                "total_failures": 0,
                "fixable_failures": 0,
                "noise_ratio_pct": 0,
            },
            "skill_usage": {
                "total_invocations": 5,
                "by_skill": {"build": 3, "test": 2},
                "top_skill": "build",
                "least_skill": "test",
            },
            "agent_dispatch": {
                "total_dispatches": 3,
                "by_agent": {"plan": 2, "verify": 1},
            },
            "actions": ["Action 1"],
        }
        _render_team(data)

    def test_render_team_empty_skill_data(self) -> None:
        from ai_engineering.cli_commands.observe import _render_team

        data = {
            "data_quality": "LOW",
            "total_events": 0,
            "event_distribution": {
                "gate_events": 0,
                "scan_events": 0,
                "build_events": 0,
                "session_events": 0,
                "deploy_events": 0,
            },
            "gate_health": {"pass_rate": 0, "most_friction": ""},
            "decision_store": _EMPTY_DECISION,
            "adoption": {
                "stacks": [],
                "primary_provider": "unknown",
                "ides": [],
                "hooks_status": "not installed",
            },
            "scan_health": {"total_scans": 0, "avg_quality_score": 0},
            "token_economy": {
                "sessions_analyzed": 0,
                "total_tokens": 0,
                "utilization_pct": 0,
                "skills_loaded": [],
            },
            "noise_ratio": {
                "total_failures": 0,
                "fixable_failures": 0,
                "noise_ratio_pct": 0,
            },
            "skill_usage": {
                "total_invocations": 0,
                "by_skill": {},
                "top_skill": "none",
                "least_skill": "none",
            },
            "agent_dispatch": {"total_dispatches": 0, "by_agent": {}},
            "actions": [],
        }
        _render_team(data)

    def test_render_ai_with_skill_data(self) -> None:
        from ai_engineering.cli_commands.observe import _render_ai

        data = {
            "data_quality": "LOW",
            "context_efficiency": {
                "sessions_analyzed": 0,
                "total_tokens": 0,
                "avg_tokens_per_session": 0,
                "tokens_available": 200000,
                "utilization_pct": 0,
                "skills_loaded": [],
            },
            "decision_continuity": {
                "decisions_reused": 0,
                "decisions_reprompted": 0,
                "cache_hit_rate": 0,
            },
            "session_recovery": {"has_checkpoint": False},
            "skill_agent_efficiency": {
                "skill_invocations": 5,
                "unique_skills_used": 3,
                "agent_dispatches": 2,
                "unique_agents_used": 2,
            },
            "self_optimization_hints": ["All patterns healthy"],
            "actions": [],
        }
        _render_ai(data)

    def test_render_ai_empty_skill_data(self) -> None:
        from ai_engineering.cli_commands.observe import _render_ai

        data = {
            "data_quality": "LOW",
            "context_efficiency": {
                "sessions_analyzed": 0,
                "total_tokens": 0,
                "avg_tokens_per_session": 0,
                "tokens_available": 200000,
                "utilization_pct": 0,
                "skills_loaded": [],
            },
            "decision_continuity": {
                "decisions_reused": 0,
                "decisions_reprompted": 0,
                "cache_hit_rate": 0,
            },
            "session_recovery": {"has_checkpoint": False},
            "skill_agent_efficiency": {
                "skill_invocations": 0,
                "unique_skills_used": 0,
                "agent_dispatches": 0,
                "unique_agents_used": 0,
            },
            "self_optimization_hints": ["No session data"],
            "actions": [],
        }
        _render_ai(data)


# ---------------------------------------------------------------------------
# guard_advisory_from
# ---------------------------------------------------------------------------


def _guard_advisory_event(warnings: int = 0, concerns: int = 0, days_ago: int = 0) -> dict:
    return {
        "timestamp": _ts(days_ago),
        "event": "guard_advisory",
        "actor": "guard",
        "detail": {
            "mode": "advise",
            "files_checked": 3,
            "warnings": warnings,
            "concerns": concerns,
        },
    }


def _guard_drift_event(
    decisions_checked: int = 5, drifted: int = 0, critical: int = 0, days_ago: int = 0
) -> dict:
    return {
        "timestamp": _ts(days_ago),
        "event": "guard_drift",
        "actor": "guard",
        "detail": {
            "mode": "drift",
            "decisions_checked": decisions_checked,
            "drifted": drifted,
            "critical": critical,
        },
    }


class TestGuardAdvisoryFrom:
    def test_empty_events(self) -> None:
        result = guard_advisory_from([])
        assert result["total_advisories"] == 0
        assert result["total_warnings"] == 0

    def test_single_advisory(self) -> None:
        events = [_guard_advisory_event(warnings=3, concerns=1)]
        result = guard_advisory_from(events)
        assert result["total_advisories"] == 1
        assert result["total_warnings"] == 3
        assert result["total_concerns"] == 1

    def test_multiple_advisories(self) -> None:
        events = [
            _guard_advisory_event(warnings=2),
            _guard_advisory_event(warnings=1, concerns=2),
        ]
        result = guard_advisory_from(events)
        assert result["total_advisories"] == 2
        assert result["total_warnings"] == 3
        assert result["total_concerns"] == 2

    def test_respects_time_window(self) -> None:
        events = [
            _guard_advisory_event(warnings=1, days_ago=0),
            _guard_advisory_event(warnings=5, days_ago=60),
        ]
        result = guard_advisory_from(events, days=30)
        assert result["total_advisories"] == 1
        assert result["total_warnings"] == 1


class TestGuardDriftFrom:
    def test_empty_events(self) -> None:
        result = guard_drift_from([])
        assert result["total_checks"] == 0
        assert result["alignment_pct"] == 0.0

    def test_perfect_alignment(self) -> None:
        events = [_guard_drift_event(decisions_checked=10, drifted=0)]
        result = guard_drift_from(events)
        assert result["alignment_pct"] == 100.0
        assert result["total_drifted"] == 0

    def test_partial_drift(self) -> None:
        events = [_guard_drift_event(decisions_checked=10, drifted=3, critical=1)]
        result = guard_drift_from(events)
        assert result["alignment_pct"] == 70.0
        assert result["total_drifted"] == 3
        assert result["total_critical"] == 1

    def test_respects_time_window(self) -> None:
        events = [
            _guard_drift_event(decisions_checked=5, drifted=1, days_ago=0),
            _guard_drift_event(decisions_checked=10, drifted=5, days_ago=60),
        ]
        result = guard_drift_from(events, days=30)
        assert result["total_checks"] == 1
        assert result["total_drifted"] == 1
