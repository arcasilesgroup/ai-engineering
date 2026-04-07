"""Unit tests for doctor/service.py and doctor/models.py (spec-071 redesign).

Tests the phase-grouped diagnostic orchestrator and report models.
All doctor phase modules and runtime modules are mocked so these tests
exercise the service layer in isolation.

TDD-ready: AAA pattern, centralized fakes, behavior-focused assertions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from ai_engineering.doctor.models import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    PhaseReport,
)
from ai_engineering.doctor.service import _run_phase, _run_runtime_modules, diagnose
from ai_engineering.installer.phases import PHASE_ORDER

# -- Fixture: mock phase + runtime modules -----------------------------------

_RUNTIME_MODULES = ("vcs_auth", "feeds", "branch_policy", "version")


def _make_ok_check(name: str = "stub") -> MagicMock:
    """Return a mock phase/runtime module whose check() returns OK."""
    mod = MagicMock()
    mod.check.return_value = [
        CheckResult(name=name, status=CheckStatus.OK, message="ok"),
    ]
    mod.fix.return_value = []
    return mod


@pytest.fixture()
def _mock_all_modules(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Patch every doctor phase and runtime module with OK stubs.

    Returns a dict keyed by module name (e.g. "detect", "vcs_auth").
    """
    mocks: dict[str, MagicMock] = {}

    for phase in PHASE_ORDER:
        m = _make_ok_check(phase)
        monkeypatch.setattr(
            "ai_engineering.doctor.service.importlib.import_module",
            None,  # placeholder -- replaced below
        )
        mocks[phase] = m

    for rt in _RUNTIME_MODULES:
        mocks[rt] = _make_ok_check(rt)

    # Build a side_effect that returns the right mock per import path
    def _import_side_effect(name: str) -> MagicMock:
        for key, mock in mocks.items():
            if name.endswith(f".{key}"):
                return mock
        return MagicMock()

    monkeypatch.setattr(
        "ai_engineering.doctor.service.importlib.import_module",
        _import_side_effect,
    )

    # Mock state/config loading to simulate an installed project
    monkeypatch.setattr(
        "ai_engineering.doctor.service.load_install_state",
        lambda _: MagicMock(),
    )
    monkeypatch.setattr(
        "ai_engineering.doctor.service.load_manifest_config",
        lambda _: MagicMock(),
    )
    # Mock framework event emission
    monkeypatch.setattr(
        "ai_engineering.doctor.service.emit_framework_operation",
        lambda *_a, **_kw: None,
    )

    # Ensure install-state.json "exists" for the service logic
    return mocks


# -- CheckStatus -------------------------------------------------------------


class TestCheckStatus:
    def test_ok_value(self) -> None:
        assert CheckStatus.OK.value == "ok"

    def test_warn_value(self) -> None:
        assert CheckStatus.WARN.value == "warn"

    def test_fail_value(self) -> None:
        assert CheckStatus.FAIL.value == "fail"

    def test_fixed_value(self) -> None:
        assert CheckStatus.FIXED.value == "fixed"


# -- CheckResult --------------------------------------------------------------


class TestCheckResult:
    def test_creation_and_fields(self) -> None:
        result = CheckResult(name="test-check", status=CheckStatus.OK, message="all good")
        assert result.name == "test-check"
        assert result.status == CheckStatus.OK
        assert result.message == "all good"

    def test_fixable_defaults_to_false(self) -> None:
        result = CheckResult(name="t", status=CheckStatus.OK, message="")
        assert result.fixable is False


# -- PhaseReport --------------------------------------------------------------


class TestPhaseReport:
    def test_status_ok_when_all_ok(self) -> None:
        pr = PhaseReport(
            name="detect",
            checks=[CheckResult(name="a", status=CheckStatus.OK, message="ok")],
        )
        assert pr.status == CheckStatus.OK

    def test_status_fail_when_any_fail(self) -> None:
        pr = PhaseReport(
            name="detect",
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.FAIL, message="bad"),
            ],
        )
        assert pr.status == CheckStatus.FAIL

    def test_status_warn_when_warns_no_fails(self) -> None:
        pr = PhaseReport(
            name="detect",
            checks=[
                CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                CheckResult(name="b", status=CheckStatus.WARN, message="degraded"),
            ],
        )
        assert pr.status == CheckStatus.WARN

    def test_status_ok_when_empty(self) -> None:
        pr = PhaseReport(name="empty")
        assert pr.status == CheckStatus.OK

    def test_to_dict(self) -> None:
        pr = PhaseReport(
            name="tools",
            checks=[CheckResult(name="t", status=CheckStatus.OK, message="ok")],
        )
        d = pr.to_dict()
        assert d["name"] == "tools"
        assert d["status"] == "ok"
        assert len(d["checks"]) == 1


# -- DoctorReport -------------------------------------------------------------


