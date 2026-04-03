"""Tests for doctor/phases/hooks.py -- git hook integrity checks."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import hooks as hooks_phase
from ai_engineering.hooks.manager import HookInstallResult


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with .git/hooks."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "scripts" / "hooks").mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def ctx(project: Path) -> DoctorContext:
    """DoctorContext targeting the temp project."""
    return DoctorContext(target=project)


# ── hooks-integrity ────────────────────────────────────────────────────


class TestHooksIntegrityCheck:
    def test_ok_when_all_hooks_verified(self, ctx: DoctorContext) -> None:
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={
                "pre-commit": True,
                "commit-msg": True,
                "pre-push": True,
            },
        ):
            results = hooks_phase.check(ctx)

        integrity = next(r for r in results if r.name == "hooks-integrity")
        assert integrity.status == CheckStatus.OK

    def test_fail_when_hook_fails_verification(self, ctx: DoctorContext) -> None:
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={
                "pre-commit": True,
                "commit-msg": False,
                "pre-push": True,
            },
        ):
            results = hooks_phase.check(ctx)

        integrity = next(r for r in results if r.name == "hooks-integrity")
        assert integrity.status == CheckStatus.FAIL
        assert integrity.fixable is True
        assert "commit-msg" in integrity.message

    def test_fail_when_multiple_hooks_fail(self, ctx: DoctorContext) -> None:
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={
                "pre-commit": False,
                "commit-msg": False,
                "pre-push": True,
            },
        ):
            results = hooks_phase.check(ctx)

        integrity = next(r for r in results if r.name == "hooks-integrity")
        assert integrity.status == CheckStatus.FAIL
        assert "commit-msg" in integrity.message
        assert "pre-commit" in integrity.message

    def test_fail_when_git_dir_missing(self, tmp_path: Path) -> None:
        ctx = DoctorContext(target=tmp_path)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            side_effect=FileNotFoundError("no .git/hooks"),
        ):
            results = hooks_phase.check(ctx)

        integrity = next(r for r in results if r.name == "hooks-integrity")
        assert integrity.status == CheckStatus.FAIL
        assert integrity.fixable is True


# ── hooks-scripts ──────────────────────────────────────────────────────


class TestHooksScriptsCheck:
    def test_ok_when_scripts_dir_exists(self, ctx: DoctorContext) -> None:
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={
                "pre-commit": True,
                "commit-msg": True,
                "pre-push": True,
            },
        ):
            results = hooks_phase.check(ctx)

        scripts = next(r for r in results if r.name == "hooks-scripts")
        assert scripts.status == CheckStatus.OK

    def test_warn_when_scripts_dir_missing(self, tmp_path: Path) -> None:
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        # Do NOT create .ai-engineering/scripts/hooks

        ctx = DoctorContext(target=tmp_path)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={
                "pre-commit": True,
                "commit-msg": True,
                "pre-push": True,
            },
        ):
            results = hooks_phase.check(ctx)

        scripts = next(r for r in results if r.name == "hooks-scripts")
        assert scripts.status == CheckStatus.WARN


# ── fix() ──────────────────────────────────────────────────────────────


class TestHooksFix:
    def test_fix_reinstalls_hooks(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FAIL,
                message="hook verification failed: pre-commit",
                fixable=True,
            )
        ]

        mock_result = HookInstallResult(installed=["pre-commit", "commit-msg", "pre-push"])
        with patch.object(hooks_phase, "install_hooks", return_value=mock_result):
            fixed = hooks_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED
        assert "reinstalled" in fixed[0].message

    def test_fix_dry_run_does_not_install(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FAIL,
                message="hook verification failed: pre-commit",
                fixable=True,
            )
        ]

        with patch.object(hooks_phase, "install_hooks") as mock_install:
            fixed = hooks_phase.fix(ctx, failed, dry_run=True)

        mock_install.assert_not_called()
        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_passes_through_non_fixable(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="hooks-scripts",
                status=CheckStatus.WARN,
                message="scripts/hooks/ directory missing",
            )
        ]

        fixed = hooks_phase.fix(ctx, failed)
        assert len(fixed) == 1
        assert fixed[0].name == "hooks-scripts"
        assert fixed[0].status == CheckStatus.WARN

    def test_fix_handles_install_failure(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FAIL,
                message="hook verification failed: all",
                fixable=True,
            )
        ]

        mock_result = HookInstallResult(installed=[], skipped=["pre-commit"])
        with patch.object(hooks_phase, "install_hooks", return_value=mock_result):
            fixed = hooks_phase.fix(ctx, failed)

        assert len(fixed) == 1
        # When nothing is installed, the original failure is returned
        assert fixed[0].status == CheckStatus.FAIL

    def test_fix_handles_file_not_found(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FAIL,
                message="git hooks directory not found",
                fixable=True,
            )
        ]

        with patch.object(hooks_phase, "install_hooks", side_effect=FileNotFoundError("no .git")):
            fixed = hooks_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FAIL

    def test_check_returns_six_results(self, ctx: DoctorContext) -> None:
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={
                "pre-commit": True,
                "commit-msg": True,
                "pre-push": True,
            },
        ):
            results = hooks_phase.check(ctx)

        assert len(results) == 6
        names = {r.name for r in results}
        assert names == {
            "hooks-integrity",
            "hooks-scripts",
            "hooks-executable",
            "hooks-lib-complete",
            "hooks-registered",
            "hooks-runtime",
        }


# ── hooks-executable ──────────────────────────────────────────────────


@pytest.mark.skipif(os.name == "nt", reason="Unix permission semantics not available on Windows")
class TestHooksExecutableCheck:
    def test_hooks_executable_all_ok(self, project: Path) -> None:
        """All scripts have executable permission -> OK."""
        hooks_dir = project / ".ai-engineering" / "scripts" / "hooks"
        for name in ("pre-commit.sh", "observe.py"):
            script = hooks_dir / name
            script.write_text("#!/bin/sh\nexit 0\n")
            script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-executable")
        assert result.status == CheckStatus.OK

    def test_hooks_executable_missing_perms(self, project: Path) -> None:
        """Some scripts lack executable permission -> FAIL + fixable."""
        hooks_dir = project / ".ai-engineering" / "scripts" / "hooks"
        good = hooks_dir / "good.sh"
        good.write_text("#!/bin/sh\nexit 0\n")
        good.chmod(good.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

        bad = hooks_dir / "bad.sh"
        bad.write_text("#!/bin/sh\nexit 0\n")
        bad.chmod(stat.S_IRUSR | stat.S_IWUSR)  # no execute bit

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-executable")
        assert result.status == CheckStatus.FAIL
        assert result.fixable is True
        assert "bad.sh" in result.message

    def test_hooks_executable_excludes_lib(self, project: Path) -> None:
        """Files inside _lib/ are excluded from the executable check."""
        hooks_dir = project / ".ai-engineering" / "scripts" / "hooks"
        lib_dir = hooks_dir / "_lib"
        lib_dir.mkdir()
        # Non-executable file in _lib should NOT trigger failure
        lib_file = lib_dir / "audit.py"
        lib_file.write_text("# library\n")
        lib_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # no execute

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-executable")
        assert result.status == CheckStatus.OK

    def test_hooks_executable_fix(self, project: Path) -> None:
        """Fix applies chmod +x to non-executable scripts."""
        hooks_dir = project / ".ai-engineering" / "scripts" / "hooks"
        bad = hooks_dir / "fix-me.sh"
        bad.write_text("#!/bin/sh\nexit 0\n")
        bad.chmod(stat.S_IRUSR | stat.S_IWUSR)  # no execute

        ctx = DoctorContext(target=project)
        failed = [
            CheckResult(
                name="hooks-executable",
                status=CheckStatus.FAIL,
                message=f"non-executable hook scripts: {bad.name}",
                fixable=True,
            )
        ]

        hooks_phase.fix(ctx, failed)

        assert os.access(bad, os.X_OK), "fix should have made the script executable"


# ── hooks-lib-complete ────────────────────────────────────────────────


class TestHooksLibCompleteCheck:
    def test_hooks_lib_complete_ok(self, project: Path) -> None:
        """All 4 required library files present -> OK."""
        lib_dir = project / ".ai-engineering" / "scripts" / "hooks" / "_lib"
        lib_dir.mkdir(parents=True)
        for name in ("audit.py", "observability.py", "instincts.py", "injection_patterns.py"):
            (lib_dir / name).write_text("# lib\n")

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-lib-complete")
        assert result.status == CheckStatus.OK

    def test_hooks_lib_complete_missing(self, project: Path) -> None:
        """Missing library files -> FAIL, not fixable."""
        lib_dir = project / ".ai-engineering" / "scripts" / "hooks" / "_lib"
        lib_dir.mkdir(parents=True)
        # Only create 2 of 4
        (lib_dir / "audit.py").write_text("# lib\n")
        (lib_dir / "observability.py").write_text("# lib\n")

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-lib-complete")
        assert result.status == CheckStatus.FAIL
        assert result.fixable is False
        assert "injection_patterns.py" in result.message
        assert "instincts.py" in result.message


# ── hooks-registered ──────────────────────────────────────────────────


class TestHooksRegisteredCheck:
    def test_hooks_registered_ok(self, project: Path) -> None:
        """All referenced scripts exist -> OK."""
        hooks_dir = project / ".ai-engineering" / "scripts" / "hooks"
        (hooks_dir / "observe.py").write_text("# hook\n")

        settings_dir = project / ".claude"
        settings_dir.mkdir(parents=True)
        settings = {
            "hooks": {
                "PostToolUse": [
                    {
                        "command": (
                            'python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/observe.py"'
                        ),
                    }
                ],
            },
        }
        (settings_dir / "settings.json").write_text(json.dumps(settings))

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-registered")
        assert result.status == CheckStatus.OK

    def test_hooks_registered_missing_script(self, project: Path) -> None:
        """Referenced script does not exist on disk -> FAIL."""
        settings_dir = project / ".claude"
        settings_dir.mkdir(parents=True)
        settings = {
            "hooks": {
                "PostToolUse": [
                    {
                        "command": (
                            'python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/missing.py"'
                        ),
                    }
                ],
            },
        }
        (settings_dir / "settings.json").write_text(json.dumps(settings))

        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-registered")
        assert result.status == CheckStatus.FAIL
        assert result.fixable is False
        assert "missing.py" in result.message

    def test_hooks_registered_no_settings(self, project: Path) -> None:
        """No settings.json -> WARN (non-Claude-Code IDE)."""
        # Ensure no .claude/settings.json exists
        ctx = DoctorContext(target=project)
        with patch.object(
            hooks_phase,
            "verify_hooks",
            return_value={"pre-commit": True},
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-registered")
        assert result.status == CheckStatus.WARN


# ── hooks-runtime ─────────────────────────────────────────────────────


class TestHooksRuntimeCheck:
    def test_hooks_runtime_available(self, project: Path) -> None:
        """Project runtime present -> OK with runtime in message."""
        venv_python = project / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True, exist_ok=True)
        venv_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        venv_python.chmod(0o755)
        ctx = DoctorContext(target=project)
        with (
            patch.object(
                hooks_phase,
                "verify_hooks",
                return_value={"pre-commit": True},
            ),
            patch.object(hooks_phase.shutil, "which", return_value=None),
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-runtime")
        assert result.status == CheckStatus.OK
        assert ".venv/bin/python" in result.message

    def test_hooks_runtime_missing(self, project: Path) -> None:
        """No project runtime launcher -> FAIL."""
        ctx = DoctorContext(target=project)
        with (
            patch.object(
                hooks_phase,
                "verify_hooks",
                return_value={"pre-commit": True},
            ),
            patch.object(hooks_phase.shutil, "which", return_value=None),
        ):
            results = hooks_phase.check(ctx)

        result = next(r for r in results if r.name == "hooks-runtime")
        assert result.status == CheckStatus.FAIL
