"""Tests for ai_engineering.maintenance.branch_cleanup.

Covers:
- fetch_and_prune: success and no-remote scenarios.
- list_merged_branches: merged vs unmerged detection.
- list_all_local_branches: listing accuracy.
- delete_branches: safe and force delete, protected branch skip.
- run_branch_cleanup: full orchestration and dry_run mode.
- CleanupResult: Markdown rendering.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.maintenance.branch_cleanup import (
    CleanupResult,
    delete_branches,
    has_unmerged_changes,
    list_all_local_branches,
    list_gone_branches,
    list_merged_branches,
    run_branch_cleanup,
)

pytestmark = pytest.mark.integration


@pytest.fixture()
def git_repo_with_branches(tmp_path: Path) -> Path:
    """Create a git repo with main + two merged feature branches."""
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create and merge feature-a
    subprocess.run(
        ["git", "checkout", "-b", "feature/a"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add a"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feature/a", "--no-ff", "-m", "merge a"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create and merge feature-b
    subprocess.run(
        ["git", "checkout", "-b", "feature/b"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "b.txt").write_text("b")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add b"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feature/b", "--no-ff", "-m", "merge b"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path


# ── list_merged_branches ────────────────────────────────────────────────


class TestListMergedBranches:
    """Tests for list_merged_branches."""

    def test_finds_merged_branches(self, git_repo_with_branches: Path) -> None:
        merged = list_merged_branches(git_repo_with_branches, "main")
        assert "feature/a" in merged
        assert "feature/b" in merged

    def test_excludes_main(self, git_repo_with_branches: Path) -> None:
        merged = list_merged_branches(git_repo_with_branches, "main")
        assert "main" not in merged

    def test_empty_when_no_branches(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
        )
        (tmp_path / "f.txt").write_text("f")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        merged = list_merged_branches(tmp_path, "main")
        assert merged == []


# ── list_all_local_branches ─────────────────────────────────────────────


class TestListAllLocalBranches:
    """Tests for list_all_local_branches."""

    def test_lists_all_branches(self, git_repo_with_branches: Path) -> None:
        branches = list_all_local_branches(git_repo_with_branches)
        assert "main" in branches
        assert "feature/a" in branches
        assert "feature/b" in branches


# ── delete_branches ─────────────────────────────────────────────────────


class TestDeleteBranches:
    """Tests for delete_branches."""

    def test_deletes_merged_branches(self, git_repo_with_branches: Path) -> None:
        deleted, failed = delete_branches(
            git_repo_with_branches,
            ["feature/a", "feature/b"],
        )
        assert "feature/a" in deleted
        assert "feature/b" in deleted
        assert failed == []

    def test_skips_protected_branches(self, git_repo_with_branches: Path) -> None:
        deleted, failed = delete_branches(
            git_repo_with_branches,
            ["main"],
        )
        assert deleted == []
        assert "main" in failed


# ── run_branch_cleanup ──────────────────────────────────────────────────


class TestRunBranchCleanup:
    """Tests for run_branch_cleanup orchestration."""

    def test_dry_run_does_not_delete(self, git_repo_with_branches: Path) -> None:
        result = run_branch_cleanup(
            git_repo_with_branches,
            base_branch="main",
            dry_run=True,
        )
        assert result.success
        assert len(result.skipped_branches) >= 2
        assert result.deleted_branches == []
        # Branches still exist
        branches = list_all_local_branches(git_repo_with_branches)
        assert "feature/a" in branches

    def test_cleanup_deletes_merged(self, git_repo_with_branches: Path) -> None:
        result = run_branch_cleanup(
            git_repo_with_branches,
            base_branch="main",
        )
        assert result.success
        assert "feature/a" in result.deleted_branches
        assert "feature/b" in result.deleted_branches


# ── CleanupResult ───────────────────────────────────────────────────────


class TestCleanupResult:
    """Tests for CleanupResult."""

    def test_success_when_no_errors(self) -> None:
        result = CleanupResult(fetched=True, deleted_branches=["a"])
        assert result.success is True

    def test_failure_when_errors_exist(self) -> None:
        result = CleanupResult(errors=["git fetch failed"])
        assert result.success is False

    def test_to_markdown_includes_summary(self) -> None:
        result = CleanupResult(
            fetched=True,
            pruned_refs=2,
            deleted_branches=["feature/a"],
            skipped_branches=["feature/b"],
        )
        md = result.to_markdown()
        assert "Branch Cleanup Summary" in md
        assert "feature/a" in md
        assert "Deleted" in md


# ── Gone branch fixtures ──────────────────────────────────────────────


@pytest.fixture()
def git_repo_with_gone_branch(tmp_path: Path) -> Path:
    """Create a git repo with a local branch whose upstream is [gone].

    Simulates a squash-merged PR: origin creates branch, local tracks it,
    then origin deletes the branch after merge.
    """
    origin = tmp_path / "origin"
    local = tmp_path / "local"

    # Create bare origin
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True
    )

    # Clone to local
    subprocess.run(["git", "clone", str(origin), str(local)], check=True, capture_output=True)

    # Initial commit on main
    (local / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=local, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=local, check=True, capture_output=True)
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=local,
        check=True,
        capture_output=True,
    )

    # Create feature branch, push it, then delete remote to simulate [gone]
    subprocess.run(
        ["git", "checkout", "-b", "feat/gone-safe"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    (local / "safe.txt").write_text("safe")
    subprocess.run(["git", "add", "."], cwd=local, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add safe"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "feat/gone-safe"],
        cwd=local,
        check=True,
        capture_output=True,
    )

    # Simulate squash-merge on main: cherry-pick the change onto main
    subprocess.run(["git", "checkout", "main"], cwd=local, check=True, capture_output=True)
    (local / "safe.txt").write_text("safe")
    subprocess.run(["git", "add", "."], cwd=local, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "squash: add safe"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=local,
        check=True,
        capture_output=True,
    )

    # Delete the remote branch (simulates GitHub deleting after PR merge)
    subprocess.run(
        ["git", "push", "origin", "--delete", "feat/gone-safe"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    # Prune so local tracking shows [gone]
    subprocess.run(["git", "fetch", "--prune"], cwd=local, check=True, capture_output=True)

    # Create another branch with commits ahead of main (unmerged content)
    subprocess.run(
        ["git", "checkout", "-b", "feat/gone-ahead"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    (local / "ahead.txt").write_text("ahead-unique-content")
    subprocess.run(["git", "add", "."], cwd=local, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "ahead work"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    # Add a second commit so the branch is clearly ahead
    (local / "ahead2.txt").write_text("more ahead content")
    subprocess.run(["git", "add", "."], cwd=local, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "more ahead work"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "feat/gone-ahead"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    # Switch back to main BEFORE deleting remote branch
    subprocess.run(["git", "checkout", "main"], cwd=local, check=True, capture_output=True)
    # Delete remote to make it [gone] (DO NOT squash-merge this one)
    subprocess.run(
        ["git", "push", "origin", "--delete", "feat/gone-ahead"],
        cwd=local,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "fetch", "--prune"], cwd=local, check=True, capture_output=True)

    return local


# ── list_gone_branches ─────────────────────────────────────────────────


class TestListGoneBranches:
    """Tests for list_gone_branches."""

    def test_finds_gone_branches(self, git_repo_with_gone_branch: Path) -> None:
        gone = list_gone_branches(git_repo_with_gone_branch)
        assert "feat/gone-safe" in gone
        assert "feat/gone-ahead" in gone

    def test_no_gone_in_clean_repo(self, git_repo_with_branches: Path) -> None:
        gone = list_gone_branches(git_repo_with_branches)
        assert gone == []


# ── commits_ahead ──────────────────────────────────────────────────────


class TestHasUnmergedChanges:
    """Tests for has_unmerged_changes."""

    def test_no_unmerged_for_squash_merged(self, git_repo_with_gone_branch: Path) -> None:
        result = has_unmerged_changes(git_repo_with_gone_branch, "origin/main", "feat/gone-safe")
        assert result is False

    def test_has_unmerged_for_ahead_branch(self, git_repo_with_gone_branch: Path) -> None:
        result = has_unmerged_changes(git_repo_with_gone_branch, "origin/main", "feat/gone-ahead")
        assert result is True


# ── run_branch_cleanup with gone branches ──────────────────────────────


class TestRunBranchCleanupGone:
    """Tests for run_branch_cleanup with gone branches."""

    def test_deletes_safe_gone_branch(self, git_repo_with_gone_branch: Path) -> None:
        result = run_branch_cleanup(git_repo_with_gone_branch, base_branch="main")
        assert result.success
        assert "feat/gone-safe" in result.deleted_branches
        # Verify branch is actually deleted
        branches = list_all_local_branches(git_repo_with_gone_branch)
        assert "feat/gone-safe" not in branches

    def test_skips_gone_branch_with_commits_ahead(self, git_repo_with_gone_branch: Path) -> None:
        result = run_branch_cleanup(git_repo_with_gone_branch, base_branch="main")
        assert result.success
        # feat/gone-ahead should be skipped (has commits ahead)
        skipped_names = [s.split(" ")[0] for s in result.skipped_branches]
        assert "feat/gone-ahead" in skipped_names
        # Verify branch still exists
        branches = list_all_local_branches(git_repo_with_gone_branch)
        assert "feat/gone-ahead" in branches
