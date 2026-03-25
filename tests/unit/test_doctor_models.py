"""Unit tests for the redesigned doctor models (spec-071)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.doctor.models import (
    CheckResult,
    CheckStatus,
    DoctorContext,
    DoctorReport,
    PhaseReport,
)

# ---------------------------------------------------------------------------
# CheckStatus
# ---------------------------------------------------------------------------


class TestCheckStatus:
    def test_enum_values(self):
        assert CheckStatus.OK == "ok"
        assert CheckStatus.WARN == "warn"
        assert CheckStatus.FAIL == "fail"
        assert CheckStatus.FIXED == "fixed"

    def test_str_enum(self):
        assert str(CheckStatus.OK) == "ok"


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_creation(self):
        r = CheckResult(name="test-check", status=CheckStatus.OK, message="all good")
        assert r.name == "test-check"
        assert r.status == CheckStatus.OK
        assert r.message == "all good"

    def test_fixable_default_false(self):
        r = CheckResult(name="x", status=CheckStatus.OK, message="")
        assert r.fixable is False

    def test_fixable_explicit(self):
        r = CheckResult(name="x", status=CheckStatus.FAIL, message="", fixable=True)
        assert r.fixable is True


# ---------------------------------------------------------------------------
# PhaseReport
# ---------------------------------------------------------------------------


class TestPhaseReport:
    def test_creation(self):
        checks = [
            CheckResult(name="a", status=CheckStatus.OK, message="ok"),
            CheckResult(name="b", status=CheckStatus.WARN, message="warn"),
        ]
        pr = PhaseReport(name="governance", checks=checks)
        assert pr.name == "governance"
        assert len(pr.checks) == 2

    def test_status_all_ok(self):
        pr = PhaseReport(
            name="detect",
            checks=[CheckResult(name="a", status=CheckStatus.OK, message="")],
        )
        assert pr.status == CheckStatus.OK

    def test_status_warn_no_fail(self):
        pr = PhaseReport(
            name="detect",
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message=""),
                CheckResult(name="b", status=CheckStatus.WARN, message=""),
            ],
        )
        assert pr.status == CheckStatus.WARN

    def test_status_fail_overrides_warn(self):
        pr = PhaseReport(
            name="detect",
            checks=[
                CheckResult(name="a", status=CheckStatus.WARN, message=""),
                CheckResult(name="b", status=CheckStatus.FAIL, message=""),
            ],
        )
        assert pr.status == CheckStatus.FAIL

    def test_status_fixed_treated_as_ok(self):
        pr = PhaseReport(
            name="hooks",
            checks=[
                CheckResult(name="a", status=CheckStatus.FIXED, message=""),
                CheckResult(name="b", status=CheckStatus.OK, message=""),
            ],
        )
        assert pr.status == CheckStatus.OK

    def test_empty_checks(self):
        pr = PhaseReport(name="empty", checks=[])
        assert pr.status == CheckStatus.OK

    def test_to_dict(self):
        pr = PhaseReport(
            name="tools",
            checks=[CheckResult(name="c", status=CheckStatus.OK, message="found")],
        )
        d = pr.to_dict()
        assert d["name"] == "tools"
        assert d["status"] == "ok"
        assert len(d["checks"]) == 1
        assert d["checks"][0]["name"] == "c"


# ---------------------------------------------------------------------------
# DoctorContext
# ---------------------------------------------------------------------------


class TestDoctorContext:
    def test_creation_minimal(self):
        ctx = DoctorContext(target=Path("/fake"))
        assert ctx.target == Path("/fake")
        assert ctx.install_state is None
        assert ctx.manifest_config is None
        assert ctx.fix_mode is False
        assert ctx.dry_run is False
        assert ctx.phase_filter is None

    def test_creation_full(self):
        ctx = DoctorContext(
            target=Path("/project"),
            install_state=None,
            manifest_config=None,
            fix_mode=True,
            dry_run=True,
            phase_filter="hooks",
        )
        assert ctx.fix_mode is True
        assert ctx.dry_run is True
        assert ctx.phase_filter == "hooks"

    def test_frozen(self):
        ctx = DoctorContext(target=Path("/fake"))
        with pytest.raises(AttributeError):
            ctx.fix_mode = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DoctorReport
# ---------------------------------------------------------------------------


class TestDoctorReport:
    def test_creation_defaults(self):
        report = DoctorReport()
        assert report.installed is True
        assert report.phases == []
        assert report.runtime == []

    def test_passed_all_ok(self):
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[CheckResult(name="a", status=CheckStatus.OK, message="")],
                )
            ]
        )
        assert report.passed is True

    def test_passed_false_on_fail(self):
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[CheckResult(name="a", status=CheckStatus.FAIL, message="bad")],
                )
            ]
        )
        assert report.passed is False

    def test_passed_false_on_runtime_fail(self):
        report = DoctorReport(
            runtime=[CheckResult(name="vcs-auth", status=CheckStatus.FAIL, message="no auth")]
        )
        assert report.passed is False

    def test_has_warnings(self):
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="tools",
                    checks=[CheckResult(name="a", status=CheckStatus.WARN, message="")],
                )
            ]
        )
        assert report.has_warnings is True

    def test_has_warnings_false_when_fail(self):
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="tools",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.WARN, message=""),
                        CheckResult(name="b", status=CheckStatus.FAIL, message=""),
                    ],
                )
            ]
        )
        assert report.has_warnings is False

    def test_summary(self):
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message=""),
                        CheckResult(name="b", status=CheckStatus.OK, message=""),
                    ],
                ),
                PhaseReport(
                    name="tools",
                    checks=[
                        CheckResult(name="c", status=CheckStatus.WARN, message=""),
                    ],
                ),
            ],
            runtime=[
                CheckResult(name="d", status=CheckStatus.OK, message=""),
            ],
        )
        s = report.summary
        assert s["ok"] == 3
        assert s["warn"] == 1

    def test_to_dict_schema(self):
        report = DoctorReport(
            installed=True,
            phases=[
                PhaseReport(
                    name="governance",
                    checks=[
                        CheckResult(
                            name="manifest-exists",
                            status=CheckStatus.OK,
                            message="present",
                        )
                    ],
                )
            ],
            runtime=[
                CheckResult(
                    name="vcs-auth",
                    status=CheckStatus.OK,
                    message="authenticated",
                )
            ],
        )
        d = report.to_dict()
        assert d["installed"] is True
        assert "phases" in d
        assert "runtime" in d
        assert "summary" in d
        assert "passed" in d
        assert d["phases"][0]["name"] == "governance"
        assert d["runtime"][0]["name"] == "vcs-auth"

    def test_empty_report(self):
        report = DoctorReport()
        assert report.passed is True
        assert report.has_warnings is False
        assert report.summary == {}
