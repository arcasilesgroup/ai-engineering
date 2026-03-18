"""Unit tests for spec-042: emit infrastructure enhancements.

Tests noise_ratio_from aggregator, enriched session events,
fixable_failures tracking in gate events, and new dashboard sections.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.lib.signals import noise_ratio_from

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(days_ago: int = 0) -> str:
    dt = datetime.now(tz=UTC) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _gate_event(
    result: str = "fail",
    failed_checks: list[str] | None = None,
    fixable_failures: list[str] | None = None,
    days_ago: int = 0,
) -> dict:
    return {
        "timestamp": _ts(days_ago),
        "event": "gate_result",
        "detail": {
            "type": "gate_result",
            "gate": "pre-commit",
            "result": result,
            "checks": {},
            "total_checks": 3,
            "failed_checks": failed_checks or [],
            "fixable_failures": fixable_failures or [],
        },
    }


def _make_audit_log(project_root: Path, events: list[dict]) -> Path:
    state_dir = project_root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "audit-log.ndjson"
    lines = [json.dumps(e) for e in events]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path


# ---------------------------------------------------------------------------
# noise_ratio_from tests
# ---------------------------------------------------------------------------


class TestNoiseRatioFrom:
    def test_no_events_returns_zero(self) -> None:
        result = noise_ratio_from([])
        assert result["total_failures"] == 0
        assert result["fixable_failures"] == 0
        assert result["noise_ratio_pct"] == 0.0

    def test_no_failures_returns_zero(self) -> None:
        events = [_gate_event(result="pass")]
        result = noise_ratio_from(events)
        assert result["total_failures"] == 0
        assert result["noise_ratio_pct"] == 0.0

    def test_all_fixable(self) -> None:
        events = [
            _gate_event(
                failed_checks=["ruff-format", "ruff-lint"],
                fixable_failures=["ruff-format", "ruff-lint"],
            ),
        ]
        result = noise_ratio_from(events)
        assert result["total_failures"] == 2
        assert result["fixable_failures"] == 2
        assert result["noise_ratio_pct"] == 100.0

    def test_mixed_failures(self) -> None:
        events = [
            _gate_event(
                failed_checks=["ruff-format", "gitleaks"],
                fixable_failures=["ruff-format"],
            ),
        ]
        result = noise_ratio_from(events)
        assert result["total_failures"] == 2
        assert result["fixable_failures"] == 1
        assert result["noise_ratio_pct"] == 50.0

    def test_respects_days_window(self) -> None:
        events = [
            _gate_event(
                failed_checks=["ruff-format"],
                fixable_failures=["ruff-format"],
                days_ago=60,
            ),
        ]
        result = noise_ratio_from(events, days=30)
        assert result["total_failures"] == 0

    def test_multiple_events(self) -> None:
        events = [
            _gate_event(
                failed_checks=["ruff-format"],
                fixable_failures=["ruff-format"],
            ),
            _gate_event(
                failed_checks=["gitleaks", "semgrep"],
                fixable_failures=[],
            ),
        ]
        result = noise_ratio_from(events)
        assert result["total_failures"] == 3
        assert result["fixable_failures"] == 1
        assert result["noise_ratio_pct"] == pytest.approx(33.3, abs=0.1)

    def test_events_without_fixable_field(self) -> None:
        """Old events without fixable_failures field should not break."""
        events = [
            {
                "timestamp": _ts(),
                "event": "gate_result",
                "detail": {
                    "type": "gate_result",
                    "failed_checks": ["ruff-format"],
                },
            },
        ]
        result = noise_ratio_from(events)
        assert result["total_failures"] == 1
        assert result["fixable_failures"] == 0


# ---------------------------------------------------------------------------
# emit_gate_event with fixable_failures tests
# ---------------------------------------------------------------------------


class TestGateEventFixableFailures:
    def test_emits_fixable_failures(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import _FIXABLE_CHECKS, emit_gate_event

        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "audit-log.ndjson").write_text("", encoding="utf-8")

        # Create a mock GateResult
        from ai_engineering.policy.gates import GateCheckResult, GateResult
        from ai_engineering.state.models import GateHook

        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[
                GateCheckResult(name="ruff-format", passed=False),
                GateCheckResult(name="gitleaks", passed=True),
                GateCheckResult(name="ruff-lint", passed=False),
            ],
        )

        with (
            patch("ai_engineering.state.audit.get_repo_context", return_value=None),
            patch("ai_engineering.state.audit.get_git_context", return_value=None),
        ):
            emit_gate_event(tmp_path, result)

        log_path = state_dir / "audit-log.ndjson"
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        detail = event["detail"]
        assert "fixable_failures" in detail
        assert set(detail["fixable_failures"]) == {"ruff-format", "ruff-lint"}
        assert "ruff-format" in _FIXABLE_CHECKS

    def test_no_fixable_when_all_pass(self, tmp_path: Path) -> None:
        from ai_engineering.state.audit import emit_gate_event

        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "audit-log.ndjson").write_text("", encoding="utf-8")

        from ai_engineering.policy.gates import GateCheckResult, GateResult
        from ai_engineering.state.models import GateHook

        result = GateResult(
            hook=GateHook.PRE_COMMIT,
            checks=[
                GateCheckResult(name="ruff-format", passed=True),
                GateCheckResult(name="gitleaks", passed=True),
            ],
        )

        with (
            patch("ai_engineering.state.audit.get_repo_context", return_value=None),
            patch("ai_engineering.state.audit.get_git_context", return_value=None),
        ):
            emit_gate_event(tmp_path, result)

        log_path = state_dir / "audit-log.ndjson"
        event = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert event["detail"]["fixable_failures"] == []


# ---------------------------------------------------------------------------
# Team dashboard new sections tests
# ---------------------------------------------------------------------------


class TestTeamDashboardNoiseRatio:
    def test_shows_noise_ratio_with_failures(self, tmp_path: Path) -> None:
        from ai_engineering.cli_commands.observe import observe_team

        events = [
            _gate_event(
                failed_checks=["ruff-format", "gitleaks"],
                fixable_failures=["ruff-format"],
            ),
        ]
        _make_audit_log(tmp_path, events)

        with (
            patch("ai_engineering.cli_commands.observe.find_project_root", return_value=tmp_path),
            patch(
                "ai_engineering.lib.signals.sonar_detailed_metrics",
                return_value={"available": False},
            ),
            patch("ai_engineering.lib.signals._sonar_cache", None),
        ):
            output = observe_team(tmp_path)

        assert output["noise_ratio"]["total_failures"] == 2
        assert output["noise_ratio"]["fixable_failures"] == 1
        assert output["noise_ratio"]["noise_ratio_pct"] == 50.0

    def test_shows_no_failures_message(self, tmp_path: Path) -> None:
        from ai_engineering.cli_commands.observe import observe_team

        events = [_gate_event(result="pass")]
        _make_audit_log(tmp_path, events)

        with (
            patch("ai_engineering.cli_commands.observe.find_project_root", return_value=tmp_path),
            patch(
                "ai_engineering.lib.signals.sonar_detailed_metrics",
                return_value={"available": False},
            ),
            patch("ai_engineering.lib.signals._sonar_cache", None),
        ):
            output = observe_team(tmp_path)

        assert output["noise_ratio"]["total_failures"] == 0


# ---------------------------------------------------------------------------
# AI dashboard avg tokens test
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Health dashboard noise component test
# ---------------------------------------------------------------------------


class TestHealthNoiseComponent:
    def test_includes_noise_component_when_failures_exist(self, tmp_path: Path) -> None:
        from ai_engineering.cli_commands.observe import observe_health

        events = [
            _gate_event(
                failed_checks=["ruff-format"],
                fixable_failures=["ruff-format"],
            ),
        ]
        _make_audit_log(tmp_path, events)

        with (
            patch("ai_engineering.cli_commands.observe.find_project_root", return_value=tmp_path),
            patch(
                "ai_engineering.cli_commands.observe._git_log_stat",
                return_value={"commits": 10, "commits_per_week": 5, "period_days": 30},
            ),
            patch(
                "ai_engineering.cli_commands.observe._dora_metrics",
                return_value={
                    "deployment_frequency_per_week": 1.0,
                    "total_merges_30d": 4,
                    "commits_per_week": 5,
                    "total_commits_30d": 10,
                },
            ),
            patch(
                "ai_engineering.lib.signals.sonar_detailed_metrics",
                return_value={"available": False},
            ),
            patch("ai_engineering.lib.signals._sonar_cache", None),
            patch(
                "ai_engineering.lib.signals.test_confidence_metrics",
                return_value={
                    "source": "none",
                    "coverage_pct": 0,
                    "meets_threshold": False,
                    "files_total": 0,
                    "files_covered": 0,
                    "untested_critical": [],
                },
            ),
        ):
            output = observe_health(tmp_path)

        assert "Gate signal quality" in output["components"]
        assert output["component_details"]["noise_score"] is not None

    def test_no_noise_component_without_failures(self, tmp_path: Path) -> None:
        from ai_engineering.cli_commands.observe import observe_health

        events = [_gate_event(result="pass")]
        _make_audit_log(tmp_path, events)

        with (
            patch("ai_engineering.cli_commands.observe.find_project_root", return_value=tmp_path),
            patch(
                "ai_engineering.cli_commands.observe._git_log_stat",
                return_value={"commits": 10, "commits_per_week": 5, "period_days": 30},
            ),
            patch(
                "ai_engineering.cli_commands.observe._dora_metrics",
                return_value={
                    "deployment_frequency_per_week": 1.0,
                    "total_merges_30d": 4,
                    "commits_per_week": 5,
                    "total_commits_30d": 10,
                },
            ),
            patch(
                "ai_engineering.lib.signals.sonar_detailed_metrics",
                return_value={"available": False},
            ),
            patch("ai_engineering.lib.signals._sonar_cache", None),
            patch(
                "ai_engineering.lib.signals.test_confidence_metrics",
                return_value={
                    "source": "none",
                    "coverage_pct": 0,
                    "meets_threshold": False,
                    "files_total": 0,
                    "files_covered": 0,
                    "untested_critical": [],
                },
            ),
        ):
            output = observe_health(tmp_path)

        assert "Gate signal quality" not in output["components"]
        assert output["component_details"]["noise_score"] is None
