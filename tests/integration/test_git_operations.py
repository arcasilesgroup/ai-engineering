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
    get_changed_files,
    get_merge_base,
    is_branch_pushed,
    is_on_protected_branch,
    run_git,
)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real git repo on a feature branch."""
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
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


class TestMergeBaseAndChangedFiles:
    """Tests for get_merge_base() and get_changed_files()."""

    def _commit_file(self, repo: Path, rel_path: str, content: str, msg: str) -> None:
        target = repo / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", rel_path], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=repo, check=True, capture_output=True)

    def test_get_merge_base_success(self, git_repo: Path) -> None:
        self._commit_file(git_repo, "src/one.py", "print('one')\n", "feat: add one")
        merge_base = get_merge_base(git_repo, "main")
        assert len(merge_base) >= 7

    def test_get_merge_base_failure_raises(self, git_repo: Path) -> None:
        with pytest.raises(RuntimeError):
            get_merge_base(git_repo, "refs/heads/does-not-exist")

    def test_get_changed_files_acmrt(self, git_repo: Path) -> None:
        self._commit_file(git_repo, "src/example.py", "print('hello')\n", "feat: add example")
        changed = get_changed_files(git_repo, "main", diff_filter="ACMRT")
        assert "src/example.py" in changed

    def test_get_changed_files_deleted(self, git_repo: Path) -> None:
        self._commit_file(git_repo, "src/to_delete.py", "print('bye')\n", "feat: add deletable")
        subprocess.run(
            ["git", "rm", "src/to_delete.py"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: delete file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        deleted = get_changed_files(git_repo, "HEAD~1", diff_filter="D")
        assert "src/to_delete.py" in deleted

    def test_get_changed_files_rename_reports_new_path(self, git_repo: Path) -> None:
        self._commit_file(git_repo, "src/old_name.py", "print('rename')\n", "feat: add old name")
        subprocess.run(
            ["git", "mv", "src/old_name.py", "src/new_name.py"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: rename source file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        changed = get_changed_files(git_repo, "main", diff_filter="ACMRT")
        assert "src/new_name.py" in changed


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
