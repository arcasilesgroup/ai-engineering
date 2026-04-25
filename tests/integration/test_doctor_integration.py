"""Integration tests for doctor/service.py -- phase-grouped diagnostic checks.

Covers:
- Layout validation (governance phase).
- State file integrity checks (state phase).
- Hook verification and fix remediation (hooks phase).
- Venv health checks (tools phase).
- Tool availability checks (tools phase).
- Branch policy warnings (runtime).
- Report serialization and summary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport, PhaseReport
from ai_engineering.doctor.service import diagnose
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

    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    install(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_check_in_phases(report: DoctorReport, name: str) -> CheckResult:
    """Find a check by name across all phases in a report."""
    for phase in report.phases:
        for check in phase.checks:
            if check.name == name:
                return check
    pytest.fail(f"Check '{name}' not found in report phases")


def _find_check_in_runtime(report: DoctorReport, name: str) -> CheckResult:
    """Find a check by name in runtime checks."""
    for check in report.runtime:
        if check.name == name:
            return check
    pytest.fail(f"Check '{name}' not found in report runtime")


def _find_phase(report: DoctorReport, name: str) -> PhaseReport:
    """Find a phase by name in a report."""
    for phase in report.phases:
        if phase.name == name:
            return phase
    pytest.fail(f"Phase '{name}' not found in report")


def _all_checks(report: DoctorReport) -> list[CheckResult]:
    """Collect all checks from phases and runtime."""
    checks = []
    for phase in report.phases:
        checks.extend(phase.checks)
    checks.extend(report.runtime)
    return checks


def _force_venv_mode(project: Path) -> None:
    """Force the project's manifest into ``python_env.mode: venv``.

    Spec-101 D-101-12 made ``uv-tool`` the default mode for fresh installs;
    that mode skips the venv-health probe (which is the correct behaviour
    for the new architecture). Tests below pin the LEGACY ``venv`` probe
    semantics and therefore need to opt into ``mode: venv`` explicitly.
    """
    manifest_path = project / ".ai-engineering" / "manifest.yml"
    text = manifest_path.read_text(encoding="utf-8")
    if "python_env:" in text:
        # Replace whatever mode is set with ``venv``.
        import re

        text = re.sub(
            r"python_env:\s*\n\s*mode:\s*\S+",
            "python_env:\n  mode: venv",
            text,
        )
    else:
        text += "\npython_env:\n  mode: venv\n"
    manifest_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Governance phase checks (formerly layout)
# ---------------------------------------------------------------------------


class TestGovernancePhaseCheck:
    """Tests for governance phase validation (framework layout + manifest)."""

    def test_passes_on_valid_layout(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        governance = _find_phase(report, "governance")
        governance_dirs = next((c for c in governance.checks if c.name == "governance-dirs"), None)
        assert governance_dirs is not None
        assert governance_dirs.status == CheckStatus.OK

    def test_fails_on_missing_ai_engineering_dir(self, tmp_path: Path) -> None:
        report = diagnose(tmp_path)
        # Pre-install mode: limited checks only (tools + limited runtime)
        assert report.installed is False

    def test_fails_on_missing_subdirectory(self, installed_project: Path) -> None:
        import shutil

        shutil.rmtree(installed_project / ".ai-engineering" / "contexts")
        report = diagnose(installed_project)
        governance = _find_phase(report, "governance")
        governance_dirs = next((c for c in governance.checks if c.name == "governance-dirs"), None)
        assert governance_dirs is not None
        assert governance_dirs.status == CheckStatus.FAIL
        assert "contexts" in governance_dirs.message


# ---------------------------------------------------------------------------
# State phase checks
# ---------------------------------------------------------------------------


class TestStatePhaseChecks:
    """Tests for state file integrity validation."""

    def test_all_state_files_valid(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        state_phase = _find_phase(report, "state")
        parseable = next((c for c in state_phase.checks if c.name == "state-files-parseable"), None)
        assert parseable is not None
        assert parseable.status == CheckStatus.OK

    def test_fails_on_missing_state(self, installed_project: Path) -> None:
        state_file = installed_project / ".ai-engineering" / "state" / "install-state.json"
        state_file.unlink()
        # With install-state.json missing, diagnose goes into pre-install mode
        report = diagnose(installed_project)
        assert report.installed is False

    def test_falls_to_preinstall_on_corrupt_state(self, installed_project: Path) -> None:
        state_file = installed_project / ".ai-engineering" / "state" / "install-state.json"
        state_file.write_text("{invalid json", encoding="utf-8")
        # Corrupt JSON means the service cannot load state -- enters pre-install mode
        report = diagnose(installed_project)
        assert report.installed is False


# ---------------------------------------------------------------------------
# Hook checks
# ---------------------------------------------------------------------------


class TestHookChecks:
    """Tests for git hook verification."""

    def test_ok_when_installed_with_git(self, installed_project: Path) -> None:
        # Since spec-072, install() auto-initializes git and installs hooks
        report = diagnose(installed_project)
        hooks_phase = _find_phase(report, "hooks")
        hook_check = next((c for c in hooks_phase.checks if c.name == "hooks-integrity"), None)
        assert hook_check is not None
        assert hook_check.status == CheckStatus.OK

    def test_fails_when_hooks_missing(self, installed_git_project: Path) -> None:
        # Remove auto-installed hooks to simulate missing state
        for hook in (installed_git_project / ".git" / "hooks").glob("pre-*"):
            hook.unlink()
        for hook in (installed_git_project / ".git" / "hooks").glob("commit-msg*"):
            hook.unlink()
        report = diagnose(installed_git_project)
        hooks_phase = _find_phase(report, "hooks")
        hook_check = next((c for c in hooks_phase.checks if c.name == "hooks-integrity"), None)
        assert hook_check is not None
        assert hook_check.status == CheckStatus.FAIL

    def test_fix_hooks_reinstalls(self, installed_git_project: Path) -> None:
        # Remove auto-installed hooks to simulate missing state
        for hook in (installed_git_project / ".git" / "hooks").glob("pre-*"):
            hook.unlink()
        for hook in (installed_git_project / ".git" / "hooks").glob("commit-msg*"):
            hook.unlink()
        report = diagnose(installed_git_project, fix=True, phase_filter="hooks")
        hooks_phase = _find_phase(report, "hooks")
        hook_check = next((c for c in hooks_phase.checks if c.name == "hooks-integrity"), None)
        assert hook_check is not None
        assert hook_check.status == CheckStatus.FIXED

    def test_passes_after_fix(self, installed_git_project: Path) -> None:
        diagnose(installed_git_project, fix=True, phase_filter="hooks")
        report = diagnose(installed_git_project)
        hooks_phase = _find_phase(report, "hooks")
        hook_check = next((c for c in hooks_phase.checks if c.name == "hooks-integrity"), None)
        assert hook_check is not None
        assert hook_check.status == CheckStatus.OK


# ---------------------------------------------------------------------------
# Tools phase checks (venv health)
# ---------------------------------------------------------------------------


class TestVenvHealthCheck:
    """Tests for venv health validation (now in tools phase)."""

    def test_ok_when_home_path_exists(self, installed_project: Path) -> None:
        """Venv health passes when pyvenv.cfg home points to existing dir."""
        venv = installed_project / ".venv"
        venv.mkdir(exist_ok=True)
        cfg = venv / "pyvenv.cfg"
        cfg.write_text(f"home = {installed_project}\n", encoding="utf-8")
        report = diagnose(installed_project)
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.OK

    def test_fails_when_home_path_stale(self, installed_project: Path) -> None:
        """Venv health fails when pyvenv.cfg home points to nonexistent dir."""
        _force_venv_mode(installed_project)
        venv = installed_project / ".venv"
        venv.mkdir(exist_ok=True)
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("home = /nonexistent/stale/python/path\n", encoding="utf-8")
        report = diagnose(installed_project)
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.FAIL
        assert "does not exist" in venv_check.message or "home" in venv_check.message.lower()

    def test_warns_when_no_venv(self, installed_project: Path) -> None:
        """Venv health warns when .venv directory is absent."""
        _force_venv_mode(installed_project)
        venv = installed_project / ".venv"
        if venv.exists():
            import shutil

            shutil.rmtree(venv)
        report = diagnose(installed_project)
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.WARN

    def test_fixed_when_recreated(self, installed_project: Path) -> None:
        """Venv health is fixed when fix recreates stale venv."""
        from unittest.mock import patch

        _force_venv_mode(installed_project)
        venv = installed_project / ".venv"
        venv.mkdir(exist_ok=True)
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("home = /nonexistent/stale/python/path\n", encoding="utf-8")

        # Mock the private fix function to return FIXED result
        fixed_result = CheckResult(
            name="venv-health", status=CheckStatus.FIXED, message="recreated .venv via uv venv"
        )
        with patch(
            "ai_engineering.doctor.phases.tools._fix_venv_health",
            return_value=fixed_result,
        ):
            report = diagnose(installed_project, fix=True, phase_filter="tools")
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.FIXED

    def test_warns_when_no_pyvenv_cfg(self, installed_project: Path) -> None:
        """Venv health warns when .venv exists but pyvenv.cfg is absent."""
        _force_venv_mode(installed_project)
        venv = installed_project / ".venv"
        venv.mkdir(exist_ok=True)
        report = diagnose(installed_project)
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.WARN
        assert "pyvenv.cfg" in venv_check.message

    def test_fails_when_home_not_parseable(self, installed_project: Path) -> None:
        """Venv health fails when pyvenv.cfg has no home key."""
        _force_venv_mode(installed_project)
        venv = installed_project / ".venv"
        venv.mkdir(exist_ok=True)
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("version = 3.12\nno-home-here = true\n", encoding="utf-8")
        report = diagnose(installed_project)
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.FAIL
        assert "home" in venv_check.message.lower()

    def test_recreation_failure_reports_fail(self, installed_project: Path) -> None:
        """Venv recreation failure reports FAIL status."""
        from unittest.mock import patch

        _force_venv_mode(installed_project)
        venv = installed_project / ".venv"
        venv.mkdir(exist_ok=True)
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("home = /nonexistent/stale/python/path\n", encoding="utf-8")

        fail_result = CheckResult(
            name="venv-health",
            status=CheckStatus.FAIL,
            message="failed to recreate .venv",
            fixable=True,
        )
        with patch(
            "ai_engineering.doctor.phases.tools._fix_venv_health",
            return_value=fail_result,
        ):
            report = diagnose(installed_project, fix=True, phase_filter="tools")
        tools_phase = _find_phase(report, "tools")
        venv_check = next((c for c in tools_phase.checks if c.name == "venv-health"), None)
        assert venv_check is not None
        assert venv_check.status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Tool checks
# ---------------------------------------------------------------------------


class TestToolChecks:
    """Tests for tool availability checks."""

    def test_tool_checks_produce_results(self, installed_project: Path) -> None:
        """Tools phase should produce check results for required tools."""
        report = diagnose(installed_project)
        tools_phase = _find_phase(report, "tools")
        assert len(tools_phase.checks) > 0


# ---------------------------------------------------------------------------
# Version lifecycle check (runtime)
# ---------------------------------------------------------------------------


class TestVersionLifecycleCheck:
    """Tests for version lifecycle diagnostic check."""

    def test_version_check_appears_in_report(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        check = _find_check_in_runtime(report, "version")
        assert check.status in (CheckStatus.OK, CheckStatus.WARN)

    def test_version_check_ok_when_current(self, installed_project: Path) -> None:
        from unittest.mock import patch

        from ai_engineering.version.checker import VersionCheckResult
        from ai_engineering.version.models import VersionStatus

        mock_result = VersionCheckResult(
            installed="0.1.0",
            status=VersionStatus.CURRENT,
            is_current=True,
            is_outdated=False,
            is_deprecated=False,
            is_eol=False,
            latest="0.1.0",
            message="0.1.0 (current)",
        )
        with patch("ai_engineering.doctor.runtime.version.check_version", return_value=mock_result):
            report = diagnose(installed_project)
        check = _find_check_in_runtime(report, "version")
        assert check.status == CheckStatus.OK

    def test_version_check_fail_when_deprecated(self, installed_project: Path) -> None:
        from unittest.mock import patch

        from ai_engineering.version.checker import VersionCheckResult
        from ai_engineering.version.models import VersionStatus

        mock_result = VersionCheckResult(
            installed="0.0.1",
            status=VersionStatus.DEPRECATED,
            is_current=False,
            is_outdated=False,
            is_deprecated=True,
            is_eol=False,
            latest="0.1.0",
            message="0.0.1 is deprecated",
        )
        with patch("ai_engineering.doctor.runtime.version.check_version", return_value=mock_result):
            report = diagnose(installed_project)
        check = _find_check_in_runtime(report, "version")
        assert check.status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


class TestDoctorReport:
    """Tests for report structure and serialization."""

    def test_report_passed_when_no_failures(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.WARN, message="warn"),
                    ],
                ),
            ],
        )
        assert report.passed is True

    def test_report_not_passed_with_failure(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.FAIL, message="fail"),
                    ],
                ),
            ],
        )
        assert report.passed is False

    def test_summary_counts(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p1",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message=""),
                        CheckResult(name="b", status=CheckStatus.OK, message=""),
                        CheckResult(name="c", status=CheckStatus.FAIL, message=""),
                    ],
                ),
            ],
            runtime=[
                CheckResult(name="d", status=CheckStatus.WARN, message=""),
            ],
        )
        assert report.summary == {"ok": 2, "fail": 1, "warn": 1}

    def test_to_dict_serializable(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="test",
                    checks=[
                        CheckResult(name="test", status=CheckStatus.OK, message="msg"),
                    ],
                ),
            ],
        )
        data = report.to_dict()
        serialized = json.dumps(data)
        assert '"test"' in serialized

    def test_full_report_on_installed_project(self, installed_project: Path) -> None:
        report = diagnose(installed_project)
        assert len(report.phases) > 0
        data = report.to_dict()
        assert "passed" in data
        assert "phases" in data
        assert "runtime" in data
        assert "summary" in data
