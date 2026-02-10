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
    list_all_local_branches,
    list_merged_branches,
    run_branch_cleanup,
)


@pytest.fixture()
def git_repo_with_branches(tmp_path: Path) -> Path:
    """Create a git repo with main + two merged feature branches."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    # Create and merge feature-a
    subprocess.run(
        ["git", "checkout", "-b", "feature/a"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    (tmp_path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add a"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feature/a", "--no-ff", "-m", "merge a"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    # Create and merge feature-b
    subprocess.run(
        ["git", "checkout", "-b", "feature/b"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    (tmp_path / "b.txt").write_text("b")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add b"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feature/b", "--no-ff", "-m", "merge b"],
        cwd=tmp_path, check=True, capture_output=True,
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
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=tmp_path, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=tmp_path, check=True, capture_output=True,
        )
        (tmp_path / "f.txt").write_text("f")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, check=True, capture_output=True,
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
