"""Unit tests for NEW observe dashboard sections added in spec-039 Phase 6.

Tests specifically the expanded sections:
- Engineer: Lead Time, Code Quality (from scans), Build Activity
- Team: Decision Store Health, Adoption, Scan Health, Deploy events
- AI: expanded Context Efficiency, Session Recovery
- DORA: Lead Time for Changes, Change Failure Rate
- Health: multi-variable weighted score

Existing dashboard tests remain in test_cli_observe.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.cli_commands.observe import (
    observe_ai,
    observe_dora,
    observe_engineer,
    observe_health,
    observe_team,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Shared mock defaults
# ---------------------------------------------------------------------------

_EMPTY_SCAN = {
    "total_scans": 0,
    "avg_quality_score": 0.0,
    "avg_security_score": 0.0,
    "findings": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    "modes_scanned": [],
}

_GOOD_SCAN = {
    "total_scans": 5,
    "avg_quality_score": 85.0,
    "avg_security_score": 92.0,
    "findings": {"critical": 1, "high": 3, "medium": 5, "low": 10},
    "modes_scanned": ["quality", "security"],
}

_EMPTY_BUILD = {
    "total_builds": 0,
    "files_changed": 0,
    "lines_added": 0,
    "lines_removed": 0,
    "tests_added": 0,
}

_GOOD_BUILD = {
    "total_builds": 12,
    "files_changed": 45,
    "lines_added": 800,
    "lines_removed": 200,
    "tests_added": 15,
}

_EMPTY_LEAD_TIME = {
    "median_days": 0,
    "merges_analyzed": 0,
    "rating": "LOW",
}

_GOOD_LEAD_TIME = {
    "median_days": 2.5,
    "merges_analyzed": 8,
    "rating": "HIGH",
}

_EMPTY_DECISION = {
    "total": 0,
    "active": 0,
    "expired": 0,
    "resolved": 0,
    "avg_age_days": 0,
}

_GOOD_DECISION = {
    "total": 10,
    "active": 5,
    "expired": 2,
    "resolved": 3,
    "avg_age_days": 14.5,
}

_DEFAULT_ADOPTION = {
    "stacks": ["python", "typescript"],
    "providers": {"primary": "anthropic", "enabled": ["anthropic", "openai"]},
    "ides": ["claude-code", "cursor"],
    "hooks_installed": True,
    "hooks_verified": True,
}

_EMPTY_ADOPTION = {
    "stacks": [],
    "providers": {"primary": "unknown", "enabled": []},
    "ides": [],
    "hooks_installed": False,
    "hooks_verified": False,
}

_EMPTY_DEPLOY = {
    "total_deploys": 0,
    "rollbacks": 0,
    "failure_rate": 0.0,
    "strategies": {},
}

_GOOD_DEPLOY = {
    "total_deploys": 20,
    "rollbacks": 3,
    "failure_rate": 15.0,
    "strategies": {"rolling": 15, "blue-green": 5},
}

_HIGH_FAILURE_DEPLOY = {
    "total_deploys": 10,
    "rollbacks": 5,
    "failure_rate": 50.0,
    "strategies": {"rolling": 10},
}

_EMPTY_SESSION = {
    "sessions_analyzed": 0,
    "total_tokens": 0,
    "tokens_available": 200_000,
    "utilization_pct": 0.0,
    "skills_loaded": [],
    "decisions_reused": 0,
    "decisions_reprompted": 0,
}

_GOOD_SESSION = {
    "sessions_analyzed": 5,
    "total_tokens": 150_000,
    "tokens_available": 200_000,
    "utilization_pct": 15.0,
    "skills_loaded": ["build", "commit", "test"],
    "decisions_reused": 10,
    "decisions_reprompted": 2,
}

_NO_CHECKPOINT = {"has_checkpoint": False}

_GOOD_CHECKPOINT = {
    "has_checkpoint": True,
    "last_task": "6.3",
    "age": "2h ago",
    "completed": 3,
    "total": 5,
    "progress_pct": 60.0,
    "blocked_on": None,
}

_BLOCKED_CHECKPOINT = {
    "has_checkpoint": True,
    "last_task": "4.1",
    "age": "1d ago",
    "completed": 2,
    "total": 8,
    "progress_pct": 25.0,
    "blocked_on": "PR review pending",
}

# Shared git mocks
_GIT_STATS = {"commits": 10, "commits_per_week": 5.0, "period_days": 30}
_DORA = {
    "deployment_frequency_per_week": 2.0,
    "total_merges_30d": 9,
    "commits_per_week": 5.0,
    "total_commits_30d": 10,
}
_GATES = {
    "total": 20,
    "passed": 18,
    "failed": 2,
    "pass_rate": 90.0,
    "most_failed_check": "ruff",
    "most_failed_count": 2,
}


# ---------------------------------------------------------------------------
# 6.1 — Engineer: Lead Time, Code Quality, Build Activity
# ---------------------------------------------------------------------------


class TestEngineerNewSections:
    """Tests for new sections in observe_engineer."""

    def test_code_quality_section_present(self, tmp_path: Path) -> None:
        """Engineer dashboard includes Code Quality section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_GOOD_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_GOOD_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "## Code Quality (from scans)" in output
        assert "Quality score: 85.0/100" in output
        assert "Security score: 92.0/100" in output
        assert "1 critical, 3 high" in output

    def test_build_activity_section_present(self, tmp_path: Path) -> None:
        """Engineer dashboard includes Build Activity section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_GOOD_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_GOOD_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "## Build Activity (last 30d)" in output
        assert "Builds: 12" in output
        assert "Files changed: 45" in output
        assert "Tests added: 15" in output

    def test_no_scan_data_message(self, tmp_path: Path) -> None:
        """Engineer dashboard shows fallback when no scan events."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_EMPTY_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_EMPTY_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "No scan data" in output

    def test_no_build_data_message(self, tmp_path: Path) -> None:
        """Engineer dashboard shows fallback when no build events."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_EMPTY_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_EMPTY_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "No build data" in output

    def test_lead_time_section_with_data(self, tmp_path: Path) -> None:
        """Engineer dashboard shows Lead Time section with merge data."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_EMPTY_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "## Lead Time" in output
        assert "Median: 2.5 days" in output
        assert "Rating: HIGH" in output
        assert "Merges analyzed: 8" in output

    def test_lead_time_insufficient_data(self, tmp_path: Path) -> None:
        """Engineer dashboard shows fallback when no merge data."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_EMPTY_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_EMPTY_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "Insufficient merge data" in output

    def test_lead_time_in_delivery_velocity(self, tmp_path: Path) -> None:
        """Engineer dashboard shows lead time in Delivery Velocity section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}.event_date_range_from", return_value=(None, None)),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.build_metrics_from", return_value=_EMPTY_BUILD),
            patch(f"{module}._sonar_metrics", return_value=[]),
        ):
            output = observe_engineer(tmp_path)

        assert "Lead time (median): 2.5 days" in output


