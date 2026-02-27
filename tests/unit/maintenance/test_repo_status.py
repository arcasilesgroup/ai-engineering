"""Unit tests for ai_engineering.maintenance.repo_status.

Covers:
- list_remote_branches: parsing git branch -r output.
- get_ahead_behind: ahead-only, behind-only, diverged, even.
- list_open_prs: mocked gh output + fallback.
- detect_stale_branches: threshold filtering.
- RepoStatusResult.to_markdown: rendering.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from ai_engineering.maintenance.repo_status import (
    BranchStatus,
    PullRequestInfo,
    RepoStatusResult,
    detect_stale_branches,
    get_ahead_behind,
    list_open_prs,
)

pytestmark = pytest.mark.unit


class TestGetAheadBehind:
    """Tests for get_ahead_behind()."""

    def test_ahead_only(self, tmp_path):
        """Branch ahead returns (ahead, 0)."""
        with patch("ai_engineering.maintenance.repo_status.run_git") as mock_git:
            mock_git.return_value = (True, "0\t3")
            ahead, behind = get_ahead_behind(tmp_path, "feature/x", "main")
            assert ahead == 3
            assert behind == 0

    def test_behind_only(self, tmp_path):
        """Branch behind returns (0, behind)."""
        with patch("ai_engineering.maintenance.repo_status.run_git") as mock_git:
            mock_git.return_value = (True, "5\t0")
            ahead, behind = get_ahead_behind(tmp_path, "feature/x", "main")
            assert ahead == 0
            assert behind == 5

    def test_diverged(self, tmp_path):
        """Diverged branch returns (ahead, behind)."""
        with patch("ai_engineering.maintenance.repo_status.run_git") as mock_git:
            mock_git.return_value = (True, "2\t4")
            ahead, behind = get_ahead_behind(tmp_path, "feature/x", "main")
            assert ahead == 4
            assert behind == 2

    def test_even(self, tmp_path):
        """Even branch returns (0, 0)."""
        with patch("ai_engineering.maintenance.repo_status.run_git") as mock_git:
            mock_git.return_value = (True, "0\t0")
            ahead, behind = get_ahead_behind(tmp_path, "feature/x", "main")
            assert ahead == 0
            assert behind == 0

    def test_git_failure(self, tmp_path):
        """Git failure returns (0, 0)."""
        with patch("ai_engineering.maintenance.repo_status.run_git") as mock_git:
            mock_git.return_value = (False, "error")
            ahead, behind = get_ahead_behind(tmp_path, "feature/x", "main")
            assert ahead == 0
            assert behind == 0

    def test_malformed_output(self, tmp_path):
        """Malformed output returns (0, 0)."""
        with patch("ai_engineering.maintenance.repo_status.run_git") as mock_git:
            mock_git.return_value = (True, "not-a-number")
            ahead, behind = get_ahead_behind(tmp_path, "feature/x", "main")
            assert ahead == 0
            assert behind == 0


class TestDetectStaleBranches:
    """Tests for detect_stale_branches()."""

    def test_stale_branch_detected(self):
        """Branches older than threshold are detected as stale."""
        old_date = (datetime.now(tz=UTC) - timedelta(days=45)).strftime("%Y-%m-%d")
        branches = [
            BranchStatus(name="old-branch", last_commit_date=old_date),
        ]
        stale = detect_stale_branches(branches, threshold_days=30)
        assert len(stale) == 1
        assert stale[0].name == "old-branch"

    def test_recent_branch_not_stale(self):
        """Recent branches are not detected as stale."""
        recent_date = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
        branches = [
            BranchStatus(name="recent-branch", last_commit_date=recent_date),
        ]
        stale = detect_stale_branches(branches, threshold_days=30)
        assert len(stale) == 0

    def test_empty_date_skipped(self):
        """Branches with empty date are skipped."""
        branches = [
            BranchStatus(name="no-date", last_commit_date=""),
        ]
        stale = detect_stale_branches(branches, threshold_days=30)
        assert len(stale) == 0

    def test_mixed_branches(self):
        """Mix of stale and recent branches filters correctly."""
        old_date = (datetime.now(tz=UTC) - timedelta(days=60)).strftime("%Y-%m-%d")
        recent_date = (datetime.now(tz=UTC) - timedelta(days=3)).strftime("%Y-%m-%d")
        branches = [
            BranchStatus(name="old", last_commit_date=old_date),
            BranchStatus(name="new", last_commit_date=recent_date),
            BranchStatus(name="no-date", last_commit_date=""),
        ]
        stale = detect_stale_branches(branches, threshold_days=30)
        assert len(stale) == 1
        assert stale[0].name == "old"

    def test_custom_threshold(self):
        """Custom threshold filters correctly."""
        date_10d = (datetime.now(tz=UTC) - timedelta(days=10)).strftime("%Y-%m-%d")
        branches = [
            BranchStatus(name="branch-a", last_commit_date=date_10d),
        ]
        # 7 day threshold: branch is stale
        assert len(detect_stale_branches(branches, threshold_days=7)) == 1
        # 15 day threshold: branch is not stale
        assert len(detect_stale_branches(branches, threshold_days=15)) == 0


class TestListOpenPrs:
    """Tests for list_open_prs()."""

    def test_gh_available_with_prs(self, tmp_path):
        """Parses gh pr list JSON output correctly."""
        mock_output = (
            '[{"number": 42, "title": "Add feature", '
            '"headRefName": "feat/x", "baseRefName": "main", '
            '"author": {"login": "dev1"}}]'
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": mock_output})()
            prs = list_open_prs(tmp_path)
            assert len(prs) == 1
            assert prs[0].number == 42
            assert prs[0].title == "Add feature"
            assert prs[0].branch == "feat/x"
            assert prs[0].author == "dev1"

    def test_gh_not_available(self, tmp_path):
        """Falls back gracefully when gh is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            prs = list_open_prs(tmp_path)
            assert prs == []

    def test_gh_returns_empty(self, tmp_path):
        """Returns empty list when no open PRs."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": "[]"})()
            prs = list_open_prs(tmp_path)
            assert prs == []

    def test_gh_error(self, tmp_path):
        """Returns empty list on gh error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("Result", (), {"returncode": 1, "stdout": ""})()
            prs = list_open_prs(tmp_path)
            assert prs == []