class TestDoctorReport:
    def test_passed_with_all_ok(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[CheckResult(name="a", status=CheckStatus.OK, message="ok")],
                ),
            ],
        )
        assert report.passed is True

    def test_passed_with_warn_is_true(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.WARN, message="warning"),
                    ],
                ),
            ],
        )
        assert report.passed is True

    def test_passed_with_fail_is_false(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.FAIL, message="failed"),
                    ],
                ),
            ],
        )
        assert report.passed is False

    def test_passed_with_runtime_fail_is_false(self) -> None:
        report = DoctorReport(
            runtime=[CheckResult(name="rt", status=CheckStatus.FAIL, message="fail")],
        )
        assert report.passed is False

    def test_passed_with_fixed_is_true(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="hooks",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.FIXED, message="fixed"),
                        CheckResult(name="b", status=CheckStatus.OK, message="ok"),
                    ],
                ),
            ],
        )
        assert report.passed is True

    def test_empty_report_passed_is_true(self) -> None:
        assert DoctorReport().passed is True

    def test_summary_counts_by_status(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p1",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message=""),
                        CheckResult(name="b", status=CheckStatus.OK, message=""),
                        CheckResult(name="c", status=CheckStatus.WARN, message=""),
                    ],
                ),
            ],
            runtime=[
                CheckResult(name="d", status=CheckStatus.FAIL, message=""),
                CheckResult(name="e", status=CheckStatus.FIXED, message=""),
            ],
        )
        summary = report.summary
        assert summary == {"ok": 2, "warn": 1, "fail": 1, "fixed": 1}

    def test_summary_empty_report(self) -> None:
        assert DoctorReport().summary == {}

    def test_to_dict_serializable(self) -> None:
        import json

        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="test",
                    checks=[CheckResult(name="x", status=CheckStatus.OK, message="msg")],
                ),
            ],
        )
        data = report.to_dict()
        serialized = json.dumps(data)
        assert '"test"' in serialized
        assert "phases" in data
        assert "runtime" in data
        assert "passed" in data
        assert "summary" in data


# -- DoctorReport.has_warnings ------------------------------------------------


class TestDoctorReportHasWarnings:
    """Tests for DoctorReport.has_warnings -- True iff WARNs exist and no FAILs."""

    def test_has_warnings_true_when_warns_exist_no_fails(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.WARN, message="warning"),
                    ],
                ),
            ],
        )
        assert report.has_warnings is True

    def test_has_warnings_false_when_all_ok(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p",
                    checks=[CheckResult(name="a", status=CheckStatus.OK, message="ok")],
                ),
            ],
        )
        assert report.has_warnings is False

    def test_has_warnings_false_when_fails_exist(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.WARN, message="warning"),
                        CheckResult(name="b", status=CheckStatus.FAIL, message="failed"),
                    ],
                ),
            ],
        )
        assert report.has_warnings is False

    def test_has_warnings_false_on_empty_report(self) -> None:
        assert DoctorReport().has_warnings is False

    def test_has_warnings_true_with_multiple_warns(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.WARN, message="w1"),
                        CheckResult(name="b", status=CheckStatus.WARN, message="w2"),
                        CheckResult(name="c", status=CheckStatus.OK, message="ok"),
                    ],
                ),
            ],
        )
        assert report.has_warnings is True

    def test_has_warnings_false_with_fixed_only(self) -> None:
        report = DoctorReport(
            phases=[
                PhaseReport(
                    name="p",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.FIXED, message="fixed"),
                        CheckResult(name="b", status=CheckStatus.OK, message="ok"),
                    ],
                ),
            ],
        )
        assert report.has_warnings is False

    def test_has_warnings_true_in_runtime(self) -> None:
        report = DoctorReport(
            runtime=[CheckResult(name="rt", status=CheckStatus.WARN, message="w")],
        )
        assert report.has_warnings is True


# -- diagnose() ---------------------------------------------------------------


