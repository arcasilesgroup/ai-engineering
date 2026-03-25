"""Unit tests for signal aggregation functions in ai_engineering.lib.signals.

Tests the 8 aggregation functions added in spec-039 Phase 5:
- scan_metrics_from (event-based)
- build_metrics_from (event-based)
- deploy_metrics_from (event-based)
- decision_store_health (file-based)
- adoption_metrics (file-based)
- lead_time_metrics (git-based)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.lib.signals import (
    adoption_metrics,
    build_metrics_from,
    decision_store_health,
    deploy_metrics_from,
    lead_time_metrics,
    scan_metrics_from,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(days_ago: int = 0) -> str:
    """Return an ISO timestamp N days ago."""
    dt = datetime.now(tz=UTC) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(
    event_type: str,
    detail: dict | None = None,
    days_ago: int = 0,
) -> dict:
    """Build a minimal audit event dict."""
    e: dict = {
        "event": event_type,
        "actor": "test",
        "timestamp": _ts(days_ago),
    }
    if detail is not None:
        e["detail"] = detail
    return e


def _write_json(path: Path, data: dict) -> None:
    """Write JSON to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# 5.1 scan_metrics_from
# ---------------------------------------------------------------------------


class TestScanMetricsFrom:
    """Tests for scan_metrics_from()."""

    def test_normal_case(self) -> None:
        # Arrange
        events = [
            _event(
                "scan_complete",
                {
                    "score": 85.0,
                    "mode": "quality",
                    "findings": {"critical": 0, "high": 1, "medium": 2, "low": 3},
                },
                days_ago=1,
            ),
            _event(
                "scan_complete",
                {
                    "score": 90.0,
                    "mode": "security",
                    "findings": {"critical": 1, "high": 0, "medium": 1, "low": 0},
                },
                days_ago=2,
            ),
            _event(
                "scan_complete",
                {
                    "score": 70.0,
                    "mode": "security",
                    "findings": {"critical": 0, "high": 0, "medium": 0, "low": 5},
                },
                days_ago=3,
            ),
        ]

        # Act
        result = scan_metrics_from(events, days=30)

        # Assert
        assert result["total_scans"] == 3
        assert result["avg_quality_score"] == pytest.approx(81.67, abs=0.01)
        assert result["avg_security_score"] == pytest.approx(80.0, abs=0.01)
        assert result["findings"]["critical"] == 1
        assert result["findings"]["high"] == 1
        assert result["findings"]["medium"] == 3
        assert result["findings"]["low"] == 8
        assert sorted(result["modes_scanned"]) == ["quality", "security"]

    def test_empty_events(self) -> None:
        result = scan_metrics_from([], days=30)

        assert result["total_scans"] == 0
        assert result["avg_quality_score"] == 0.0
        assert result["avg_security_score"] == 0.0
        assert result["findings"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}
        assert result["modes_scanned"] == []

    def test_events_outside_window(self) -> None:
        events = [
            _event("scan_complete", {"score": 90.0, "mode": "quality"}, days_ago=60),
        ]
        result = scan_metrics_from(events, days=30)

        assert result["total_scans"] == 0

    def test_missing_score_field(self) -> None:
        events = [
            _event("scan_complete", {"mode": "quality"}, days_ago=1),
        ]
        result = scan_metrics_from(events, days=30)

        assert result["total_scans"] == 1
        assert result["avg_quality_score"] == 0.0

    def test_missing_findings_field(self) -> None:
        events = [
            _event("scan_complete", {"score": 80.0, "mode": "quality"}, days_ago=1),
        ]
        result = scan_metrics_from(events, days=30)

        assert result["findings"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}

    def test_non_scan_events_excluded(self) -> None:
        events = [
            _event("build_complete", {"files_changed": 5}, days_ago=1),
            _event("scan_complete", {"score": 95.0, "mode": "quality"}, days_ago=1),
        ]
        result = scan_metrics_from(events, days=30)

        assert result["total_scans"] == 1


# ---------------------------------------------------------------------------
# 5.2 build_metrics_from
# ---------------------------------------------------------------------------


