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
    uninstall_hooks,
    verify_hooks,
)
from ai_engineering.state.models import GateHook


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a real git repository with ``git init``.

    Returns:
        Path to the repository root.
    """
    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
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