class TestDiagnose:
    """Tests for diagnose() -- uses mocked phase/runtime modules."""

    def test_all_phases_and_runtime_called(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        # Ensure install-state.json "exists"
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        report = diagnose(tmp_path)

        # All 6 phases + 4 runtime checks should produce results
        assert len(report.phases) == len(PHASE_ORDER)
        assert len(report.runtime) == len(_RUNTIME_MODULES)
        assert report.passed is True

    def test_report_has_phase_structure(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        report = diagnose(tmp_path)

        assert isinstance(report, DoctorReport)
        assert all(isinstance(p, PhaseReport) for p in report.phases)
        phase_names = [p.name for p in report.phases]
        assert phase_names == list(PHASE_ORDER)

    def test_report_fails_when_phase_injects_failure(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        # Inject a FAIL into the hooks phase
        _mock_all_modules["hooks"].check.return_value = [
            CheckResult(name="hooks-integrity", status=CheckStatus.FAIL, message="Missing hooks"),
        ]

        report = diagnose(tmp_path)

        assert report.passed is False
        hooks_phase = next(p for p in report.phases if p.name == "hooks")
        assert hooks_phase.status == CheckStatus.FAIL

    def test_report_passes_when_phase_injects_warning(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        _mock_all_modules["tools"].check.return_value = [
            CheckResult(name="tools-required", status=CheckStatus.WARN, message="ruff not found"),
        ]

        report = diagnose(tmp_path)

        assert report.passed is True
        tools_phase = next(p for p in report.phases if p.name == "tools")
        assert tools_phase.status == CheckStatus.WARN

    def test_fix_flag_triggers_fix_on_fixable_failures(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        _mock_all_modules["hooks"].check.return_value = [
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FAIL,
                message="Missing hooks",
                fixable=True,
            ),
        ]
        _mock_all_modules["hooks"].fix.return_value = [
            CheckResult(
                name="hooks-integrity",
                status=CheckStatus.FIXED,
                message="Reinstalled hooks",
            ),
        ]

        report = diagnose(tmp_path, fix=True)

        hooks_phase = next(p for p in report.phases if p.name == "hooks")
        assert any(c.status == CheckStatus.FIXED for c in hooks_phase.checks)

    def test_phase_filter_runs_single_phase(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        report = diagnose(tmp_path, phase_filter="hooks")

        assert len(report.phases) == 1
        assert report.phases[0].name == "hooks"

    def test_pre_install_mode_when_no_state(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        """When no install-state.json exists, report.installed is False."""
        # Override state loader to return None (no install)
        import ai_engineering.doctor.service as svc

        original = svc.load_install_state
        svc.load_install_state = lambda _: None
        try:
            report = diagnose(tmp_path)
        finally:
            svc.load_install_state = original

        assert report.installed is False

    def test_returns_doctor_report_type(
        self, tmp_path: Path, _mock_all_modules: dict[str, MagicMock]
    ) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("{}", encoding="utf-8")

        report = diagnose(tmp_path)
        assert isinstance(report, DoctorReport)


class TestValidationGuards:
    """Tests for phase/runtime validation guards against non-literal imports."""

    def test_run_phase_rejects_unknown_phase(self) -> None:
        ctx = MagicMock()
        report = DoctorReport(phases=[], runtime=[])
        with pytest.raises(ValueError, match="Unknown phase"):
            _run_phase(ctx, "nonexistent_phase", report, fix=False, dry_run=False)

    def test_run_runtime_rejects_unknown_module(self) -> None:
        ctx = MagicMock()
        report = DoctorReport(phases=[], runtime=[])
        with pytest.raises(ValueError, match="Unknown runtime module"):
            _run_runtime_modules(ctx, ("bogus_module",), report)


# -- doctor_cmd exit codes ----------------------------------------------------


class TestDoctorCmdExitCodes:
    """Tests for doctor_cmd exit codes: 0 (clean), 1 (fail), 2 (warnings only).

    Uses mocked diagnose() to control the DoctorReport returned, then invokes
    the CLI via CliRunner to capture the exit code.
    """

    @pytest.fixture()
    def app(self) -> typer.Typer:
        from ai_engineering.cli_factory import create_app

        return create_app()

    def test_exit_0_when_all_ok(self, app: typer.Typer, tmp_path: Path) -> None:
        """doctor exits 0 when all checks pass (no FAIL, no WARN)."""
        ok_report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.OK, message="ok"),
                    ],
                ),
            ],
        )

        with patch("ai_engineering.cli_commands.core.diagnose", return_value=ok_report):
            result = CliRunner().invoke(app, ["doctor", str(tmp_path)])

        assert result.exit_code == 0

    def test_exit_1_when_any_fail(self, app: typer.Typer, tmp_path: Path) -> None:
        """doctor exits 1 when any check is FAIL."""
        fail_report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.FAIL, message="broken"),
                    ],
                ),
            ],
        )

        with patch("ai_engineering.cli_commands.core.diagnose", return_value=fail_report):
            result = CliRunner().invoke(app, ["doctor", str(tmp_path)])

        assert result.exit_code == 1

    def test_exit_2_when_warns_only(self, app: typer.Typer, tmp_path: Path) -> None:
        """doctor exits 2 when warnings exist but no failures."""
        warn_report = DoctorReport(
            phases=[
                PhaseReport(
                    name="detect",
                    checks=[
                        CheckResult(name="a", status=CheckStatus.OK, message="ok"),
                        CheckResult(name="b", status=CheckStatus.WARN, message="degraded"),
                    ],
                ),
            ],
        )

        with patch("ai_engineering.cli_commands.core.diagnose", return_value=warn_report):
            result = CliRunner().invoke(app, ["doctor", str(tmp_path)])

        assert result.exit_code == 2
