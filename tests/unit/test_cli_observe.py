"""Unit tests for ai_engineering.cli_commands.observe module.

Tests all five observe dashboard modes (engineer, team, ai, dora, health)
via the Typer CLI runner, plus internal helper functions.
Uses tmp_path for creating temp project dirs with state files.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands.observe import (
    _count_by_type,
    _dora_metrics,
    _git_log_stat,
    _project_root,
    observe_ai,
    observe_dora,
    observe_engineer,
    observe_health,
    observe_team,
)
from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audit_log(project_root: Path, events: list[dict]) -> Path:
    """Write events as NDJSON to the audit-log.ndjson file."""
    state_dir = project_root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "audit-log.ndjson"
    lines = [json.dumps(e) for e in events]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path


def _ts(days_ago: int = 0) -> str:
    """Return an ISO timestamp for N days ago."""
    dt = datetime.now(tz=UTC) - timedelta(days=days_ago)
    return dt.isoformat()


def _gate_event(result: str = "pass", failed_checks: list[str] | None = None) -> dict:
    """Create a gate_result event."""
    detail: dict = {"result": result}
    if failed_checks:
        detail["failed_checks"] = failed_checks
    return {
        "event": "gate_result",
        "timestamp": _ts(1),
        "detail": detail,
    }


def _session_event(
    tokens_used: int = 100,
    decisions_reused: int = 2,
    decisions_reprompted: int = 1,
) -> dict:
    """Create a session_metric event."""
    return {
        "event": "session_metric",
        "timestamp": _ts(1),
        "detail": {
            "tokens_used": tokens_used,
            "decisions_reused": decisions_reused,
            "decisions_reprompted": decisions_reprompted,
        },
    }


def _scan_event() -> dict:
    return {"event": "scan_complete", "timestamp": _ts(2)}


def _build_event() -> dict:
    return {"event": "build_complete", "timestamp": _ts(3)}


def _init_git_repo(path: Path) -> None:
    """Initialize a git repo with one commit so git log works."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    (path / "readme.txt").write_text("init", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


# ---------------------------------------------------------------------------
# _project_root tests
# ---------------------------------------------------------------------------


