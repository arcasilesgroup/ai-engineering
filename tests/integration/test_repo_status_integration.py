"""Integration tests for ai_engineering.maintenance.repo_status.

Tests run_repo_status() and get_ahead_behind() against real
temporary git repositories.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.maintenance.repo_status import (
    get_ahead_behind,
    list_local_branches_with_status,
    run_repo_status,
)


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command in cwd."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a git repo with main and a feature branch."""
    _git(["init", "-b", "main", str(tmp_path)], cwd=tmp_path)

    (tmp_path / "README.md").write_text("init")
    _git(["add", "."], cwd=tmp_path)
    _git(["commit", "-m", "init"], cwd=tmp_path)

    return tmp_path


@pytest.fixture()
def git_repo_with_branches(git_repo: Path) -> Path:
    """Create feature branches with commits ahead of main."""
    # Feature branch with commits ahead
    _git(["checkout", "-b", "feat/ahead"], cwd=git_repo)
    (git_repo / "feature.txt").write_text("feature content")
    _git(["add", "."], cwd=git_repo)
    _git(["commit", "-m", "add feature"], cwd=git_repo)
    (git_repo / "feature2.txt").write_text("more content")
    _git(["add", "."], cwd=git_repo)
    _git(["commit", "-m", "add more"], cwd=git_repo)

    # Merged branch
    _git(["checkout", "main"], cwd=git_repo)
    _git(["checkout", "-b", "feat/merged"], cwd=git_repo)
    (git_repo / "merged.txt").write_text("merged content")
    _git(["add", "."], cwd=git_repo)
    _git(["commit", "-m", "merged feature"], cwd=git_repo)
    _git(["checkout", "main"], cwd=git_repo)
    _git(["merge", "feat/merged"], cwd=git_repo)

    return git_repo


class TestGetAheadBehindIntegration:
    """Integration tests for get_ahead_behind() with real repos."""

    def test_ahead_and_behind_commits(self, git_repo_with_branches):
        """Feature branch is ahead by 2 and behind by 1 (merged commit on main)."""
        ahead, behind = get_ahead_behind(git_repo_with_branches, "feat/ahead", "main")
        assert ahead == 2
        assert behind == 1

    def test_even_branch(self, git_repo):
        """Branch at same point as main shows (0, 0)."""
        _git(["checkout", "-b", "feat/even"], cwd=git_repo)
        ahead, behind = get_ahead_behind(git_repo, "feat/even", "main")
        assert ahead == 0
        assert behind == 0


class TestRunRepoStatusIntegration:
    """Integration tests for run_repo_status()."""

    def test_basic_status(self, git_repo):
        """Status on a simple repo works."""
        result = run_repo_status(git_repo, include_prs=False)
        assert result.default_branch == "main"
        # No remote branches in a local-only repo
        assert len(result.remote_branches) == 0

    def test_local_branches_listed(self, git_repo_with_branches):
        """Local feature branches are listed."""
        result = run_repo_status(git_repo_with_branches, include_prs=False)
        branch_names = [b.name for b in result.local_branches]
        assert "feat/ahead" in branch_names
        assert "feat/merged" in branch_names

    def test_cleanup_candidates(self, git_repo_with_branches):
        """Merged branches show as cleanup candidates."""
        result = run_repo_status(git_repo_with_branches, include_prs=False)
        # feat/merged should be a cleanup candidate (ahead=0)
        assert "feat/merged" in result.cleanup_candidates

    def test_markdown_renders(self, git_repo_with_branches):
        """to_markdown produces valid output."""
        result = run_repo_status(git_repo_with_branches, include_prs=False)
        md = result.to_markdown()
        assert "## Repository Status" in md
        assert "`main`" in md


class TestListLocalBranchesWithStatus:
    """Integration tests for list_local_branches_with_status()."""

    def test_lists_non_protected(self, git_repo_with_branches):
        """Protected branches (main) are excluded."""
        branches = list_local_branches_with_status(git_repo_with_branches)
        names = [b.name for b in branches]
        assert "main" not in names

    def test_ahead_behind_populated(self, git_repo_with_branches):
        """Ahead/behind counts are populated."""
        branches = list_local_branches_with_status(git_repo_with_branches)
        ahead_branch = next((b for b in branches if b.name == "feat/ahead"), None)
        assert ahead_branch is not None
        assert ahead_branch.ahead > 0
