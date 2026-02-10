"""Tests for skills service and maintenance report.

Covers:
- Remote source sync with checksum verification.
- Offline fallback from cache.
- Allowlist (trusted) enforcement.
- Source add/remove/list operations.
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
from ai_engineering.skills.service import (
    SyncResult,
    add_source,
    list_sources,
    load_sources_lock,
    remove_source,
    sync_sources,
)
from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import CacheConfig, RemoteSource

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Create a fully installed project for testing."""
    install(tmp_path, stacks=["python"], ides=["vscode"])
    return tmp_path


@pytest.fixture()
def project_with_sources(installed_project: Path) -> Path:
    """Installed project with a sources.lock.json containing test sources."""
    lock = load_sources_lock(installed_project)
    lock.default_remote_enabled = True
    lock.sources = [
        RemoteSource(
            url="https://example.com/skill-a.md",
            trusted=True,
            checksum="",
            cache=CacheConfig(),
        ),
        RemoteSource(
            url="https://example.com/skill-b.md",
            trusted=False,
            checksum="",
            cache=CacheConfig(),
        ),
    ]
    lock_path = installed_project / ".ai-engineering" / "state" / "sources.lock.json"
    write_json_model(lock_path, lock)
    return installed_project


# ---------------------------------------------------------------------------
# Skills — Sync
# ---------------------------------------------------------------------------


class TestSyncSources:
    """Tests for the sync_sources function."""

    def test_untrusted_sources_are_skipped(
        self,
        project_with_sources: Path,
    ) -> None:
        with patch(
            "ai_engineering.skills.service._fetch_url",
            return_value=b"content",
        ):
            result = sync_sources(project_with_sources)

        assert "https://example.com/skill-b.md" in result.untrusted
        assert "https://example.com/skill-b.md" not in result.fetched

    def test_fetch_populates_cache(
        self,
        project_with_sources: Path,
    ) -> None:
        content = b"# Skill A content"
        with patch(
            "ai_engineering.skills.service._fetch_url",
            return_value=content,
        ):
            result = sync_sources(project_with_sources)

        assert "https://example.com/skill-a.md" in result.fetched
        cache_dir = project_with_sources / ".ai-engineering" / "skills-cache"
        assert cache_dir.is_dir()
        cache_files = list(cache_dir.glob("*.cache"))
        assert len(cache_files) >= 1

    def test_checksum_mismatch_fails(
        self,
        project_with_sources: Path,
    ) -> None:
        # Set a checksum that won't match
        lock = load_sources_lock(project_with_sources)
        lock.sources[0].checksum = "badhash"
        lock_path = project_with_sources / ".ai-engineering" / "state" / "sources.lock.json"
        write_json_model(lock_path, lock)

        with patch(
            "ai_engineering.skills.service._fetch_url",
            return_value=b"content",
        ):
            result = sync_sources(project_with_sources)

        assert "https://example.com/skill-a.md" in result.failed

    def test_fetch_failure_uses_cache_fallback(
        self,
        project_with_sources: Path,
    ) -> None:
        # Pre-populate cache
        cache_dir = project_with_sources / ".ai-engineering" / "skills-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # First fetch to populate cache
        with patch(
            "ai_engineering.skills.service._fetch_url",
            return_value=b"cached content",
        ):
            sync_sources(project_with_sources)

        # Now fail the fetch — should fall back to cache
        with patch(
            "ai_engineering.skills.service._fetch_url",
            return_value=None,
        ):
            result = sync_sources(project_with_sources)

        assert "https://example.com/skill-a.md" in result.cached


class TestSyncOffline:
    """Tests for offline mode."""

    def test_offline_serves_from_cache(
        self,
        project_with_sources: Path,
    ) -> None:
        # Populate cache first
        with patch(
            "ai_engineering.skills.service._fetch_url",
            return_value=b"data",
        ):
            sync_sources(project_with_sources)

        result = sync_sources(project_with_sources, offline=True)
        assert "https://example.com/skill-a.md" in result.cached

    def test_offline_fails_without_cache(
        self,
        project_with_sources: Path,
    ) -> None:
        result = sync_sources(project_with_sources, offline=True)
        assert "https://example.com/skill-a.md" in result.failed


class TestSyncDisabled:
    """Tests for disabled remote sources."""

    def test_disabled_remote_returns_empty(
        self,
        installed_project: Path,
    ) -> None:
        lock = load_sources_lock(installed_project)
        lock.default_remote_enabled = False
        lock_path = installed_project / ".ai-engineering" / "state" / "sources.lock.json"
        write_json_model(lock_path, lock)

        result = sync_sources(installed_project)
        assert result == SyncResult()


# ---------------------------------------------------------------------------
# Skills — Source management
# ---------------------------------------------------------------------------


class TestAddSource:
    """Tests for add_source."""

    def test_add_new_source(self, installed_project: Path) -> None:
        lock = add_source(installed_project, "https://new.example.com/skill.md")
        urls = [s.url for s in lock.sources]
        assert "https://new.example.com/skill.md" in urls

    def test_add_duplicate_raises(self, installed_project: Path) -> None:
        add_source(installed_project, "https://dup.example.com/skill.md")
        with pytest.raises(ValueError, match="already exists"):
            add_source(installed_project, "https://dup.example.com/skill.md")

    def test_add_untrusted_source(self, installed_project: Path) -> None:
        lock = add_source(
            installed_project,
            "https://untrusted.example.com/skill.md",
            trusted=False,
        )
        source = next(s for s in lock.sources if s.url == "https://untrusted.example.com/skill.md")
        assert source.trusted is False


class TestRemoveSource:
    """Tests for remove_source."""

    def test_remove_existing_source(self, installed_project: Path) -> None:
        add_source(installed_project, "https://removeme.example.com/skill.md")
        lock = remove_source(
            installed_project,
            "https://removeme.example.com/skill.md",
        )
        urls = [s.url for s in lock.sources]
        assert "https://removeme.example.com/skill.md" not in urls

    def test_remove_nonexistent_raises(self, installed_project: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            remove_source(installed_project, "https://nope.example.com/skill.md")


class TestListSources:
    """Tests for list_sources."""

    def test_list_returns_all_sources(
        self,
        project_with_sources: Path,
    ) -> None:
        sources = list_sources(project_with_sources)
        urls = [s.url for s in sources]
        assert "https://example.com/skill-a.md" in urls
        assert "https://example.com/skill-b.md" in urls


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

    def test_report_counts_audit_events(
        self,
        installed_project: Path,
    ) -> None:
        report = generate_report(installed_project)
        # Install creates at least one audit entry
        assert report.recent_audit_events >= 1


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
        report = generate_report(installed_project)
        report_path = installed_project / ".ai-engineering" / "state" / "maintenance-report.md"

        # Mock subprocess to avoid real git/gh calls
        with patch(
            "ai_engineering.maintenance.report.subprocess.run",
        ) as mock_run:
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

        with patch(
            "ai_engineering.maintenance.report.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = create_maintenance_pr(installed_project, report)

        assert result is False