class TestRepoStatusResultMarkdown:
    """Tests for RepoStatusResult.to_markdown()."""

    def test_empty_result_renders(self):
        """Empty result renders without errors."""
        result = RepoStatusResult(default_branch="main")
        md = result.to_markdown()
        assert "## Repository Status" in md
        assert "**Default branch**: `main`" in md
        assert "Remote branches**: 0" in md

    def test_with_prs_renders_table(self):
        """PRs are rendered as a Markdown table."""
        result = RepoStatusResult(
            default_branch="main",
            open_prs=[
                PullRequestInfo(
                    number=1,
                    title="Fix bug",
                    branch="fix/bug",
                    target="main",
                    author="dev",
                ),
            ],
        )
        md = result.to_markdown()
        assert "### Open Pull Requests" in md
        assert "Fix bug" in md
        assert "`fix/bug`" in md

    def test_with_stale_branches(self):
        """Stale branches are listed."""
        result = RepoStatusResult(
            default_branch="main",
            stale_branches=[
                BranchStatus(name="old-feat", is_remote=False, last_commit_date="2025-01-01"),
            ],
        )
        md = result.to_markdown()
        assert "### Stale Branches" in md
        assert "`old-feat`" in md

    def test_with_cleanup_candidates(self):
        """Cleanup candidates are listed."""
        result = RepoStatusResult(
            default_branch="main",
            cleanup_candidates=["merged-branch"],
        )
        md = result.to_markdown()
        assert "### Cleanup Candidates" in md
        assert "`merged-branch`" in md