# ---------------------------------------------------------------------------
# 6.2 — Team: Decision Store Health, Adoption, Scan Health
# ---------------------------------------------------------------------------


class TestTeamNewSections:
    """Tests for new sections in observe_team."""

    def test_decision_store_health_section(self, tmp_path: Path) -> None:
        """Team dashboard includes Decision Store Health section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_GOOD_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_DEFAULT_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "## Decision Store Health" in output
        assert "Active: 5" in output
        assert "Expired (need review): 2" in output
        assert "Resolved: 3" in output
        assert "Avg age: 14.5 days" in output

    def test_decision_store_no_decisions(self, tmp_path: Path) -> None:
        """Team dashboard shows fallback when no decisions."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "No decisions recorded" in output

    def test_adoption_section(self, tmp_path: Path) -> None:
        """Team dashboard includes Adoption section with stacks/providers/ides."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_DEFAULT_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "## Adoption" in output
        assert "Stacks: python, typescript" in output
        assert "Providers: anthropic" in output
        assert "IDEs: claude-code, cursor" in output
        assert "Hooks: installed/verified" in output

    def test_adoption_hooks_not_installed(self, tmp_path: Path) -> None:
        """Team dashboard shows not-installed hooks status."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "Hooks: not installed" in output

    def test_adoption_hooks_installed_unverified(self, tmp_path: Path) -> None:
        """Team dashboard shows installed/unverified hooks status."""
        adopt = {**_DEFAULT_ADOPTION, "hooks_verified": False}
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=adopt),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "Hooks: installed/unverified" in output

    def test_scan_health_section(self, tmp_path: Path) -> None:
        """Team dashboard includes Scan Health section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_GOOD_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "## Scan Health" in output
        assert "Avg quality score: 85.0/100" in output
        assert "Scans run: 5" in output

    def test_scan_health_no_data(self, tmp_path: Path) -> None:
        """Team dashboard shows fallback when no scan data."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "## Scan Health" in output
        assert "No scan data" in output

    def test_deploy_events_in_distribution(self, tmp_path: Path) -> None:
        """Team dashboard includes deploy events in Event Distribution."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
        ):
            output = observe_team(tmp_path)

        assert "Deploy events:" in output


# ---------------------------------------------------------------------------
# 6.3 — AI: expanded Context Efficiency, Session Recovery
# ---------------------------------------------------------------------------


class TestAiNewSections:
    """Tests for new sections in observe_ai."""

    def test_session_recovery_section(self, tmp_path: Path) -> None:
        """AI dashboard includes Session Recovery section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.session_metrics_from", return_value=_GOOD_SESSION),
            patch(f"{module}.checkpoint_status", return_value=_GOOD_CHECKPOINT),
        ):
            output = observe_ai(tmp_path)

        assert "## Session Recovery" in output
        assert "Last checkpoint: 6.3 (2h ago)" in output
        assert "Progress: 3/5 (60.0%)" in output
        assert "Blocked on: nothing" in output

    def test_no_checkpoint_found(self, tmp_path: Path) -> None:
        """AI dashboard shows 'No checkpoint found' when no checkpoint."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.session_metrics_from", return_value=_EMPTY_SESSION),
            patch(f"{module}.checkpoint_status", return_value=_NO_CHECKPOINT),
        ):
            output = observe_ai(tmp_path)

        assert "No checkpoint found" in output

    def test_blocked_checkpoint(self, tmp_path: Path) -> None:
        """AI dashboard shows blocked-on item when present."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.session_metrics_from", return_value=_GOOD_SESSION),
            patch(f"{module}.checkpoint_status", return_value=_BLOCKED_CHECKPOINT),
        ):
            output = observe_ai(tmp_path)

        assert "Blocked on: PR review pending" in output

    def test_expanded_context_efficiency(self, tmp_path: Path) -> None:
        """AI dashboard shows expanded context efficiency with utilization."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.session_metrics_from", return_value=_GOOD_SESSION),
            patch(f"{module}.checkpoint_status", return_value=_NO_CHECKPOINT),
        ):
            output = observe_ai(tmp_path)

        assert "Sessions analyzed: 5" in output
        assert "Total tokens (recent): 150,000" in output
        assert "Token utilization: 150000/200000 (15.0%)" in output
        assert "Skills loaded: build, commit, test" in output

    def test_context_efficiency_no_skills(self, tmp_path: Path) -> None:
        """AI dashboard shows 'none' when no skills loaded."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.session_metrics_from", return_value=_EMPTY_SESSION),
            patch(f"{module}.checkpoint_status", return_value=_NO_CHECKPOINT),
        ):
            output = observe_ai(tmp_path)

        assert "Skills loaded: none" in output


