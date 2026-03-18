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

_EMPTY_NOISE = {
    "total_failures": 0,
    "fixable_failures": 0,
    "noise_ratio_pct": 0.0,
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

# Shared mocks for security/test confidence (needed by observe_engineer)
_EMPTY_SECURITY = {
    "source": "none",
    "vulnerabilities": 0,
    "security_hotspots": 0,
    "security_rating": "N/A",
    "dep_vulns": 0,
}

_EMPTY_TEST_CONFIDENCE = {
    "source": "none",
    "coverage_pct": 0,
    "files_covered": 0,
    "files_total": 0,
    "meets_threshold": False,
    "untested_critical": [],
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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        cq = result["code_quality"]
        assert cq["avg_quality_score"] == 85.0
        assert cq["avg_security_score"] == 92.0
        assert cq["findings"]["critical"] == 1
        assert cq["findings"]["high"] == 3

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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        ba = result["build_activity"]
        assert ba["total_builds"] == 12
        assert ba["files_changed"] == 45
        assert ba["tests_added"] == 15

    def test_no_scan_data_message(self, tmp_path: Path) -> None:
        """Engineer dashboard shows zero scans when no scan events."""
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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        assert result["code_quality"]["total_scans"] == 0
        assert result["code_quality"]["findings"] is None

    def test_no_build_data_message(self, tmp_path: Path) -> None:
        """Engineer dashboard shows zero builds when no build events."""
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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        assert result["build_activity"]["total_builds"] == 0

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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        lt = result["lead_time"]
        assert lt["median_days"] == 2.5
        assert lt["rating"] == "HIGH"
        assert lt["merges_analyzed"] == 8

    def test_lead_time_insufficient_data(self, tmp_path: Path) -> None:
        """Engineer dashboard shows zero merges when no merge data."""
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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        assert result["lead_time"]["merges_analyzed"] == 0

    def test_lead_time_in_delivery_velocity(self, tmp_path: Path) -> None:
        """Engineer dashboard shows lead time in delivery_velocity dict."""
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
            patch(f"{module}._sonar_metrics_data", return_value={"available": False}),
            patch(f"{module}.security_posture_metrics", return_value=_EMPTY_SECURITY),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
        ):
            result = observe_engineer(tmp_path)

        assert result["delivery_velocity"]["lead_time_median_days"] == 2.5


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
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        ds = result["decision_store"]
        assert ds["active"] == 5
        assert ds["expired"] == 2
        assert ds["resolved"] == 3
        assert ds["avg_age_days"] == 14.5

    def test_decision_store_no_decisions(self, tmp_path: Path) -> None:
        """Team dashboard shows zero total when no decisions."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        assert result["decision_store"]["total"] == 0

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
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        ad = result["adoption"]
        assert ad["stacks"] == ["python", "typescript"]
        assert ad["primary_provider"] == "anthropic"
        assert ad["ides"] == ["claude-code", "cursor"]
        assert ad["hooks_status"] == "installed/verified"

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
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        assert result["adoption"]["hooks_status"] == "not installed"

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
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        assert result["adoption"]["hooks_status"] == "installed/unverified"

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
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        sh = result["scan_health"]
        assert sh["avg_quality_score"] == 85.0
        assert sh["total_scans"] == 5

    def test_scan_health_no_data(self, tmp_path: Path) -> None:
        """Team dashboard shows zero scans when no scan data."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.adoption_metrics", return_value=_EMPTY_ADOPTION),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        assert result["scan_health"]["total_scans"] == 0

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
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
        ):
            result = observe_team(tmp_path)

        assert "deploy_events" in result["event_distribution"]


# ---------------------------------------------------------------------------
# 6.3 — AI: expanded Context Efficiency, Session Recovery
# ---------------------------------------------------------------------------


