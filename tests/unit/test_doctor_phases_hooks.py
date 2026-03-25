"""Tests for doctor/phases/hooks.py -- git hook integrity checks."""

from __future__ import annotations

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

    def test_check_returns_two_results(self, ctx: DoctorContext) -> None:
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

        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {"hooks-integrity", "hooks-scripts"}
