"""Unit tests for work-item sync service and PR description issue linking."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.vcs.protocol import VcsResult
from ai_engineering.work_items.service import (
    SyncReport,
    get_linked_issue_id,
    sync_spec_issues,
)

pytestmark = pytest.mark.unit


def _make_spec_dir(root: Path, spec_id: str, *, done: bool = False, spec_text: str = "") -> Path:
    """Create a minimal spec directory structure."""
    spec_dir = root / ".ai-engineering" / "context" / "specs" / spec_id
    spec_dir.mkdir(parents=True, exist_ok=True)
    if spec_text:
        (spec_dir / "spec.md").write_text(spec_text, encoding="utf-8")
    if done:
        (spec_dir / "done.md").write_text("Done.", encoding="utf-8")
    return spec_dir


def _mock_provider(
    *,
    find_output: str = "",
    find_success: bool = True,
    create_success: bool = True,
    close_success: bool = True,
) -> MagicMock:
    """Build a mock VCS provider with configurable issue methods."""
    provider = MagicMock()
    provider.find_issue.return_value = VcsResult(success=find_success, output=find_output)
    provider.create_issue.return_value = VcsResult(
        success=create_success, output="42" if create_success else "error"
    )
    provider.close_issue.return_value = VcsResult(
        success=close_success, output="closed" if close_success else "error"
    )
    provider.provider_name.return_value = "github"
    return provider


# ── sync_spec_issues ─────────────────────────────────────────────


class TestSyncSpecIssues:
    """Tests for sync_spec_issues."""

    def test_creates_when_not_found(self, tmp_path: Path) -> None:
        _make_spec_dir(tmp_path, "037-sync", spec_text="# Spec 037 — Sync\n## Problem\nNeed sync.")
        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "037-sync" in report.created
        provider.create_issue.assert_called_once()

    def test_skips_when_exists(self, tmp_path: Path) -> None:
        _make_spec_dir(tmp_path, "037-sync")
        provider = _mock_provider(find_output="42")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "037-sync" in report.found
        provider.create_issue.assert_not_called()

    def test_closes_when_done_md(self, tmp_path: Path) -> None:
        _make_spec_dir(tmp_path, "037-sync", done=True)
        provider = _mock_provider(find_output="42")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert "037-sync" in report.closed
        provider.close_issue.assert_called_once()

    def test_dry_run_no_writes(self, tmp_path: Path) -> None:
        _make_spec_dir(tmp_path, "037-sync")
        _make_spec_dir(tmp_path, "038-other", done=True)
        provider = _mock_provider(find_output="")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path, dry_run=True)

        # Should report what would happen but not call provider write methods
        assert len(report.created) == 2
        provider.create_issue.assert_not_called()
        provider.close_issue.assert_not_called()

    def test_handles_find_error(self, tmp_path: Path) -> None:
        _make_spec_dir(tmp_path, "037-sync")
        provider = _mock_provider(find_success=False)
        provider.find_issue.return_value = VcsResult(success=False, output="auth failed")

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        assert len(report.errors) == 1
        assert "037-sync" in report.errors[0]

    def test_skips_archive_and_special_files(self, tmp_path: Path) -> None:
        specs_dir = tmp_path / ".ai-engineering" / "context" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "_active.md").write_text("active: none", encoding="utf-8")
        (specs_dir / "_catalog.md").write_text("catalog", encoding="utf-8")
        archive_dir = specs_dir / "archive"
        archive_dir.mkdir()
        provider = _mock_provider()

        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            report = sync_spec_issues(tmp_path)

        provider.find_issue.assert_not_called()
        assert report == SyncReport()


# ── get_linked_issue_id ──────────────────────────────────────────


class TestGetLinkedIssueId:
    """Tests for get_linked_issue_id."""

    def test_returns_number(self, tmp_path: Path) -> None:
        provider = _mock_provider(find_output="42")
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            result = get_linked_issue_id(tmp_path, "037-sync")
        assert result == "42"

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        provider = _mock_provider(find_output="")
        with patch("ai_engineering.work_items.service.get_provider", return_value=provider):
            result = get_linked_issue_id(tmp_path, "037-sync")
        assert result is None


# ── PR description issue linking ─────────────────────────────────


class TestPrDescriptionIssueLink:
    """Tests for _build_issue_reference in pr_description module."""

    def test_github_closes_keyword(self, tmp_path: Path) -> None:
        from ai_engineering.vcs.pr_description import _build_issue_reference

        with (
            patch(
                "ai_engineering.work_items.service.get_provider",
                return_value=_mock_provider(find_output="7"),
            ),
            patch(
                "ai_engineering.vcs.factory.detect_from_remote",
                return_value="github",
            ),
        ):
            result = _build_issue_reference(tmp_path, "037-sync")
        assert result == "Closes #7"

    def test_azure_ab_keyword(self, tmp_path: Path) -> None:
        from ai_engineering.vcs.pr_description import _build_issue_reference

        with (
            patch(
                "ai_engineering.work_items.service.get_provider",
                return_value=_mock_provider(find_output="101"),
            ),
            patch(
                "ai_engineering.vcs.factory.detect_from_remote",
                return_value="azure_devops",
            ),
        ):
            result = _build_issue_reference(tmp_path, "037-sync")
        assert result == "AB#101"

    def test_no_issue_returns_none(self, tmp_path: Path) -> None:
        from ai_engineering.vcs.pr_description import _build_issue_reference

        with patch(
            "ai_engineering.work_items.service.get_provider",
            return_value=_mock_provider(find_output=""),
        ):
            result = _build_issue_reference(tmp_path, "037-sync")
        assert result is None
