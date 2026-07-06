"""Integration tests for hooks with real git repositories.

Tests hook installation, execution markers, and lifecycle against
actual ``git init`` repositories.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.hooks.manager import (
    _HOOK_MARKER,
    install_hooks,
    is_managed_hook,
    resolve_hooks_dir,
    uninstall_hooks,
    verify_hooks,
)
from ai_engineering.state.defaults import default_install_state
from ai_engineering.state.models import GateHook
from ai_engineering.state.service import save_install_state


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real git repository with ``git init``.

    Returns:
        Path to the repository root.
    """
    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    return tmp_path


class TestInstallHooksInRealRepo:
    """Tests for hook installation in a real git repository."""

    def test_hooks_installed_in_git_dir(self, git_repo: Path) -> None:
        result = install_hooks(git_repo)

        assert len(result.installed) == 3
        hooks_dir = git_repo / ".git" / "hooks"
        for hook in GateHook:
            hook_path = hooks_dir / hook.value
            assert hook_path.is_file()
            content = hook_path.read_text(encoding="utf-8")
            assert _HOOK_MARKER in content
            assert f"ai-eng gate {hook.value}" in content

    def test_powershell_scripts_created(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        hooks_dir = git_repo / ".git" / "hooks"
        for hook in GateHook:
            ps_path = hooks_dir / f"{hook.value}.ps1"
            assert ps_path.is_file()

    def test_idempotent_install(self, git_repo: Path) -> None:
        result1 = install_hooks(git_repo)
        result2 = install_hooks(git_repo)

        # Both installs succeed (we overwrite our own hooks)
        assert len(result1.installed) == 3
        assert len(result2.installed) == 3
        assert len(result2.skipped) == 0

    def test_verify_after_install(self, git_repo: Path) -> None:
        # Manifest must exist so install_hooks records hashes for verification
        state_dir = git_repo / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        save_install_state(state_dir, default_install_state())
        install_hooks(git_repo)
        status = verify_hooks(git_repo)
        assert all(status.values())

    def test_uninstall_removes_hooks(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        removed = uninstall_hooks(git_repo)
        assert len(removed) == 3

        status = verify_hooks(git_repo)
        assert all(v is False for v in status.values())

    def test_reinstall_after_uninstall(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        uninstall_hooks(git_repo)
        result = install_hooks(git_repo)
        assert len(result.installed) == 3

    def test_preserves_sample_hooks(self, git_repo: Path) -> None:
        """Git init creates sample hooks; install should not affect them."""
        hooks_dir = git_repo / ".git" / "hooks"
        samples = list(hooks_dir.glob("*.sample"))

        install_hooks(git_repo)

        # Sample files should still exist
        for sample in samples:
            assert sample.is_file()

    def test_managed_hook_detected_correctly(self, git_repo: Path) -> None:
        install_hooks(git_repo)
        hook_path = git_repo / ".git" / "hooks" / "pre-commit"
        assert is_managed_hook(hook_path) is True

    def test_conflict_detection_with_husky(self, git_repo: Path) -> None:
        (git_repo / ".husky").mkdir()
        result = install_hooks(git_repo)
        assert len(result.conflicts) == 1
        assert result.conflicts[0].manager == "husky"
        # Hooks still installed despite conflicts (just warned)
        assert len(result.installed) == 3


@pytest.fixture()
def linked_worktree(git_repo: Path) -> Path:
    """Add a linked worktree ``wt-1`` and return its path.

    In a linked worktree ``wt-1/.git`` is a pointer *file* (not a directory),
    so ``wt-1/.git/hooks`` does not exist — the exact CI configuration
    (``Worktree Fast (Second)``, ARC-314) that broke the naive
    ``<root>/.git/hooks`` assumption.
    """
    subprocess.run(
        ["git", "-C", str(git_repo), "config", "user.email", "t@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(git_repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(git_repo), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(git_repo), "worktree", "add", "wt-1"],
        check=True,
        capture_output=True,
    )
    return git_repo / "wt-1"


class TestInstallHooksInLinkedWorktree:
    """Hook lifecycle from a linked worktree (ARC-314 regression).

    ``git worktree add`` makes ``wt-1/.git`` a pointer file; hooks live in the
    shared common dir. Every hook operation must resolve that shared dir via
    ``git rev-parse --git-path hooks`` instead of assuming ``<root>/.git/hooks``.
    """

    def test_worktree_git_is_a_pointer_file(self, linked_worktree: Path) -> None:
        # Guard the premise: if this ever became a directory the regression
        # would silently stop being exercised.
        assert (linked_worktree / ".git").is_file()
        assert not (linked_worktree / ".git" / "hooks").exists()

    def test_resolve_points_at_shared_common_hooks(
        self, git_repo: Path, linked_worktree: Path
    ) -> None:
        resolved = resolve_hooks_dir(linked_worktree)
        assert resolved.is_dir()
        # Hooks are shared: the worktree resolves to the primary tree's dir.
        assert resolved == (git_repo / ".git" / "hooks")

    def test_install_from_worktree_succeeds(self, linked_worktree: Path) -> None:
        # Previously raised FileNotFoundError: "Git hooks directory not found".
        result = install_hooks(linked_worktree)
        assert len(result.installed) == 3

        hooks_dir = resolve_hooks_dir(linked_worktree)
        for hook in GateHook:
            hook_path = hooks_dir / hook.value
            assert hook_path.is_file()
            assert _HOOK_MARKER in hook_path.read_text(encoding="utf-8")

    def test_verify_and_uninstall_from_worktree(self, linked_worktree: Path) -> None:
        state_dir = linked_worktree / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        save_install_state(state_dir, default_install_state())

        install_hooks(linked_worktree)
        assert all(verify_hooks(linked_worktree).values())

        removed = uninstall_hooks(linked_worktree)
        assert len(removed) == 3


class TestResolveHooksDirPrimaryTree:
    """``resolve_hooks_dir`` fast-paths a primary working tree."""

    def test_primary_tree_returns_literal_hooks_dir(self, git_repo: Path) -> None:
        # ``.git`` is a real directory -> literal path, no git subprocess.
        assert resolve_hooks_dir(git_repo) == git_repo / ".git" / "hooks"

    def test_non_git_dir_falls_back_to_legacy_path(self, tmp_path: Path) -> None:
        # No ``.git`` at all: fall back to the legacy path so callers still
        # get the "not a git repository" signal (dir will not exist).
        resolved = resolve_hooks_dir(tmp_path)
        assert resolved == tmp_path / ".git" / "hooks"
        assert not resolved.exists()
