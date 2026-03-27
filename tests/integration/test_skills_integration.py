"""Tests for maintenance report.

Covers:
- Maintenance report generation.
- Staleness detection.
- Markdown report rendering.
- PR creation flow.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.installer.service import install
from ai_engineering.maintenance.report import (
    MaintenanceReport,
    StaleFile,
    create_maintenance_pr,
    generate_report,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Create a fully installed project for testing."""
    install(tmp_path, stacks=["python"], ides=["vscode"])
    return tmp_path


# ---------------------------------------------------------------------------
# Maintenance — Report generation
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Tests for generate_report."""

    def test_report_on_installed_project(
        self,
        installed_project: Path,
    ) -> None:
        report = generate_report(installed_project)
        assert report.total_governance_files >= 0
        assert report.total_state_files >= 1
        assert report.install_manifest_version != ""
        assert report.health_score >= 0.0

    def test_report_on_uninstalled_project(self, tmp_path: Path) -> None:
        report = generate_report(tmp_path)
        assert "Framework not installed" in report.warnings

    def test_report_counts_framework_events(
        self,
        installed_project: Path,
    ) -> None:
        report = generate_report(installed_project)
        # Install creates at least one framework event
        assert report.recent_framework_events >= 1


class TestStalenessDetection:
    """Tests for stale file detection."""

    def test_fresh_files_not_stale(self, installed_project: Path) -> None:
        report = generate_report(installed_project, staleness_days=90)
        assert len(report.stale_files) == 0

    def test_old_files_detected_as_stale(
        self,
        installed_project: Path,
    ) -> None:
        # Create an artificially old file
        ai_dir = installed_project / ".ai-engineering" / "standards"
        ai_dir.mkdir(parents=True, exist_ok=True)
        old_file = ai_dir / "old-standard.md"
        old_file.write_text("# Old\n", encoding="utf-8")

        import os

        old_time = (datetime.now(tz=UTC) - timedelta(days=200)).timestamp()
        os.utime(old_file, (old_time, old_time))

        report = generate_report(installed_project, staleness_days=90)
        stale_paths = [sf.path.as_posix() for sf in report.stale_files]
        assert "standards/old-standard.md" in stale_paths

    def test_custom_staleness_threshold(
        self,
        installed_project: Path,
    ) -> None:
        # With threshold of 0 days everything is stale (if governance
        # files exist); with a very large threshold nothing is stale
        report = generate_report(installed_project, staleness_days=999_999)
        assert len(report.stale_files) == 0


# ---------------------------------------------------------------------------
# Maintenance — Report rendering
# ---------------------------------------------------------------------------


class TestReportMarkdown:
    """Tests for to_markdown rendering."""

    def test_markdown_contains_header(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        md = report.to_markdown()
        assert "# Maintenance Report" in md
        assert "2025-01-01" in md

    def test_markdown_renders_stale_files(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
            stale_files=[
                StaleFile(
                    path=Path("standards/old.md"),
                    last_modified=datetime(2024, 1, 1, tzinfo=UTC),
                    age_days=365,
                ),
            ],
            total_governance_files=10,
        )
        md = report.to_markdown()
        assert "## Stale Files" in md
        assert "standards/old.md" in md
        assert "365" in md

    def test_markdown_renders_warnings(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
            warnings=["Something is wrong"],
        )
        md = report.to_markdown()
        assert "## Warnings" in md
        assert "Something is wrong" in md


class TestHealthScore:
    """Tests for the health_score property."""

    def test_perfect_health_with_no_stale(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
            total_governance_files=10,
        )
        assert report.health_score == 1.0

    def test_zero_health_with_all_stale(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
            total_governance_files=2,
            stale_files=[
                StaleFile(
                    path=Path("a.md"),
                    last_modified=datetime(2024, 1, 1, tzinfo=UTC),
                    age_days=365,
                ),
                StaleFile(
                    path=Path("b.md"),
                    last_modified=datetime(2024, 1, 1, tzinfo=UTC),
                    age_days=365,
                ),
            ],
        )
        assert report.health_score == 0.0

    def test_zero_files_gives_zero_score(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
            total_governance_files=0,
        )
        assert report.health_score == 0.0


# ---------------------------------------------------------------------------
# Maintenance — PR creation
# ---------------------------------------------------------------------------


class TestCreateMaintenancePR:
    """Tests for create_maintenance_pr."""

    def test_pr_creation_writes_report_file(
        self,
        installed_project: Path,
    ) -> None:
        from ai_engineering.vcs.protocol import VcsResult

        report = generate_report(installed_project)
        report_path = installed_project / ".ai-engineering" / "state" / "maintenance-report.md"

        mock_provider = type(
            "MockProvider",
            (),
            {"create_pr": lambda self, ctx: VcsResult(success=True, output="ok")},
        )()
        # Mock subprocess to avoid real git calls
        with (
            patch("ai_engineering.maintenance.report.subprocess.run") as mock_run,
            patch("ai_engineering.maintenance.report.get_provider", return_value=mock_provider),
        ):
            mock_run.return_value = None
            create_maintenance_pr(installed_project, report)

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Maintenance Report" in content

    def test_pr_creation_returns_false_on_failure(
        self,
        installed_project: Path,
    ) -> None:
        import subprocess

        report = generate_report(installed_project)

        # Make subprocess.run raise CalledProcessError to simulate git failure
        with patch(
            "ai_engineering.maintenance.report.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = create_maintenance_pr(installed_project, report)

        assert result is False