# ---------------------------------------------------------------------------
# 6.4 — DORA: Lead Time for Changes, Change Failure Rate
# ---------------------------------------------------------------------------


class TestDoraNewSections:
    """Tests for new sections in observe_dora."""

    def test_lead_time_section(self, tmp_path: Path) -> None:
        """DORA dashboard includes Lead Time for Changes section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.deploy_metrics_from", return_value=_EMPTY_DEPLOY),
        ):
            output = observe_dora(tmp_path)

        assert "## Lead Time for Changes" in output
        assert "Median: 2.5 days" in output
        assert "Rating: HIGH" in output

    def test_change_failure_rate_section(self, tmp_path: Path) -> None:
        """DORA dashboard includes Change Failure Rate section."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.deploy_metrics_from", return_value=_GOOD_DEPLOY),
        ):
            output = observe_dora(tmp_path)

        assert "## Change Failure Rate" in output
        assert "Deployments: 20" in output
        assert "Rollbacks: 3" in output
        assert "Rate: 15.0%" in output
        assert "Rating: ELITE" in output  # 15.0% <= 15 => ELITE

    def test_cfr_rating_high(self, tmp_path: Path) -> None:
        """CFR rating HIGH for 16-30% failure rate."""
        deploy = {**_GOOD_DEPLOY, "failure_rate": 25.0}
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.deploy_metrics_from", return_value=deploy),
        ):
            output = observe_dora(tmp_path)

        # Find the CFR rating specifically (not the deployment frequency rating)
        lines = output.split("\n")
        cfr_section = False
        for line in lines:
            if "## Change Failure Rate" in line:
                cfr_section = True
            if cfr_section and line.startswith("- Rating:"):
                assert "HIGH" in line
                break

    def test_cfr_rating_medium(self, tmp_path: Path) -> None:
        """CFR rating MEDIUM for 31-45% failure rate."""
        deploy = {**_GOOD_DEPLOY, "failure_rate": 40.0}
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.deploy_metrics_from", return_value=deploy),
        ):
            output = observe_dora(tmp_path)

        lines = output.split("\n")
        cfr_section = False
        for line in lines:
            if "## Change Failure Rate" in line:
                cfr_section = True
            if cfr_section and line.startswith("- Rating:"):
                assert "MEDIUM" in line
                break

    def test_cfr_rating_low(self, tmp_path: Path) -> None:
        """CFR rating LOW for >45% failure rate."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.lead_time_metrics", return_value=_GOOD_LEAD_TIME),
            patch(f"{module}.deploy_metrics_from", return_value=_HIGH_FAILURE_DEPLOY),
        ):
            output = observe_dora(tmp_path)

        lines = output.split("\n")
        cfr_section = False
        for line in lines:
            if "## Change Failure Rate" in line:
                cfr_section = True
            if cfr_section and line.startswith("- Rating:"):
                assert "LOW" in line
                break

    def test_zero_deploys_cfr_elite(self, tmp_path: Path) -> None:
        """Zero deploys gives 0% failure rate => ELITE."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.lead_time_metrics", return_value=_EMPTY_LEAD_TIME),
            patch(f"{module}.deploy_metrics_from", return_value=_EMPTY_DEPLOY),
        ):
            output = observe_dora(tmp_path)

        assert "Rate: 0.0%" in output