class TestProjectRoot:
    """Tests for _project_root helper."""

    def test_finds_ai_engineering_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir()
        with patch("ai_engineering.cli_commands.observe.Path.cwd", return_value=tmp_path):
            assert _project_root() == tmp_path

    def test_finds_parent_with_ai_engineering(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir()
        child = tmp_path / "src" / "sub"
        child.mkdir(parents=True)
        with patch("ai_engineering.cli_commands.observe.Path.cwd", return_value=child):
            assert _project_root() == tmp_path

    def test_falls_back_to_cwd_when_not_found(self, tmp_path: Path) -> None:
        with patch("ai_engineering.cli_commands.observe.Path.cwd", return_value=tmp_path):
            assert _project_root() == tmp_path


# ---------------------------------------------------------------------------
# _git_log_stat tests
# ---------------------------------------------------------------------------


class TestGitLogStat:
    """Tests for _git_log_stat helper."""

    def test_returns_commit_stats(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        stats = _git_log_stat(tmp_path, days=30)
        assert "commits" in stats
        assert "commits_per_week" in stats
        assert "period_days" in stats
        assert stats["period_days"] == 30
        assert stats["commits"] >= 1  # at least the init commit

    def test_handles_no_git_repo(self, tmp_path: Path) -> None:
        stats = _git_log_stat(tmp_path, days=30)
        # Should not crash; returns 0 commits (git command may fail or return nothing)
        assert "commits" in stats
        assert isinstance(stats["commits"], int)

    def test_handles_subprocess_timeout(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
        ):
            stats = _git_log_stat(tmp_path)
            assert stats["commits"] == 0
            assert stats["commits_per_week"] == 0.0

    def test_handles_file_not_found(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            stats = _git_log_stat(tmp_path)
            assert stats["commits"] == 0

    def test_commits_per_week_calculation(self, tmp_path: Path) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc1234 commit1\ndef5678 commit2\n"
        )
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            stats = _git_log_stat(tmp_path, days=14)
            assert stats["commits"] == 2
            assert stats["commits_per_week"] == 1.0  # 2 commits / 2 weeks

    def test_empty_stdout(self, tmp_path: Path) -> None:
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            stats = _git_log_stat(tmp_path)
            assert stats["commits"] == 0


# ---------------------------------------------------------------------------
# _dora_metrics tests
# ---------------------------------------------------------------------------


class TestDoraMetrics:
    """Tests for _dora_metrics helper."""

    def test_computes_metrics_with_git_stats(self, tmp_path: Path) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc merge1\ndef merge2\n"
        )
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            git_stats = {"commits": 10, "commits_per_week": 5.0, "period_days": 30}
            metrics = _dora_metrics(tmp_path, git_stats=git_stats)
            assert metrics["total_merges_30d"] == 2
            assert metrics["deployment_frequency_per_week"] == round(2 / 4.3, 1)
            assert metrics["commits_per_week"] == 5.0
            assert metrics["total_commits_30d"] == 10

    def test_computes_metrics_without_git_stats(self, tmp_path: Path) -> None:
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            metrics = _dora_metrics(tmp_path, git_stats=None)
            assert metrics["total_merges_30d"] == 0
            assert metrics["deployment_frequency_per_week"] == 0.0

    def test_handles_timeout(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
        ):
            git_stats = {"commits": 0, "commits_per_week": 0.0, "period_days": 30}
            metrics = _dora_metrics(tmp_path, git_stats=git_stats)
            assert metrics["total_merges_30d"] == 0

    def test_handles_file_not_found(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            git_stats = {"commits": 0, "commits_per_week": 0.0, "period_days": 30}
            metrics = _dora_metrics(tmp_path, git_stats=git_stats)
            assert metrics["total_merges_30d"] == 0


# ---------------------------------------------------------------------------
# _count_by_type tests
# ---------------------------------------------------------------------------


class TestCountByType:
    """Tests for _count_by_type helper."""

    def test_counts_matching_events(self) -> None:
        events = [
            {"event": "scan_complete"},
            {"event": "build_complete"},
            {"event": "scan_complete"},
        ]
        assert _count_by_type(events, "scan_complete") == 2

    def test_returns_zero_for_no_match(self) -> None:
        events = [{"event": "build_complete"}]
        assert _count_by_type(events, "scan_complete") == 0

    def test_handles_empty_list(self) -> None:
        assert _count_by_type([], "scan_complete") == 0

    def test_handles_events_without_event_key(self) -> None:
        events = [{"other": "field"}, {"event": "scan_complete"}]
        assert _count_by_type(events, "scan_complete") == 1


# ---------------------------------------------------------------------------
# observe_engineer tests
# ---------------------------------------------------------------------------


class TestObserveEngineer:
    """Tests for observe_engineer dashboard."""

    def test_empty_audit_log(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_engineer(tmp_path)
        assert "# Engineer Dashboard" in output
        assert "Data quality: LOW" in output
        assert "Commits/week:" in output
        assert "Gate Health" in output
        assert "Actions" in output

    def test_with_events(self, tmp_path: Path) -> None:
        events = [
            _gate_event("pass"),
            _gate_event("pass"),
            _gate_event("fail", ["ruff"]),
        ]
        _make_audit_log(tmp_path, events)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc commit1\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_engineer(tmp_path)
        assert "# Engineer Dashboard" in output
        assert "3 events" in output
        assert "Pass rate:" in output
        assert "Most failed check:" in output


# ---------------------------------------------------------------------------
# observe_team tests
# ---------------------------------------------------------------------------


class TestObserveTeam:
    """Tests for observe_team dashboard."""

    def test_empty_audit_log(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        output = observe_team(tmp_path)
        assert "# Team Dashboard" in output
        assert "Data quality: LOW" in output
        assert "Event Distribution" in output

    def test_with_mixed_events(self, tmp_path: Path) -> None:
        events = [
            _gate_event("pass"),
            _scan_event(),
            _scan_event(),
            _build_event(),
            _session_event(),
        ]
        _make_audit_log(tmp_path, events)
        output = observe_team(tmp_path)
        assert "# Team Dashboard" in output
        assert "5 events" in output
        assert "Scan events: 2" in output
        assert "Build events: 1" in output
        assert "Session events: 1" in output
        assert "Gate Health" in output
        assert "Actions" in output


# ---------------------------------------------------------------------------
# observe_ai tests
# ---------------------------------------------------------------------------


class TestObserveAi:
    """Tests for observe_ai dashboard."""

    def test_empty_audit_log(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        output = observe_ai(tmp_path)
        assert "# AI Self-Awareness" in output
        assert "Data quality: LOW" in output
        assert "Cache hit rate: 0.0%" in output

    def test_with_session_events(self, tmp_path: Path) -> None:
        events = [
            _session_event(tokens_used=500, decisions_reused=5, decisions_reprompted=2),
            _session_event(tokens_used=300, decisions_reused=3, decisions_reprompted=1),
        ]
        _make_audit_log(tmp_path, events)
        output = observe_ai(tmp_path)
        assert "# AI Self-Awareness" in output
        assert "Sessions analyzed: 2" in output
        assert "Total tokens (recent): 800" in output
        assert "Decisions reused: 8" in output
        assert "Decisions re-prompted: 3" in output
        # Cache hit rate: 8 / (8 + 3) * 100 = 72.7%
        assert "Cache hit rate: 72.7%" in output

    def test_zero_decisions_gives_zero_cache_hit(self, tmp_path: Path) -> None:
        events = [
            _session_event(tokens_used=100, decisions_reused=0, decisions_reprompted=0),
        ]
        _make_audit_log(tmp_path, events)
        output = observe_ai(tmp_path)
        assert "Cache hit rate: 0.0%" in output

    def test_non_dict_detail_is_handled(self, tmp_path: Path) -> None:
        events = [
            {"event": "session_metric", "timestamp": _ts(1), "detail": "not-a-dict"},
        ]
        _make_audit_log(tmp_path, events)
        output = observe_ai(tmp_path)
        assert "Total tokens (recent): 0" in output


# ---------------------------------------------------------------------------
# observe_dora tests
# ---------------------------------------------------------------------------


class TestObserveDora:
    """Tests for observe_dora dashboard."""

    def test_empty_audit_log(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_dora(tmp_path)
        assert "# DORA Metrics" in output
        assert "Data quality: LOW" in output
        assert "Deployment Frequency" in output
        assert "Delivery Velocity" in output
        assert "Rating: LOW" in output

    def test_elite_freq_rating(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        # 22 merges => 22 / 4.3 ~= 5.1 => ELITE
        merge_lines = "\n".join([f"abc{i} merge{i}" for i in range(22)])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=merge_lines + "\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_dora(tmp_path)
        assert "Rating: ELITE" in output

    def test_high_freq_rating(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        # 5 merges => 5 / 4.3 ~= 1.2 => HIGH
        merge_lines = "\n".join([f"abc{i} merge{i}" for i in range(5)])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=merge_lines + "\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_dora(tmp_path)
        assert "Rating: HIGH" in output

    def test_medium_freq_rating(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        # 2 merges => 2 / 4.3 ~= 0.47 => MEDIUM (>= 0.25)
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc merge1\ndef merge2\n"
        )
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_dora(tmp_path)
        assert "Rating: MEDIUM" in output


# ---------------------------------------------------------------------------
# observe_health tests
# ---------------------------------------------------------------------------


class TestObserveHealth:
    """Tests for observe_health dashboard."""

    def test_empty_audit_log_red(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_health(tmp_path)
        assert "# Health Score:" in output
        assert "RED" in output
        assert "Components" in output
        assert "Semaphore" in output
        assert "Top Actions" in output

    def test_green_semaphore(self, tmp_path: Path) -> None:
        """100% gate pass + high velocity => GREEN."""
        events = [_gate_event("pass") for _ in range(10)]
        _make_audit_log(tmp_path, events)
        # 80 commits => 80 / (30/7) ~= 18.7 commits/week => velocity = min(187, 100) = 100
        commit_lines = "\n".join([f"abc{i} commit{i}" for i in range(80)])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=commit_lines + "\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_health(tmp_path)
        assert "GREEN" in output

    def test_yellow_semaphore(self, tmp_path: Path) -> None:
        """Moderate gate pass + moderate velocity => YELLOW."""
        # 6 pass + 4 fail => 60% pass rate
        events = [_gate_event("pass") for _ in range(6)]
        events += [_gate_event("fail", ["ruff"]) for _ in range(4)]
        _make_audit_log(tmp_path, events)
        # 6 commits => 6 / (30/7) ~= 1.4 commits/week => velocity = 14
        # overall = (60 + 14) / 2 = 37 => RED
        # Let's use 26 commits => 26 / 4.29 ~= 6.1 commits/week => velocity = 61
        # overall = (60 + 61) / 2 = 60.5 => rounds to 60 => YELLOW
        commit_lines = "\n".join([f"abc{i} commit{i}" for i in range(26)])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=commit_lines + "\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_health(tmp_path)
        assert "YELLOW" in output

    def test_red_semaphore(self, tmp_path: Path) -> None:
        """Low gate pass + low velocity => RED."""
        events = [_gate_event("fail", ["ruff"]) for _ in range(10)]
        _make_audit_log(tmp_path, events)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc commit1\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_health(tmp_path)
        assert "RED" in output

    def test_velocity_capped_at_100(self, tmp_path: Path) -> None:
        """velocity_score is capped at 100."""
        events = [_gate_event("pass") for _ in range(5)]
        _make_audit_log(tmp_path, events)
        # 200 commits => 200 / 4.29 ~= 46.6 commits/week => velocity = min(466, 100) = 100
        commit_lines = "\n".join([f"abc{i} commit{i}" for i in range(200)])
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout=commit_lines + "\n")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_health(tmp_path)
        assert "GREEN" in output


# ---------------------------------------------------------------------------
# CLI invocation tests (via Typer CliRunner)
# ---------------------------------------------------------------------------


class TestObserveCli:
    """Tests for observe_cmd invoked through the Typer CLI runner."""

    def test_default_mode_is_health(self, tmp_path: Path) -> None:
        app = create_app()
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with (
            patch(
                "ai_engineering.cli_commands.observe._project_root",
                return_value=tmp_path,
            ),
            patch(
                "ai_engineering.cli_commands.observe.subprocess.run",
                return_value=mock_result,
            ),
        ):
            (tmp_path / ".ai-engineering").mkdir(parents=True)
            result = runner.invoke(app, ["observe"])
        assert result.exit_code == 0
        assert "Health Score" in result.output

    def test_engineer_mode(self, tmp_path: Path) -> None:
        app = create_app()
        events = [_gate_event("pass")]
        _make_audit_log(tmp_path, events)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc commit1\n")
        with (
            patch(
                "ai_engineering.cli_commands.observe._project_root",
                return_value=tmp_path,
            ),
            patch(
                "ai_engineering.cli_commands.observe.subprocess.run",
                return_value=mock_result,
            ),
        ):
            result = runner.invoke(app, ["observe", "engineer"])
        assert result.exit_code == 0
        assert "Engineer Dashboard" in result.output

    def test_team_mode(self, tmp_path: Path) -> None:
        app = create_app()
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.observe._project_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["observe", "team"])
        assert result.exit_code == 0
        assert "Team Dashboard" in result.output

    def test_ai_mode(self, tmp_path: Path) -> None:
        app = create_app()
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.observe._project_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["observe", "ai"])
        assert result.exit_code == 0
        assert "AI Self-Awareness" in result.output

    def test_dora_mode(self, tmp_path: Path) -> None:
        app = create_app()
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with (
            patch(
                "ai_engineering.cli_commands.observe._project_root",
                return_value=tmp_path,
            ),
            patch(
                "ai_engineering.cli_commands.observe.subprocess.run",
                return_value=mock_result,
            ),
        ):
            result = runner.invoke(app, ["observe", "dora"])
        assert result.exit_code == 0
        assert "DORA Metrics" in result.output

    def test_health_mode(self, tmp_path: Path) -> None:
        app = create_app()
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with (
            patch(
                "ai_engineering.cli_commands.observe._project_root",
                return_value=tmp_path,
            ),
            patch(
                "ai_engineering.cli_commands.observe.subprocess.run",
                return_value=mock_result,
            ),
        ):
            result = runner.invoke(app, ["observe", "health"])
        assert result.exit_code == 0
        assert "Health Score" in result.output

    def test_unknown_mode_exits_with_error(self, tmp_path: Path) -> None:
        app = create_app()
        with patch(
            "ai_engineering.cli_commands.observe._project_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["observe", "unknown"])
        assert result.exit_code != 0
        assert "Unknown mode: unknown" in result.output
        assert "engineer" in result.output


# ---------------------------------------------------------------------------
# Edge case and integration-style tests
# ---------------------------------------------------------------------------


class TestObserveEdgeCases:
    """Edge case tests for observe module."""

    def test_audit_log_with_malformed_json(self, tmp_path: Path) -> None:
        """Malformed NDJSON lines should be skipped gracefully."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        log_path = state_dir / "audit-log.ndjson"
        log_path.write_text(
            '{"event": "gate_result", "timestamp": "'
            + _ts(1)
            + '", "detail": {"result": "pass"}}\n'
            "INVALID JSON LINE\n"
            '{"event": "gate_result", "timestamp": "'
            + _ts(1)
            + '", "detail": {"result": "pass"}}\n',
            encoding="utf-8",
        )
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_engineer(tmp_path)
        assert "2 events" in output

    def test_date_range_with_timestamps(self, tmp_path: Path) -> None:
        """Engineer dashboard should show day span when timestamps differ."""
        events = [
            {
                "event": "gate_result",
                "timestamp": _ts(30),
                "detail": {"result": "pass"},
            },
            {
                "event": "gate_result",
                "timestamp": _ts(0),
                "detail": {"result": "pass"},
            },
        ]
        _make_audit_log(tmp_path, events)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_engineer(tmp_path)
        # Should show approximately 30 days span
        assert "30 days" in output or "29 days" in output

    def test_gate_events_with_failed_checks(self, tmp_path: Path) -> None:
        """Most failed check should be reported correctly."""
        events = [
            _gate_event("fail", ["ruff"]),
            _gate_event("fail", ["ruff"]),
            _gate_event("fail", ["gitleaks"]),
            _gate_event("pass"),
        ]
        _make_audit_log(tmp_path, events)
        mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            return_value=mock_result,
        ):
            output = observe_engineer(tmp_path)
        assert "ruff" in output
        assert "2x" in output

    def test_observe_health_reuses_git_stats_for_dora(self, tmp_path: Path) -> None:
        """Health dashboard passes git_stats to _dora_metrics to avoid double call."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        call_count = {"git_log": 0, "merges": 0}

        def counting_run(cmd, **kwargs):
            if "git" in cmd and "log" in cmd:
                if "--merges" in cmd:
                    call_count["merges"] += 1
                else:
                    call_count["git_log"] += 1
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        with patch(
            "ai_engineering.cli_commands.observe.subprocess.run",
            side_effect=counting_run,
        ):
            observe_health(tmp_path)
        # Should call git log once for stats and once for merges (not twice for stats)
        assert call_count["git_log"] == 1
        assert call_count["merges"] == 1

    def test_no_audit_log_file(self, tmp_path: Path) -> None:
        """Missing audit-log.ndjson should be handled gracefully."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        output = observe_team(tmp_path)
        assert "0 events" in output

    def test_session_events_detail_missing_keys(self, tmp_path: Path) -> None:
        """Session events with missing detail fields default to 0."""
        events = [
            {"event": "session_metric", "timestamp": _ts(1), "detail": {}},
        ]
        _make_audit_log(tmp_path, events)
        output = observe_ai(tmp_path)
        assert "Total tokens (recent): 0" in output
        assert "Decisions reused: 0" in output
        assert "Decisions re-prompted: 0" in output
        assert "Cache hit rate: 0.0%" in output
