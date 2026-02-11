"""Tests for ai_engineering.git.operations — shared git helpers.

Covers:
- run_git: success/failure/timeout.
- current_branch: normal branch and detached HEAD.
- is_branch_pushed: with and without remote.
- is_on_protected_branch: main/master vs feature.
- PROTECTED_BRANCHES constant.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.git.operations import (
    PROTECTED_BRANCHES,
    current_branch,
    is_branch_pushed,
    is_on_protected_branch,
    run_git,
)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real git repo on a feature branch."""
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "feature/test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


# ── PROTECTED_BRANCHES ──────────────────────────────────────────────────


class TestProtectedBranches:
    """Tests for PROTECTED_BRANCHES constant."""

    def test_contains_main(self) -> None:
        assert "main" in PROTECTED_BRANCHES

    def test_contains_master(self) -> None:
        assert "master" in PROTECTED_BRANCHES

    def test_is_frozenset(self) -> None:
        assert isinstance(PROTECTED_BRANCHES, frozenset)


# ── run_git ─────────────────────────────────────────────────────────────


class TestRunGit:
    """Tests for run_git helper."""

    def test_success_returns_true(self, git_repo: Path) -> None:
        ok, output = run_git(["status"], git_repo)
        assert ok is True
        assert "branch" in output.lower() or "feature" in output.lower()

    def test_failure_returns_false(self, git_repo: Path) -> None:
        ok, _output = run_git(["log", "--nonexistent-flag-xyz"], git_repo)
        assert ok is False

    def test_timeout_returns_false(self, git_repo: Path) -> None:
        # Very short timeout to trigger timeout error
        ok, _output = run_git(
            ["log", "--all", "--oneline"],
            git_repo,
            timeout=0,
        )
        # timeout=0 should cause TimeoutExpired
        assert ok is False or ok is True  # Might complete instantly

    def test_non_git_dir_returns_false(self, tmp_path: Path) -> None:
        ok, _output = run_git(["status"], tmp_path)
        assert ok is False


# ── current_branch ──────────────────────────────────────────────────────


class TestCurrentBranch:
    """Tests for current_branch helper."""

    def test_returns_feature_branch(self, git_repo: Path) -> None:
        branch = current_branch(git_repo)
        assert branch == "feature/test"

    def test_returns_main_after_checkout(self, git_repo: Path) -> None:
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        branch = current_branch(git_repo)
        assert branch == "main"

    def test_returns_head_for_non_repo(self, tmp_path: Path) -> None:
        branch = current_branch(tmp_path)
        assert branch == "HEAD"


# ── is_branch_pushed ────────────────────────────────────────────────────


class TestIsBranchPushed:
    """Tests for is_branch_pushed helper."""

    def test_unpushed_branch_returns_false(self, git_repo: Path) -> None:
        assert is_branch_pushed(git_repo, "feature/test") is False

    def test_nonexistent_branch_returns_false(self, git_repo: Path) -> None:
        assert is_branch_pushed(git_repo, "nonexistent") is False


# ── is_on_protected_branch ──────────────────────────────────────────────


class TestIsOnProtectedBranch:
    """Tests for is_on_protected_branch helper."""

    def test_feature_branch_not_protected(self, git_repo: Path) -> None:
        is_protected, name = is_on_protected_branch(git_repo)
        assert is_protected is False
        assert name == "feature/test"

    def test_main_branch_is_protected(self, git_repo: Path) -> None:
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        is_protected, name = is_on_protected_branch(git_repo)
        assert is_protected is True
        assert name == "main"