# ---------------------------------------------------------------------------
# 6.5 — Health: multi-variable weighted score
# ---------------------------------------------------------------------------


class TestHealthMultiVariable:
    """Tests for multi-variable health score computation."""

    def test_score_with_only_gate_velocity_dora(self, tmp_path: Path) -> None:
        """Health score with gate + velocity + DORA (no scan, no decisions)."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
        ):
            output = observe_health(tmp_path)

        # gate=90, velocity=min(5.0*10,100)=50, dora=75 (freq 2.0 >= 1)
        # 3 components: (90 + 50 + 75) / 3 = 71.67 => round => 72
        assert "# Health Score: 72/100" in output
        assert "YELLOW" in output
        assert "Scan quality: No data" in output
        assert "Decision health: No decisions" in output

    def test_score_with_all_components(self, tmp_path: Path) -> None:
        """Health score with all 5 components."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_GOOD_SCAN),
            patch(f"{module}.decision_store_health", return_value=_GOOD_DECISION),
        ):
            output = observe_health(tmp_path)

        # gate=90, velocity=50, scan=85, decision=max(0,100-2*20)=60, dora=75
        # 5 components: (90 + 50 + 85 + 60 + 75) / 5 = 72
        assert "# Health Score: 72/100" in output
        assert "YELLOW" in output
        assert "Scan quality: 85.0/100" in output
        assert "Decision health: 60/100" in output
        assert "DORA frequency:" in output

    def test_green_score_all_high(self, tmp_path: Path) -> None:
        """Health score GREEN when all components are high."""
        high_gates = {**_GATES, "pass_rate": 100.0}
        high_git = {"commits": 100, "commits_per_week": 15.0, "period_days": 30}
        high_dora = {**_DORA, "deployment_frequency_per_week": 6.0}
        high_scan = {**_GOOD_SCAN, "avg_quality_score": 95.0}
        no_expired = {**_GOOD_DECISION, "expired": 0}

        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="HIGH"),
            patch(f"{module}.gate_pass_rate_from", return_value=high_gates),
            patch(f"{module}._git_log_stat", return_value=high_git),
            patch(f"{module}._dora_metrics", return_value=high_dora),
            patch(f"{module}.scan_metrics_from", return_value=high_scan),
            patch(f"{module}.decision_store_health", return_value=no_expired),
        ):
            output = observe_health(tmp_path)

        # gate=100, velocity=100, scan=95, decision=100, dora=100
        # (100+100+95+100+100)/5 = 99
        assert "GREEN" in output

    def test_red_score_all_low(self, tmp_path: Path) -> None:
        """Health score RED when components are poor."""
        low_gates = {**_GATES, "pass_rate": 20.0}
        low_git = {"commits": 1, "commits_per_week": 0.5, "period_days": 30}
        low_dora = {**_DORA, "deployment_frequency_per_week": 0.1}

        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=low_gates),
            patch(f"{module}._git_log_stat", return_value=low_git),
            patch(f"{module}._dora_metrics", return_value=low_dora),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
        ):
            output = observe_health(tmp_path)

        # gate=20, velocity=5, dora=25
        # (20+5+25)/3 = 16.67 => 17
        assert "RED" in output

    def test_decision_health_capped_at_zero(self, tmp_path: Path) -> None:
        """Decision score floors at 0 when many expired decisions."""
        many_expired = {**_GOOD_DECISION, "expired": 10}
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=many_expired),
        ):
            output = observe_health(tmp_path)

        # decision_score = max(0, 100 - 10*20) = max(0, -100) = 0
        assert "Decision health: 0/100" in output

    def test_semaphore_section_format(self, tmp_path: Path) -> None:
        """Health dashboard uses new semaphore format."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
        ):
            output = observe_health(tmp_path)

        assert "## Semaphore:" in output

    def test_component_scores_displayed(self, tmp_path: Path) -> None:
        """Health dashboard shows arrow notation for component scores."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
        ):
            output = observe_health(tmp_path)

        assert "Gate pass rate: 90.0% -> 90.0/100" in output
        assert "Delivery velocity: 5.0/week -> 50.0/100" in output
        assert "DORA frequency: 2.0/week -> 75/100" in output

    def test_dora_score_elite(self, tmp_path: Path) -> None:
        """DORA frequency score is 100 when freq >= 5."""
        high_dora = {**_DORA, "deployment_frequency_per_week": 6.0}
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=high_dora),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
        ):
            output = observe_health(tmp_path)

        assert "DORA frequency: 6.0/week -> 100/100" in output

    def test_dora_score_low(self, tmp_path: Path) -> None:
        """DORA frequency score is 25 when freq < 0.25."""
        low_dora = {**_DORA, "deployment_frequency_per_week": 0.1}
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=low_dora),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
        ):
            output = observe_health(tmp_path)

        assert "DORA frequency: 0.1/week -> 25/100" in output