class TestBuildMetricsFrom:
    """Tests for build_metrics_from()."""

    def test_normal_case(self) -> None:
        # Arrange
        events = [
            _event(
                "build_complete",
                {"files_changed": 10, "lines_added": 200, "lines_removed": 50, "tests_added": 5},
                days_ago=1,
            ),
            _event(
                "build_complete",
                {"files_changed": 3, "lines_added": 30, "lines_removed": 10, "tests_added": 2},
                days_ago=2,
            ),
        ]

        # Act
        result = build_metrics_from(events, days=30)

        # Assert
        assert result["total_builds"] == 2
        assert result["files_changed"] == 13
        assert result["lines_added"] == 230
        assert result["lines_removed"] == 60
        assert result["tests_added"] == 7

    def test_empty_events(self) -> None:
        result = build_metrics_from([], days=30)

        assert result["total_builds"] == 0
        assert result["files_changed"] == 0
        assert result["lines_added"] == 0
        assert result["lines_removed"] == 0
        assert result["tests_added"] == 0

    def test_missing_detail_fields(self) -> None:
        events = [
            _event("build_complete", {"files_changed": 5}, days_ago=1),
        ]
        result = build_metrics_from(events, days=30)

        assert result["total_builds"] == 1
        assert result["files_changed"] == 5
        assert result["lines_added"] == 0
        assert result["tests_added"] == 0

    def test_events_outside_window(self) -> None:
        events = [
            _event("build_complete", {"files_changed": 10}, days_ago=45),
        ]
        result = build_metrics_from(events, days=30)

        assert result["total_builds"] == 0

    def test_invalid_field_values(self) -> None:
        events = [
            _event(
                "build_complete", {"files_changed": "not_a_number", "lines_added": 10}, days_ago=1
            ),
        ]
        result = build_metrics_from(events, days=30)

        assert result["total_builds"] == 1
        assert result["files_changed"] == 0
        assert result["lines_added"] == 10


# ---------------------------------------------------------------------------
# 5.3 deploy_metrics_from
# ---------------------------------------------------------------------------


class TestDeployMetricsFrom:
    """Tests for deploy_metrics_from()."""

    def test_normal_case(self) -> None:
        # Arrange
        events = [
            _event("deploy_complete", {"rollback": False, "strategy": "blue-green"}, days_ago=1),
            _event("deploy_complete", {"rollback": True, "strategy": "rolling"}, days_ago=2),
            _event("deploy_complete", {"rollback": False, "strategy": "blue-green"}, days_ago=3),
        ]

        # Act
        result = deploy_metrics_from(events, days=30)

        # Assert
        assert result["total_deploys"] == 3
        assert result["rollbacks"] == 1
        assert result["failure_rate"] == pytest.approx(33.3, abs=0.1)
        assert result["strategies"] == {"blue-green": 2, "rolling": 1}

    def test_empty_events(self) -> None:
        result = deploy_metrics_from([], days=30)

        assert result["total_deploys"] == 0
        assert result["rollbacks"] == 0
        assert result["failure_rate"] == 0.0
        assert result["strategies"] == {}

    def test_no_rollbacks(self) -> None:
        events = [
            _event("deploy_complete", {"rollback": False, "strategy": "canary"}, days_ago=1),
            _event("deploy_complete", {"rollback": False, "strategy": "canary"}, days_ago=2),
        ]
        result = deploy_metrics_from(events, days=30)

        assert result["failure_rate"] == 0.0
        assert result["rollbacks"] == 0

    def test_all_rollbacks(self) -> None:
        events = [
            _event("deploy_complete", {"rollback": True, "strategy": "rolling"}, days_ago=1),
        ]
        result = deploy_metrics_from(events, days=30)

        assert result["failure_rate"] == 100.0
        assert result["rollbacks"] == 1

    def test_missing_strategy(self) -> None:
        events = [
            _event("deploy_complete", {"rollback": False}, days_ago=1),
        ]
        result = deploy_metrics_from(events, days=30)

        assert result["strategies"] == {}


# ---------------------------------------------------------------------------
# 5.5 decision_store_health
# ---------------------------------------------------------------------------