class TestAiNewSections:
    """Tests for new sections in observe_ai."""

    def test_expanded_context_efficiency(self, tmp_path: Path) -> None:
        """AI dashboard shows expanded context efficiency with utilization."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
        ):
            result = observe_ai(tmp_path)

        ce = result["context_efficiency"]
        assert ce["sessions_analyzed"] == 0
        assert ce["total_tokens"] == 0

    def test_context_efficiency_no_skills(self, tmp_path: Path) -> None:
        """AI dashboard shows empty skills list when no skills loaded."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.filter_events", return_value=[]),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
        ):
            result = observe_ai(tmp_path)

        assert result["context_efficiency"]["skills_loaded"] == []


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
            result = observe_dora(tmp_path)

        lt = result["lead_time"]
        assert lt["median_days"] == 2.5
        assert lt["rating"] == "HIGH"

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
            result = observe_dora(tmp_path)

        cfr = result["change_failure_rate"]
        assert cfr["total_deploys"] == 20
        assert cfr["rollbacks"] == 3
        assert cfr["rate_pct"] == 15.0
        assert cfr["rating"] == "ELITE"  # 15.0% <= 15 => ELITE

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
            result = observe_dora(tmp_path)

        assert result["change_failure_rate"]["rating"] == "HIGH"

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
            result = observe_dora(tmp_path)

        assert result["change_failure_rate"]["rating"] == "MEDIUM"

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
            result = observe_dora(tmp_path)

        assert result["change_failure_rate"]["rating"] == "LOW"

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
            result = observe_dora(tmp_path)

        assert result["change_failure_rate"]["rate_pct"] == 0.0


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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        # gate=90, velocity=min(5.0*10,100)=50, dora=75 (freq 2.0 >= 1)
        # 3 components: (90 + 50 + 75) / 3 = 71.67 => round => 72
        assert result["score"] == 72
        assert result["semaphore"] == "YELLOW"
        assert result["components"].get("Scan quality") is None
        assert result["component_details"]["scan_score"] is None
        assert result["component_details"]["decision_score"] is None

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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        # gate=90, velocity=50, scan=85, decision=max(0,100-2*20)=60, dora=75
        # 5 components: (90 + 50 + 85 + 60 + 75) / 5 = 72
        assert result["score"] == 72
        assert result["semaphore"] == "YELLOW"
        assert result["components"]["Scan quality"] == 85.0
        assert result["component_details"]["decision_score"] == 60

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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        # gate=100, velocity=100, scan=95, decision=100, dora=100
        # (100+100+95+100+100)/5 = 99
        assert result["semaphore"] == "GREEN"

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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        # gate=20, velocity=5, dora=25
        # (20+5+25)/3 = 16.67 => 17
        assert result["semaphore"] == "RED"

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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        # decision_score = max(0, 100 - 10*20) = max(0, -100) = 0
        assert result["component_details"]["decision_score"] == 0

    def test_semaphore_section_format(self, tmp_path: Path) -> None:
        """Health dashboard uses semaphore field."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        assert "semaphore" in result
        assert result["semaphore"] in {"GREEN", "YELLOW", "RED"}

    def test_component_scores_displayed(self, tmp_path: Path) -> None:
        """Health dashboard shows component scores in components dict."""
        module = "ai_engineering.cli_commands.observe"
        with (
            patch(f"{module}.load_all_events", return_value=[]),
            patch(f"{module}.data_quality_from", return_value="LOW"),
            patch(f"{module}.gate_pass_rate_from", return_value=_GATES),
            patch(f"{module}._git_log_stat", return_value=_GIT_STATS),
            patch(f"{module}._dora_metrics", return_value=_DORA),
            patch(f"{module}.scan_metrics_from", return_value=_EMPTY_SCAN),
            patch(f"{module}.decision_store_health", return_value=_EMPTY_DECISION),
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        assert result["components"]["Gate pass rate"] == 90.0
        assert result["components"]["Delivery velocity"] == 50.0
        assert result["components"]["DORA frequency"] == 75

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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        assert result["components"]["DORA frequency"] == 100

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
            patch(f"{module}.sonar_detailed_metrics", return_value={"available": False}),
            patch(f"{module}.test_confidence_metrics", return_value=_EMPTY_TEST_CONFIDENCE),
            patch(f"{module}.noise_ratio_from", return_value=_EMPTY_NOISE),
            patch(f"{module}.load_health_history", return_value=[]),
            patch(f"{module}.health_direction", return_value="stable"),
            patch(f"{module}.save_health_snapshot"),
        ):
            result = observe_health(tmp_path)

        assert result["components"]["DORA frequency"] == 25
