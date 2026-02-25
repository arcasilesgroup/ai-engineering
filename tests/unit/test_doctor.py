"""Unit tests for doctor/service.py — diagnostic checks and remediation.

Covers:
- CheckStatus enum values.
- CheckResult creation and fields.
- DoctorReport aggregation, passed property, summary counts.
- diagnose() function with mocked dependencies (no real I/O).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.doctor.service import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    diagnose,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# CheckStatus
# ---------------------------------------------------------------------------


class TestCheckStatus:
    """Tests for CheckStatus enum values."""

    def test_ok_value(self) -> None:
        assert CheckStatus.OK == "ok"
        assert CheckStatus.OK.value == "ok"

    def test_warn_value(self) -> None:
        assert CheckStatus.WARN == "warn"
        assert CheckStatus.WARN.value == "warn"

    def test_fail_value(self) -> None:
        assert CheckStatus.FAIL == "fail"
        assert CheckStatus.FAIL.value == "fail"

    def test_fixed_value(self) -> None:
        assert CheckStatus.FIXED == "fixed"
        assert CheckStatus.FIXED.value == "fixed"


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_creation_and_fields(self) -> None:
        result = CheckResult(name="test-check", status=CheckStatus.OK, message="all good")
        assert result.name == "test-check"
        assert result.status == CheckStatus.OK
        assert result.message == "all good"


# ---------------------------------------------------------------------------
# DoctorReport
# ---------------------------------------------------------------------------


class TestDoctorReport:
    """Tests for DoctorReport aggregation."""

    def test_passed_with_all_ok(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.OK, message="ok"),
            ]
        )
        assert report.passed is True

    def test_passed_with_warn_is_true(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.WARN, message="warning"),
            ]
        )
        assert report.passed is True

    def test_passed_with_fail_is_false(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.FAIL, message="failed"),
            ]
        )
        assert report.passed is False

    def test_passed_with_fixed_is_true(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.FIXED, message="fixed"),
                CheckResult(name="b", status=CheckStatus.OK, message="ok"),
            ]
        )
        assert report.passed is True

    def test_empty_report_passed_is_true(self) -> None:
        report = DoctorReport()
        assert report.passed is True

    def test_summary_counts_by_status(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message=""),
                CheckResult(name="b", status=CheckStatus.OK, message=""),
                CheckResult(name="c", status=CheckStatus.WARN, message=""),
                CheckResult(name="d", status=CheckStatus.FAIL, message=""),
                CheckResult(name="e", status=CheckStatus.FIXED, message=""),
            ]
        )
        summary = report.summary
        assert summary == {"ok": 2, "warn": 1, "fail": 1, "fixed": 1}

    def test_summary_empty_report(self) -> None:
        report = DoctorReport()
        assert report.summary == {}


# ---------------------------------------------------------------------------
# diagnose() — mocked
# ---------------------------------------------------------------------------


class TestDiagnose:
    """Tests for diagnose() with fully mocked internals."""

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_valid_project_all_pass(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """All sub-checks are called; report starts empty (passed=True)."""
        target = Path("/fake/project")
        report = diagnose(target)

        assert report.passed is True
        mock_layout.assert_called_once()
        mock_state.assert_called_once()
        mock_hooks.assert_called_once()
        mock_venv.assert_called_once()
        mock_tools.assert_called_once()
        mock_vcs.assert_called_once()
        mock_branch.assert_called_once()
        mock_readiness.assert_called_once()
        mock_version.assert_called_once()

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_with_failing_hooks(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """When _check_hooks injects a FAIL, the report should not pass."""

        def inject_fail(target: Path, report: DoctorReport, *, fix: bool) -> None:
            report.checks.append(
                CheckResult(
                    name="git-hooks",
                    status=CheckStatus.FAIL,
                    message="Missing or invalid hooks: pre-commit",
                )
            )

        mock_hooks.side_effect = inject_fail
        target = Path("/fake/project")
        report = diagnose(target)
        assert report.passed is False
        assert any(c.name == "git-hooks" and c.status == CheckStatus.FAIL for c in report.checks)

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_fix_hooks_passes_flag(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """fix_hooks=True is forwarded to _check_hooks."""
        target = Path("/fake/project")
        diagnose(target, fix_hooks=True)
        _, kwargs = mock_hooks.call_args
        assert kwargs["fix"] is True

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_with_missing_tool(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """When _check_tools injects a WARN for missing tool, report still passes."""

        def inject_warn(report: DoctorReport, *, fix: bool) -> None:
            report.checks.append(
                CheckResult(
                    name="tool:ruff",
                    status=CheckStatus.WARN,
                    message="ruff not found",
                )
            )

        mock_tools.side_effect = inject_warn
        target = Path("/fake/project")
        report = diagnose(target)
        # WARN does not fail the report
        assert report.passed is True
        assert any(c.name == "tool:ruff" for c in report.checks)

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_fix_tools_passes_flag(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """fix_tools=True is forwarded to _check_tools and _check_venv_health."""
        target = Path("/fake/project")
        diagnose(target, fix_tools=True)

        _, tools_kwargs = mock_tools.call_args
        assert tools_kwargs["fix"] is True

        _, venv_kwargs = mock_venv.call_args
        assert venv_kwargs["fix"] is True

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_returns_doctor_report_type(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """diagnose() always returns a DoctorReport instance."""
        target = Path("/fake/project")
        report = diagnose(target)
        assert isinstance(report, DoctorReport)

    @patch("ai_engineering.doctor.service._check_version")
    @patch("ai_engineering.doctor.service._check_operational_readiness")
    @patch("ai_engineering.doctor.service._check_branch_policy")
    @patch("ai_engineering.doctor.service._check_vcs_tools")
    @patch("ai_engineering.doctor.service._check_tools")
    @patch("ai_engineering.doctor.service._check_venv_health")
    @patch("ai_engineering.doctor.service._check_hooks")
    @patch("ai_engineering.doctor.service._check_state_files")
    @patch("ai_engineering.doctor.service._check_layout")
    def test_diagnose_default_flags_are_false(
        self,
        mock_layout: MagicMock,
        mock_state: MagicMock,
        mock_hooks: MagicMock,
        mock_venv: MagicMock,
        mock_tools: MagicMock,
        mock_vcs: MagicMock,
        mock_branch: MagicMock,
        mock_readiness: MagicMock,
        mock_version: MagicMock,
    ) -> None:
        """By default fix_hooks and fix_tools are False."""
        target = Path("/fake/project")
        diagnose(target)

        _, hooks_kwargs = mock_hooks.call_args
        assert hooks_kwargs["fix"] is False

        _, tools_kwargs = mock_tools.call_args
        assert tools_kwargs["fix"] is False

        _, venv_kwargs = mock_venv.call_args
        assert venv_kwargs["fix"] is False