class TestDecisionStoreHealth:
    """Tests for decision_store_health()."""

    def test_normal_case(self, tmp_path: Path) -> None:
        # Arrange
        now = datetime.now(tz=UTC)
        future = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        past = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        created = (now - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")

        data = {
            "schemaVersion": "1.1",
            "decisions": [
                {
                    "id": "d1",
                    "status": "active",
                    "expiresAt": future,
                    "decidedAt": created,
                },
                {
                    "id": "d2",
                    "status": "active",
                    "expiresAt": past,
                    "decidedAt": created,
                },
                {
                    "id": "d3",
                    "status": "resolved",
                    "expiresAt": future,
                    "decidedAt": created,
                },
            ],
        }
        _write_json(
            tmp_path / ".ai-engineering" / "state" / "decision-store.json",
            data,
        )

        # Act
        result = decision_store_health(tmp_path)

        # Assert
        assert result["total"] == 3
        assert result["active"] == 1
        assert result["expired"] == 1
        assert result["resolved"] == 1
        assert result["avg_age_days"] == pytest.approx(20, abs=1)

    def test_empty_decisions(self, tmp_path: Path) -> None:
        # Arrange
        data = {"schemaVersion": "1.1", "decisions": []}
        _write_json(
            tmp_path / ".ai-engineering" / "state" / "decision-store.json",
            data,
        )

        # Act
        result = decision_store_health(tmp_path)

        # Assert
        assert result["total"] == 0
        assert result["active"] == 0

    def test_file_not_found(self, tmp_path: Path) -> None:
        result = decision_store_health(tmp_path)

        assert result["total"] == 0
        assert result["active"] == 0

    def test_corrupt_json(self, tmp_path: Path) -> None:
        # Arrange
        path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{invalid json", encoding="utf-8")

        # Act
        result = decision_store_health(tmp_path)

        # Assert
        assert result["total"] == 0

    def test_remediated_counted_as_resolved(self, tmp_path: Path) -> None:
        # Arrange
        now = datetime.now(tz=UTC)
        future = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        created = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        data = {
            "schemaVersion": "1.1",
            "decisions": [
                {
                    "id": "d1",
                    "status": "remediated",
                    "expiresAt": future,
                    "decidedAt": created,
                },
            ],
        }
        _write_json(
            tmp_path / ".ai-engineering" / "state" / "decision-store.json",
            data,
        )

        # Act
        result = decision_store_health(tmp_path)

        # Assert
        assert result["resolved"] == 1

    def test_no_expires_at(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        created = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

        data = {
            "schemaVersion": "1.1",
            "decisions": [
                {"id": "d1", "status": "active", "decidedAt": created},
            ],
        }
        _write_json(
            tmp_path / ".ai-engineering" / "state" / "decision-store.json",
            data,
        )
        result = decision_store_health(tmp_path)

        assert result["active"] == 1
        assert result["expired"] == 0


# ---------------------------------------------------------------------------
# 5.6 adoption_metrics
# ---------------------------------------------------------------------------


class TestAdoptionMetrics:
    """Tests for adoption_metrics()."""

    def _setup_project(self, tmp_path: Path, *, stacks: list[str], ides: list[str]) -> None:
        """Create manifest.yml and install-state.json for adoption metric tests."""
        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True, exist_ok=True)
        stacks_yaml = "\n".join(f"    - {s}" for s in stacks) if stacks else "  []"
        ides_yaml = "\n".join(f"    - {i}" for i in ides) if ides else "  []"
        content = (
            f"schema_version: '2.0'\nproviders:\n  vcs: github\n"
            f"  stacks:\n{stacks_yaml}\n  ides:\n{ides_yaml}\n"
        )
        (ai_dir / "manifest.yml").write_text(content)
        state_dir = ai_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        _write_json(state_dir / "install-state.json", {"schema_version": "2.0"})

    def test_normal_case(self, tmp_path: Path) -> None:
        self._setup_project(
            tmp_path,
            stacks=["python", "nextjs"],
            ides=["vscode", "terminal"],
        )
        result = adoption_metrics(tmp_path)
        assert result["stacks"] == ["python", "nextjs"]
        assert result["ides"] == ["vscode", "terminal"]
        assert result["providers"]["primary"] == "github"

    def test_file_not_found(self, tmp_path: Path) -> None:
        result = adoption_metrics(tmp_path)
        # ManifestConfig returns defaults when no manifest.yml exists
        assert result["stacks"] == ["python"]
        assert result["hooks_installed"] is False

    def test_minimal_config(self, tmp_path: Path) -> None:
        self._setup_project(tmp_path, stacks=["python"], ides=[])
        result = adoption_metrics(tmp_path)
        assert result["stacks"] == ["python"]

    def test_corrupt_json(self, tmp_path: Path) -> None:
        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "manifest.yml").write_text("not: valid: yaml: [")
        state_dir = ai_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("not json", encoding="utf-8")
        result = adoption_metrics(tmp_path)
        assert result["stacks"] == []
        assert result["hooks_installed"] is False


# ---------------------------------------------------------------------------
# 5.8 lead_time_metrics
# ---------------------------------------------------------------------------


class TestLeadTimeMetrics:
    """Tests for lead_time_metrics()."""

    def test_normal_case(self, tmp_path: Path) -> None:
        # Arrange
        now = datetime.now(tz=UTC)
        merge1_date = now - timedelta(days=2)
        merge2_date = now - timedelta(days=5)
        branch1_first = merge1_date - timedelta(hours=12)
        branch2_first = merge2_date - timedelta(days=3)

        merge_output = f"abc123 {merge1_date.isoformat()}\ndef456 {merge2_date.isoformat()}\n"

        def mock_run(cmd, *, capture_output=True, text=True, cwd=None, timeout=None):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.returncode = 0

            if "--merges" in cmd:
                result.stdout = merge_output
            elif "abc123^2" in cmd:
                result.stdout = f"{branch1_first.isoformat()}\n"
            elif "def456^2" in cmd:
                result.stdout = f"{branch2_first.isoformat()}\n"
            else:
                result.stdout = ""
                result.returncode = 1
            return result

        # Act
        with patch("subprocess.run", side_effect=mock_run):
            result = lead_time_metrics(tmp_path, days=30)

        # Assert
        assert result["merges_analyzed"] == 2
        assert result["median_days"] > 0
        assert result["rating"] in ("ELITE", "HIGH", "MEDIUM", "LOW")

    def test_no_merges(self, tmp_path: Path) -> None:
        def mock_run(cmd, *, capture_output=True, text=True, cwd=None, timeout=None):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = lead_time_metrics(tmp_path, days=30)

        assert result["merges_analyzed"] == 0
        assert result["median_days"] == 0
        assert result["rating"] == "LOW"

    def test_git_not_available(self, tmp_path: Path) -> None:
        def mock_run(cmd, *, capture_output=True, text=True, cwd=None, timeout=None):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.returncode = 128
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = lead_time_metrics(tmp_path, days=30)

        assert result["merges_analyzed"] == 0
        assert result["rating"] == "LOW"

    def test_subprocess_exception(self, tmp_path: Path) -> None:
        with patch(
            "subprocess.run",
            side_effect=OSError("git not found"),
        ):
            result = lead_time_metrics(tmp_path, days=30)

        assert result["merges_analyzed"] == 0
        assert result["rating"] == "LOW"

    def test_elite_rating(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        merge_date = now - timedelta(days=1)
        branch_first = merge_date - timedelta(hours=2)  # 0.08 days lead time

        def mock_run(cmd, *, capture_output=True, text=True, cwd=None, timeout=None):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.returncode = 0

            if "--merges" in cmd:
                result.stdout = f"abc123 {merge_date.isoformat()}\n"
            elif "abc123^2" in cmd:
                result.stdout = f"{branch_first.isoformat()}\n"
            else:
                result.stdout = ""
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = lead_time_metrics(tmp_path, days=30)

        assert result["rating"] == "ELITE"
        assert result["median_days"] < 1

    def test_low_rating(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        merge_date = now - timedelta(days=1)
        branch_first = merge_date - timedelta(days=45)  # 45 days lead time

        def mock_run(cmd, *, capture_output=True, text=True, cwd=None, timeout=None):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.returncode = 0

            if "--merges" in cmd:
                result.stdout = f"abc123 {merge_date.isoformat()}\n"
            elif "abc123^2" in cmd:
                result.stdout = f"{branch_first.isoformat()}\n"
            else:
                result.stdout = ""
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = lead_time_metrics(tmp_path, days=60)

        assert result["rating"] == "LOW"
        assert result["median_days"] >= 30

    def test_invalid_merge_line_format(self, tmp_path: Path) -> None:
        def mock_run(cmd, *, capture_output=True, text=True, cwd=None, timeout=None):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.returncode = 0

            if "--merges" in cmd:
                result.stdout = "invalid_line_no_space\n"
            else:
                result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            result = lead_time_metrics(tmp_path, days=30)

        assert result["merges_analyzed"] == 0
        assert result["rating"] == "LOW"


# ---------------------------------------------------------------------------
# guard_advisory_from
# ---------------------------------------------------------------------------


class TestGuardAdvisoryFrom:
    """Tests for guard_advisory_from aggregator."""

    def test_no_events_returns_zeros(self) -> None:
        from ai_engineering.lib.signals import guard_advisory_from

        result = guard_advisory_from([])
        assert result["total_advisories"] == 0
        assert result["total_warnings"] == 0
        assert result["total_concerns"] == 0

    def test_aggregates_warnings_and_concerns(self) -> None:
        from ai_engineering.lib.signals import guard_advisory_from

        now = datetime.now(tz=UTC).isoformat()
        events = [
            {
                "event": "guard_advisory",
                "timestamp": now,
                "detail": {"warnings": 3, "concerns": 1},
            },
            {
                "event": "guard_advisory",
                "timestamp": now,
                "detail": {"warnings": 2, "concerns": 4},
            },
        ]
        result = guard_advisory_from(events)
        assert result["total_advisories"] == 2
        assert result["total_warnings"] == 5
        assert result["total_concerns"] == 5

    def test_excludes_old_events(self) -> None:
        from ai_engineering.lib.signals import guard_advisory_from

        old = (datetime.now(tz=UTC) - timedelta(days=60)).isoformat()
        events = [
            {"event": "guard_advisory", "timestamp": old, "detail": {"warnings": 10}},
        ]
        result = guard_advisory_from(events, days=30)
        assert result["total_advisories"] == 0


# ---------------------------------------------------------------------------
# guard_drift_from
# ---------------------------------------------------------------------------


class TestGuardDriftFrom:
    """Tests for guard_drift_from aggregator."""

    def test_no_events_returns_zeros(self) -> None:
        from ai_engineering.lib.signals import guard_drift_from

        result = guard_drift_from([])
        assert result["total_checks"] == 0
        assert result["alignment_pct"] == 0.0

    def test_perfect_alignment(self) -> None:
        from ai_engineering.lib.signals import guard_drift_from

        now = datetime.now(tz=UTC).isoformat()
        events = [
            {
                "event": "guard_drift",
                "timestamp": now,
                "detail": {"decisions_checked": 10, "drifted": 0, "critical": 0},
            },
        ]
        result = guard_drift_from(events)
        assert result["total_checks"] == 1
        assert result["total_decisions_checked"] == 10
        assert result["total_drifted"] == 0
        assert result["alignment_pct"] == 100.0

    def test_partial_drift(self) -> None:
        from ai_engineering.lib.signals import guard_drift_from

        now = datetime.now(tz=UTC).isoformat()
        events = [
            {
                "event": "guard_drift",
                "timestamp": now,
                "detail": {"decisions_checked": 10, "drifted": 3, "critical": 1},
            },
        ]
        result = guard_drift_from(events)
        assert result["total_drifted"] == 3
        assert result["total_critical"] == 1
        assert result["alignment_pct"] == 70.0

    def test_multiple_events_aggregate(self) -> None:
        from ai_engineering.lib.signals import guard_drift_from

        now = datetime.now(tz=UTC).isoformat()
        events = [
            {
                "event": "guard_drift",
                "timestamp": now,
                "detail": {"decisions_checked": 5, "drifted": 1, "critical": 0},
            },
            {
                "event": "guard_drift",
                "timestamp": now,
                "detail": {"decisions_checked": 5, "drifted": 1, "critical": 1},
            },
        ]
        result = guard_drift_from(events)
        assert result["total_checks"] == 2
        assert result["total_decisions_checked"] == 10
        assert result["total_drifted"] == 2
        assert result["total_critical"] == 1
        assert result["alignment_pct"] == 80.0
