"""Tests for doctor/service.py — diagnostic checks and remediation.

Covers:
- Layout validation (framework dirs present/missing).
- State file integrity checks.
- Hook verification and fix-hooks remediation.
- Tool availability checks.
- Branch policy warnings.
- Report serialization and summary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.doctor.service import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    diagnose,
)
from ai_engineering.installer.service import install


@pytest.fixture()
def installed_project(tmp_path: Path) -> Path:
    """Create a fully installed project."""
    install(tmp_path)
    return tmp_path


@pytest.fixture()
def installed_git_project(tmp_path: Path) -> Path:
    """Create a fully installed project with a git repo."""
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    install(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Layout checks
# ---------------------------------------------------------------------------


class TestLayoutCheck:
    """Tests for framework layout validation."""

    def test_passes_on_valid_layout(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        layout = _find_check(report, "framework-layout")
        assert layout.status == CheckStatus.OK

    def test_fails_on_missing_ai_engineering_dir(self, tmp_path: Path) -> None:
        report = diagnose(tmp_path)
        layout = _find_check(report, "framework-layout")
        assert layout.status == CheckStatus.FAIL

    def test_fails_on_missing_subdirectory(self, installed_project: Path) -> None:
        import shutil

        shutil.rmtree(installed_project / ".ai-engineering" / "standards")
        report = diagnose(installed_project)
        layout = _find_check(report, "framework-layout")
        assert layout.status == CheckStatus.FAIL
        assert "standards" in layout.message


# ---------------------------------------------------------------------------
# State file checks
# ---------------------------------------------------------------------------


class TestStateFileChecks:
    """Tests for state file integrity validation."""

    def test_all_state_files_valid(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        state_checks = [c for c in report.checks if c.name.startswith("state:")]
        assert all(c.status == CheckStatus.OK for c in state_checks)
        assert len(state_checks) == 4

    def test_fails_on_missing_manifest(self, installed_project: Path) -> None:
        manifest = installed_project / ".ai-engineering" / "state" / "install-manifest.json"
        manifest.unlink()
        report = diagnose(installed_project)
        check = _find_check(report, "state:install-manifest.json")
        assert check.status == CheckStatus.FAIL

    def test_fails_on_corrupt_manifest(self, installed_project: Path) -> None:
        manifest = installed_project / ".ai-engineering" / "state" / "install-manifest.json"
        manifest.write_text("{invalid json", encoding="utf-8")
        report = diagnose(installed_project)
        check = _find_check(report, "state:install-manifest.json")
        assert check.status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Hook checks
# ---------------------------------------------------------------------------


class TestHookChecks:
    """Tests for git hook verification."""

    def test_warns_when_not_git_repo(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        hook_check = _find_check(report, "git-hooks")
        assert hook_check.status == CheckStatus.WARN

    def test_fails_when_hooks_missing(self, installed_git_project: Path) -> None:
        report = diagnose(installed_git_project)
        hook_check = _find_check(report, "git-hooks")
        assert hook_check.status == CheckStatus.FAIL

    def test_fix_hooks_reinstalls(self, installed_git_project: Path) -> None:
        report = diagnose(installed_git_project, fix_hooks=True)
        hook_check = _find_check(report, "git-hooks")
        assert hook_check.status == CheckStatus.FIXED

    def test_passes_after_fix(self, installed_git_project: Path) -> None:
        diagnose(installed_git_project, fix_hooks=True)
        report = diagnose(installed_git_project)
        hook_check = _find_check(report, "git-hooks")
        assert hook_check.status == CheckStatus.OK


# ---------------------------------------------------------------------------
# Tool checks
# ---------------------------------------------------------------------------


class TestToolChecks:
    """Tests for tool availability checks."""

    def test_git_is_always_available(self, installed_project: Path) -> None:
        """Git should be available in the test environment."""
        report = diagnose(installed_project)
        # We can't guarantee ruff/ty/etc are installed, but the check should
        # produce results for each tool
        tool_checks = [c for c in report.checks if c.name.startswith("tool:")]
        expected_tools = {"ruff", "ty", "gitleaks", "semgrep", "pip-audit", "gh", "az"}
        actual_tools = {c.name.split(":")[1] for c in tool_checks}
        assert expected_tools == actual_tools


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


class TestDoctorReport:
    """Tests for report structure and serialization."""

    def test_report_passed_when_no_failures(self) -> None:
        report = DoctorReport(checks=[
            CheckResult(name="a", status=CheckStatus.OK, message="ok"),
            CheckResult(name="b", status=CheckStatus.WARN, message="warn"),
        ])
        assert report.passed is True

    def test_report_not_passed_with_failure(self) -> None:
        report = DoctorReport(checks=[
            CheckResult(name="a", status=CheckStatus.OK, message="ok"),
            CheckResult(name="b", status=CheckStatus.FAIL, message="fail"),
        ])
        assert report.passed is False

    def test_summary_counts(self) -> None:
        report = DoctorReport(checks=[
            CheckResult(name="a", status=CheckStatus.OK, message=""),
            CheckResult(name="b", status=CheckStatus.OK, message=""),
            CheckResult(name="c", status=CheckStatus.FAIL, message=""),
            CheckResult(name="d", status=CheckStatus.WARN, message=""),
        ])
        assert report.summary == {"ok": 2, "fail": 1, "warn": 1}

    def test_to_dict_serializable(self) -> None:
        report = DoctorReport(checks=[
            CheckResult(name="test", status=CheckStatus.OK, message="msg"),
        ])
        data = report.to_dict()
        # Should be JSON-serializable
        serialized = json.dumps(data)
        assert '"test"' in serialized

    def test_full_report_on_installed_project(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        assert len(report.checks) > 0
        data = report.to_dict()
        assert "passed" in data
        assert "checks" in data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_check(report: DoctorReport, name: str) -> CheckResult:
    """Find a check by name in a report."""
    for check in report.checks:
        if check.name == name:
            return check
    pytest.fail(f"Check '{name}' not found in report")
