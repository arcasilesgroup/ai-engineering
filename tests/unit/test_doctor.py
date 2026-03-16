"""Unit tests for doctor/service.py — diagnostic checks and remediation.

Refactored from 63 @patch decorators to a single mocked_checks fixture.
Tests behavior (report outcomes), not implementation (mock call counts).

TDD-ready: AAA pattern, centralized fakes, behavior-focused assertions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport
from ai_engineering.doctor.service import diagnose

pytestmark = pytest.mark.unit


# ── Fixture: centralized check patching ───────────────────────────────────

_CHECK_MODULES = {
    "layout": "ai_engineering.doctor.checks.layout.check_layout",
    "state_files": "ai_engineering.doctor.checks.state_files.check_state_files",
    "hooks": "ai_engineering.doctor.checks.hooks.check_hooks",
    "venv": "ai_engineering.doctor.checks.venv.check_venv_health",
    "tools": "ai_engineering.doctor.checks.tools.check_tools",
    "vcs_tools": "ai_engineering.doctor.checks.tools.check_vcs_tools",
    "branch_policy": "ai_engineering.doctor.checks.branch_policy.check_branch_policy",
    "readiness": "ai_engineering.doctor.checks.readiness.check_operational_readiness",
    "version": "ai_engineering.doctor.checks.version_check.check_version",
}


@pytest.fixture()
def mocked_checks(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Patch all 9 doctor checks at once. Returns dict of mocks by name."""
    mocks: dict[str, MagicMock] = {}
    for name, module_path in _CHECK_MODULES.items():
        mock = MagicMock()
        monkeypatch.setattr(module_path, mock)
        mocks[name] = mock
    return mocks


# ── CheckStatus ───────────────────────────────────────────────────────────


class TestCheckStatus:
    def test_ok_value(self) -> None:
        assert CheckStatus.OK.value == "ok"

    def test_warn_value(self) -> None:
        assert CheckStatus.WARN.value == "warn"

    def test_fail_value(self) -> None:
        assert CheckStatus.FAIL.value == "fail"

    def test_fixed_value(self) -> None:
        assert CheckStatus.FIXED.value == "fixed"


# ── CheckResult ───────────────────────────────────────────────────────────


class TestCheckResult:
    def test_creation_and_fields(self) -> None:
        # Arrange & Act
        result = CheckResult(name="test-check", status=CheckStatus.OK, message="all good")

        # Assert
        assert result.name == "test-check"
        assert result.status == CheckStatus.OK
        assert result.message == "all good"


# ── DoctorReport ──────────────────────────────────────────────────────────


class TestDoctorReport:
    def test_passed_with_all_ok(self) -> None:
        # Arrange
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.OK, message="ok"),
            ]
        )

        # Assert
        assert report.passed is True

    def test_passed_with_warn_is_true(self) -> None:
        # Arrange
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.WARN, message="warning"),
            ]
        )

        # Assert
        assert report.passed is True

    def test_passed_with_fail_is_false(self) -> None:
        # Arrange
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.FAIL, message="failed"),
            ]
        )

        # Assert
        assert report.passed is False

    def test_passed_with_fixed_is_true(self) -> None:
        # Arrange
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.FIXED, message="fixed"),
                CheckResult(name="b", status=CheckStatus.OK, message="ok"),
            ]
        )

        # Assert
        assert report.passed is True

    def test_empty_report_passed_is_true(self) -> None:
        assert DoctorReport().passed is True

    def test_summary_counts_by_status(self) -> None:
        # Arrange
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message=""),
                CheckResult(name="b", status=CheckStatus.OK, message=""),
                CheckResult(name="c", status=CheckStatus.WARN, message=""),
                CheckResult(name="d", status=CheckStatus.FAIL, message=""),
                CheckResult(name="e", status=CheckStatus.FIXED, message=""),
            ]
        )

        # Act
        summary = report.summary

        # Assert
        assert summary == {"ok": 2, "warn": 1, "fail": 1, "fixed": 1}

    def test_summary_empty_report(self) -> None:
        assert DoctorReport().summary == {}


# ── diagnose() ────────────────────────────────────────────────────────────


class TestDiagnose:
    """Tests for diagnose() — uses mocked_checks fixture (1 fixture, not 63 patches)."""

    def test_all_checks_called(self, mocked_checks: dict[str, MagicMock]) -> None:
        # Act
        report = diagnose(Path("/fake"))

        # Assert — all 9 checks were invoked
        assert report.passed is True
        for name, mock in mocked_checks.items():
            assert mock.called, f"{name} was not called"

    def test_report_fails_when_hooks_inject_failure(
        self, mocked_checks: dict[str, MagicMock]
    ) -> None:
        # Arrange — hooks check injects a FAIL result
        def inject_fail(target: Path, report: DoctorReport, *, fix: bool) -> None:
            report.checks.append(
                CheckResult(name="git-hooks", status=CheckStatus.FAIL, message="Missing hooks")
            )

        mocked_checks["hooks"].side_effect = inject_fail

        # Act
        report = diagnose(Path("/fake"))

        # Assert
        assert report.passed is False
        assert any(c.name == "git-hooks" and c.status == CheckStatus.FAIL for c in report.checks)

    def test_report_passes_when_tools_inject_warning(
        self, mocked_checks: dict[str, MagicMock]
    ) -> None:
        # Arrange — tools check injects a WARN (not failure)
        def inject_warn(report: DoctorReport, *, fix: bool) -> None:
            report.checks.append(
                CheckResult(name="tool:ruff", status=CheckStatus.WARN, message="ruff not found")
            )

        mocked_checks["tools"].side_effect = inject_warn

        # Act
        report = diagnose(Path("/fake"))

        # Assert — WARN does not fail the report
        assert report.passed is True
        assert any(c.name == "tool:ruff" for c in report.checks)

    def test_fix_hooks_flag_forwarded(self, mocked_checks: dict[str, MagicMock]) -> None:
        # Act
        diagnose(Path("/fake"), fix_hooks=True)

        # Assert
        _, kwargs = mocked_checks["hooks"].call_args
        assert kwargs["fix"] is True

    def test_fix_tools_flag_forwarded(self, mocked_checks: dict[str, MagicMock]) -> None:
        # Act
        diagnose(Path("/fake"), fix_tools=True)

        # Assert
        _, tools_kwargs = mocked_checks["tools"].call_args
        assert tools_kwargs["fix"] is True
        _, venv_kwargs = mocked_checks["venv"].call_args
        assert venv_kwargs["fix"] is True

    def test_default_flags_are_false(self, mocked_checks: dict[str, MagicMock]) -> None:
        # Act
        diagnose(Path("/fake"))

        # Assert
        _, hooks_kwargs = mocked_checks["hooks"].call_args
        assert hooks_kwargs["fix"] is False
        _, tools_kwargs = mocked_checks["tools"].call_args
        assert tools_kwargs["fix"] is False

    def test_returns_doctor_report_type(self, mocked_checks: dict[str, MagicMock]) -> None:
        # Act
        report = diagnose(Path("/fake"))

        # Assert
        assert isinstance(report, DoctorReport)
