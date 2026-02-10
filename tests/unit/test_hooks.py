"""Unit tests for hooks/manager.py — hook generation and conflict detection.

Covers:
- Bash and PowerShell hook script generation.
- Conflict detection for husky, lefthook, pre-commit.
- Hook marker identification.
- Install with create-only semantics and force mode.
- Uninstall of managed hooks.
- Hook integrity verification.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.hooks.manager import (
    _HOOK_MARKER,
    detect_conflicts,
    generate_bash_hook,
    generate_dispatcher_hook,
    generate_powershell_hook,
    install_hooks,
    is_managed_hook,
    uninstall_hooks,
    verify_hooks,
)
from ai_engineering.state.models import GateHook

# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------


class TestGenerateBashHook:
    """Tests for Bash hook script generation."""

    def test_pre_commit_contains_command(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT)
        assert "ai-eng gate pre-commit" in script
        assert script.startswith("#!/usr/bin/env bash")

    def test_commit_msg_contains_command(self) -> None:
        script = generate_bash_hook(GateHook.COMMIT_MSG)
        assert "ai-eng gate commit-msg" in script

    def test_pre_push_contains_command(self) -> None:
        script = generate_bash_hook(GateHook.PRE_PUSH)
        assert "ai-eng gate pre-push" in script

    def test_contains_marker(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT)
        assert _HOOK_MARKER in script

    def test_contains_set_euo_pipefail(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT)
        assert "set -euo pipefail" in script

    def test_passes_args(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT)
        assert '"$@"' in script


class TestGeneratePowershellHook:
    """Tests for PowerShell hook script generation."""

    def test_pre_commit_contains_command(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT)
        assert "ai-eng gate pre-commit" in script

    def test_contains_marker(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT)
        assert _HOOK_MARKER in script

    def test_contains_error_action(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT)
        assert "$ErrorActionPreference = 'Stop'" in script

    def test_checks_exit_code(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT)
        assert "$LASTEXITCODE" in script


class TestGenerateDispatcherHook:
    """Tests for cross-OS dispatcher hook generation."""

    def test_returns_bash_hook(self) -> None:
        dispatcher = generate_dispatcher_hook(GateHook.PRE_COMMIT)
        bash = generate_bash_hook(GateHook.PRE_COMMIT)
        assert dispatcher == bash


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestDetectConflicts:
    """Tests for third-party hook manager conflict detection."""

    def test_no_conflicts_on_clean_project(self, tmp_path: Path) -> None:
        conflicts = detect_conflicts(tmp_path)
        assert conflicts == []

    def test_detects_husky(self, tmp_path: Path) -> None:
        (tmp_path / ".husky").mkdir()
        conflicts = detect_conflicts(tmp_path)
        assert len(conflicts) == 1
        assert conflicts[0].manager == "husky"

    def test_detects_lefthook(self, tmp_path: Path) -> None:
        (tmp_path / "lefthook.yml").write_text("")
        conflicts = detect_conflicts(tmp_path)
        assert len(conflicts) == 1
        assert conflicts[0].manager == "lefthook"

    def test_detects_pre_commit(self, tmp_path: Path) -> None:
        (tmp_path / ".pre-commit-config.yaml").write_text("")
        conflicts = detect_conflicts(tmp_path)
        assert len(conflicts) == 1
        assert conflicts[0].manager == "pre-commit"

    def test_detects_multiple_conflicts(self, tmp_path: Path) -> None:
        (tmp_path / ".husky").mkdir()
        (tmp_path / ".pre-commit-config.yaml").write_text("")
        conflicts = detect_conflicts(tmp_path)
        managers = {c.manager for c in conflicts}
        assert "husky" in managers
        assert "pre-commit" in managers


# ---------------------------------------------------------------------------
# Hook marker
# ---------------------------------------------------------------------------


class TestIsManagedHook:
    """Tests for hook marker identification."""

    def test_identifies_managed_hook(self, tmp_path: Path) -> None:
        hook = tmp_path / "pre-commit"
        hook.write_text(f"#!/bin/bash\n{_HOOK_MARKER}\necho 'hello'")
        assert is_managed_hook(hook) is True

    def test_rejects_unmanaged_hook(self, tmp_path: Path) -> None:
        hook = tmp_path / "pre-commit"
        hook.write_text("#!/bin/bash\necho 'hello'")
        assert is_managed_hook(hook) is False

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        assert is_managed_hook(tmp_path / "nonexistent") is False

    def test_returns_false_for_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "somedir"
        d.mkdir()
        assert is_managed_hook(d) is False


# ---------------------------------------------------------------------------
# Install hooks
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_hooks_dir(tmp_path: Path) -> Path:
    """Create a .git/hooks/ directory structure."""
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return tmp_path


class TestInstallHooks:
    """Tests for hook installation."""

    def test_installs_all_hooks_by_default(self, git_hooks_dir: Path) -> None:
        result = install_hooks(git_hooks_dir)

        assert len(result.installed) == 3
        assert "pre-commit" in result.installed
        assert "commit-msg" in result.installed
        assert "pre-push" in result.installed

        for hook in GateHook:
            hook_path = git_hooks_dir / ".git" / "hooks" / hook.value
            assert hook_path.is_file()
            assert _HOOK_MARKER in hook_path.read_text()

    def test_installs_specific_hooks(self, git_hooks_dir: Path) -> None:
        result = install_hooks(git_hooks_dir, hooks=[GateHook.PRE_COMMIT])
        assert result.installed == ["pre-commit"]
        assert (git_hooks_dir / ".git" / "hooks" / "pre-commit").is_file()
        assert not (git_hooks_dir / ".git" / "hooks" / "commit-msg").exists()

    def test_skips_existing_unmanaged_hooks(self, git_hooks_dir: Path) -> None:
        hook_path = git_hooks_dir / ".git" / "hooks" / "pre-commit"
        hook_path.write_text("#!/bin/bash\necho 'custom'")

        result = install_hooks(git_hooks_dir)
        assert "pre-commit" in result.skipped
        assert hook_path.read_text() == "#!/bin/bash\necho 'custom'"

    def test_overwrites_managed_hooks(self, git_hooks_dir: Path) -> None:
        hook_path = git_hooks_dir / ".git" / "hooks" / "pre-commit"
        hook_path.write_text(f"#!/bin/bash\n{_HOOK_MARKER}\nold version")

        result = install_hooks(git_hooks_dir)
        assert "pre-commit" in result.installed
        assert "old version" not in hook_path.read_text()

    def test_force_overwrites_unmanaged_hooks(self, git_hooks_dir: Path) -> None:
        hook_path = git_hooks_dir / ".git" / "hooks" / "pre-commit"
        hook_path.write_text("#!/bin/bash\necho 'custom'")

        result = install_hooks(git_hooks_dir, force=True)
        assert "pre-commit" in result.installed
        assert _HOOK_MARKER in hook_path.read_text()

    def test_creates_powershell_companions(self, git_hooks_dir: Path) -> None:
        install_hooks(git_hooks_dir)
        for hook in GateHook:
            ps_path = git_hooks_dir / ".git" / "hooks" / f"{hook.value}.ps1"
            assert ps_path.is_file()
            assert _HOOK_MARKER in ps_path.read_text()

    def test_raises_without_git_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Git hooks directory"):
            install_hooks(tmp_path)

    def test_reports_conflicts(self, git_hooks_dir: Path) -> None:
        (git_hooks_dir / ".husky").mkdir()
        result = install_hooks(git_hooks_dir)
        assert len(result.conflicts) == 1
        assert result.conflicts[0].manager == "husky"


# ---------------------------------------------------------------------------
# Uninstall hooks
# ---------------------------------------------------------------------------


class TestUninstallHooks:
    """Tests for hook removal."""

    def test_removes_managed_hooks(self, git_hooks_dir: Path) -> None:
        install_hooks(git_hooks_dir)
        removed = uninstall_hooks(git_hooks_dir)
        assert len(removed) == 3
        for hook in GateHook:
            assert not (git_hooks_dir / ".git" / "hooks" / hook.value).exists()

    def test_leaves_unmanaged_hooks(self, git_hooks_dir: Path) -> None:
        hook_path = git_hooks_dir / ".git" / "hooks" / "pre-commit"
        hook_path.write_text("#!/bin/bash\ncustom")

        removed = uninstall_hooks(git_hooks_dir)
        assert "pre-commit" not in removed
        assert hook_path.is_file()

    def test_returns_empty_without_git_dir(self, tmp_path: Path) -> None:
        removed = uninstall_hooks(tmp_path)
        assert removed == []

    def test_removes_specific_hooks(self, git_hooks_dir: Path) -> None:
        install_hooks(git_hooks_dir)
        removed = uninstall_hooks(git_hooks_dir, hooks=[GateHook.PRE_COMMIT])
        assert removed == ["pre-commit"]
        assert (git_hooks_dir / ".git" / "hooks" / "commit-msg").is_file()


# ---------------------------------------------------------------------------
# Verify hooks
# ---------------------------------------------------------------------------


class TestVerifyHooks:
    """Tests for hook integrity verification."""

    def test_all_valid_after_install(self, git_hooks_dir: Path) -> None:
        install_hooks(git_hooks_dir)
        status = verify_hooks(git_hooks_dir)
        assert all(status.values())

    def test_missing_hooks_report_false(self, git_hooks_dir: Path) -> None:
        status = verify_hooks(git_hooks_dir)
        assert all(v is False for v in status.values())

    def test_tampered_hook_reports_false(self, git_hooks_dir: Path) -> None:
        install_hooks(git_hooks_dir)
        hook_path = git_hooks_dir / ".git" / "hooks" / "pre-commit"
        hook_path.write_text("#!/bin/bash\ntampered")
        status = verify_hooks(git_hooks_dir)
        assert status["pre-commit"] is False
        assert status["commit-msg"] is True
