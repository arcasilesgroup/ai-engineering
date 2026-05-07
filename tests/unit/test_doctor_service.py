"""Tests for doctor/service.py orchestrator (spec-071, T-5.1).

Mocks all phase modules and runtime modules to verify orchestration
logic in isolation: phase ordering, runtime execution, pre-install
mode, fix/dry-run delegation, and audit log emission.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.doctor.models import (
    CheckResult,
    CheckStatus,
    DoctorContext,
    DoctorReport,
    PhaseReport,
)
from ai_engineering.doctor.service import (
    _PRE_INSTALL_RUNTIME,
    _RUNTIME_MODULES,
    diagnose,
)
from ai_engineering.installer.phases import PHASE_ORDER
from ai_engineering.state.models import InstallState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SVC = "ai_engineering.doctor.service"


def _ok_result(name: str = "test-check") -> CheckResult:
    return CheckResult(name=name, status=CheckStatus.OK, message="ok")


def _fail_result(name: str = "test-check", *, fixable: bool = False) -> CheckResult:
    return CheckResult(name=name, status=CheckStatus.FAIL, message="fail", fixable=fixable)


def _warn_result(name: str = "test-check", *, fixable: bool = False) -> CheckResult:
    return CheckResult(name=name, status=CheckStatus.WARN, message="warn", fixable=fixable)


def _fixed_result(name: str = "test-check") -> CheckResult:
    return CheckResult(name=name, status=CheckStatus.FIXED, message="fixed")


def _make_phase_module(results: list[CheckResult] | None = None) -> ModuleType:
    """Create a fake phase module with check() and fix() functions."""
    mod = ModuleType("fake_phase")
    mod.check = MagicMock(return_value=results or [_ok_result()])  # type: ignore[attr-defined]
    mod.fix = MagicMock(return_value=[])  # type: ignore[attr-defined]
    return mod


def _make_runtime_module(results: list[CheckResult] | None = None) -> ModuleType:
    """Create a fake runtime module with check() function."""
    mod = ModuleType("fake_runtime")
    mod.check = MagicMock(return_value=results or [_ok_result()])  # type: ignore[attr-defined]
    return mod


def _build_all_modules(
    phase_overrides: dict[str, ModuleType] | None = None,
    runtime_overrides: dict[str, ModuleType] | None = None,
) -> dict[str, ModuleType]:
    """Build the full module lookup dict for all phases and runtimes."""
    modules: dict[str, ModuleType] = {}
    po = phase_overrides or {}
    ro = runtime_overrides or {}
    for name in PHASE_ORDER:
        key = f"ai_engineering.doctor.phases.{name}"
        modules[key] = po.get(name, _make_phase_module())
    for name in _RUNTIME_MODULES:
        key = f"ai_engineering.doctor.runtime.{name}"
        modules[key] = ro.get(name, _make_runtime_module())
    return modules


def _phase_module_map(modules: dict[str, ModuleType]) -> dict[str, ModuleType]:
    return {name: modules[f"ai_engineering.doctor.phases.{name}"] for name in PHASE_ORDER}


def _runtime_module_map(modules: dict[str, ModuleType]) -> dict[str, ModuleType]:
    return {name: modules[f"ai_engineering.doctor.runtime.{name}"] for name in _RUNTIME_MODULES}


@pytest.fixture()
def target_dir(tmp_path: Path) -> Path:
    """Create a target directory with install-state.json present."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "install-state.json"
    state = InstallState()
    state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def target_dir_no_state(tmp_path: Path) -> Path:
    """Create a target directory WITHOUT install-state.json (pre-install)."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: diagnose() runs all 6 phases in PHASE_ORDER
# ---------------------------------------------------------------------------


class TestPhaseOrdering:
    def test_runs_all_phases_in_order(self, target_dir: Path) -> None:
        """diagnose() imports and calls check() for all 6 PHASE_ORDER phases."""
        executed_phases: list[str] = []
        modules = _build_all_modules()
        for name in PHASE_ORDER:
            module = modules[f"ai_engineering.doctor.phases.{name}"]
            module.check.side_effect = lambda _ctx, phase=name: (
                executed_phases.append(phase),
                [_ok_result()],
            )[1]

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir)

        assert executed_phases == list(PHASE_ORDER)
        assert len(report.phases) == len(PHASE_ORDER)
        for i, phase_report in enumerate(report.phases):
            assert phase_report.name == PHASE_ORDER[i]

    def test_run_phase_uses_reconciler_lifecycle(self, target_dir: Path, monkeypatch) -> None:
        """Doctor phase execution is routed through the shared reconciler."""
        from ai_engineering.doctor import service as service_module

        calls: list[tuple[str, bool]] = []
        real_reconciler = service_module.ResourceReconciler

        class _TrackingReconciler(real_reconciler):
            def run(self, adapter, context, *, preview: bool = False):
                calls.append((adapter.name, preview))
                return super().run(adapter, context, preview=preview)

        monkeypatch.setattr(service_module, "ResourceReconciler", _TrackingReconciler)
        monkeypatch.setattr(service_module, "_PHASE_MODULES", {"tools": _make_phase_module()})

        report = DoctorReport()
        service_module._run_phase(
            DoctorContext(target=target_dir),
            "tools",
            report,
            fix=False,
            dry_run=False,
        )

        assert calls == [("tools", False)]
        assert [phase.name for phase in report.phases] == ["tools"]


# ---------------------------------------------------------------------------
# Test 2: diagnose() runs 4 runtime checks after phases
# ---------------------------------------------------------------------------


class TestRuntimeChecks:
    def test_runs_all_runtime_modules(self, target_dir: Path) -> None:
        """diagnose() runs all 4 runtime modules and appends to report.runtime."""
        executed_runtimes: list[str] = []
        rt_overrides = {
            name: _make_runtime_module([_ok_result(f"rt-{name}")]) for name in _RUNTIME_MODULES
        }
        modules = _build_all_modules(runtime_overrides=rt_overrides)
        for name in _RUNTIME_MODULES:
            module = modules[f"ai_engineering.doctor.runtime.{name}"]
            module.check.side_effect = lambda _ctx, runtime=name: (
                executed_runtimes.append(runtime),
                [_ok_result(f"rt-{runtime}")],
            )[1]

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir)

        assert executed_runtimes == list(_RUNTIME_MODULES)
        assert len(report.runtime) == len(_RUNTIME_MODULES)


# ---------------------------------------------------------------------------
# Test 3: phase_filter only runs the filtered phase
# ---------------------------------------------------------------------------


class TestPhaseFilter:
    def test_phase_filter_only_runs_matching_phase(self, target_dir: Path) -> None:
        """diagnose(phase_filter='hooks') only runs the hooks phase."""
        executed_phases: list[str] = []
        modules = _build_all_modules()
        for name in PHASE_ORDER:
            module = modules[f"ai_engineering.doctor.phases.{name}"]
            module.check.side_effect = lambda _ctx, phase=name: (
                executed_phases.append(phase),
                [_ok_result()],
            )[1]

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir, phase_filter="hooks")

        assert executed_phases == ["hooks"]
        assert len(report.phases) == 1
        assert report.phases[0].name == "hooks"


# ---------------------------------------------------------------------------
# Test 4: fix=True calls fix() on phases with fixable failures
# ---------------------------------------------------------------------------


class TestFixMode:
    def test_fix_calls_fix_on_fixable_failures(self, target_dir: Path) -> None:
        """diagnose(fix=True) calls fix() for phases with fixable FAIL/WARN results."""
        hooks_mod = _make_phase_module(
            [_fail_result("hooks-integrity", fixable=True), _ok_result("hooks-scripts")]
        )
        hooks_mod.fix = MagicMock(  # type: ignore[attr-defined]
            return_value=[_fixed_result("hooks-integrity")]
        )
        modules = _build_all_modules(phase_overrides={"hooks": hooks_mod})

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir, fix=True)

        hooks_mod.fix.assert_called_once()
        call_args = hooks_mod.fix.call_args
        failed_arg = call_args[0][1]  # second positional arg
        assert len(failed_arg) == 1
        assert failed_arg[0].name == "hooks-integrity"
        assert failed_arg[0].fixable is True

        hooks_phase = next(p for p in report.phases if p.name == "hooks")
        fixed_check = next(c for c in hooks_phase.checks if c.name == "hooks-integrity")
        assert fixed_check.status == CheckStatus.FIXED

    def test_fix_does_not_call_fix_when_no_fixable(self, target_dir: Path) -> None:
        """diagnose(fix=True) skips fix() when all failures are non-fixable."""
        detect_mod = _make_phase_module([_fail_result("install-state-exists", fixable=False)])
        modules = _build_all_modules(phase_overrides={"detect": detect_mod})

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir, fix=True)

        detect_mod.fix.assert_not_called()

    def test_fix_also_fixes_fixable_warnings(self, target_dir: Path) -> None:
        """diagnose(fix=True) also calls fix() on WARN results that are fixable."""
        tools_mod = _make_phase_module([_warn_result("venv-health", fixable=True)])
        tools_mod.fix = MagicMock(  # type: ignore[attr-defined]
            return_value=[_fixed_result("venv-health")]
        )
        modules = _build_all_modules(phase_overrides={"tools": tools_mod})

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir, fix=True)

        tools_mod.fix.assert_called_once()
        tools_phase = next(p for p in report.phases if p.name == "tools")
        fixed_check = next(c for c in tools_phase.checks if c.name == "venv-health")
        assert fixed_check.status == CheckStatus.FIXED


# ---------------------------------------------------------------------------
# Test 5: fix=True, dry_run=True passes dry_run to fix()
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_passed_to_fix(self, target_dir: Path) -> None:
        """diagnose(fix=True, dry_run=True) passes dry_run=True to phase fix()."""
        hooks_mod = _make_phase_module([_fail_result("hooks-integrity", fixable=True)])
        hooks_mod.fix = MagicMock(  # type: ignore[attr-defined]
            return_value=[_fixed_result("hooks-integrity")]
        )
        modules = _build_all_modules(phase_overrides={"hooks": hooks_mod})

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir, fix=True, dry_run=True)

        hooks_mod.fix.assert_called_once()
        _, kwargs = hooks_mod.fix.call_args
        assert kwargs["dry_run"] is True


# ---------------------------------------------------------------------------
# Test 6: Pre-install mode (no install-state.json)
# ---------------------------------------------------------------------------


class TestPreInstallMode:
    def test_pre_install_runs_tools_and_limited_runtime(self, target_dir_no_state: Path) -> None:
        """Pre-install: only tools phase + branch_policy + version runtime."""
        executed_phases: list[str] = []
        executed_runtimes: list[str] = []
        modules = _build_all_modules()
        tools_module = modules["ai_engineering.doctor.phases.tools"]
        tools_module.check.side_effect = lambda _ctx: (
            executed_phases.append("tools"),
            [_ok_result()],
        )[1]
        for name in _PRE_INSTALL_RUNTIME:
            module = modules[f"ai_engineering.doctor.runtime.{name}"]
            module.check.side_effect = lambda _ctx, runtime=name: (
                executed_runtimes.append(runtime),
                [_ok_result(f"rt-{runtime}")],
            )[1]

        with (
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir_no_state)

        assert report.installed is False
        assert executed_phases == ["tools"]
        assert executed_runtimes == list(_PRE_INSTALL_RUNTIME)
        assert len(report.phases) == 1
        assert report.phases[0].name == "tools"
        assert len(report.runtime) == len(_PRE_INSTALL_RUNTIME)


# ---------------------------------------------------------------------------
# Test 7: Framework event is emitted on every call
# ---------------------------------------------------------------------------


class TestFrameworkEvents:
    def test_framework_event_emitted_on_diagnose(self, target_dir: Path) -> None:
        """diagnose() always emits a framework operation event."""
        modules = _build_all_modules()
        mock_emit = MagicMock()

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation", mock_emit),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir)

        mock_emit.assert_called_once()
        kwargs = mock_emit.call_args.kwargs
        assert kwargs["operation"] == "doctor"
        assert kwargs["component"] == "doctor"
        assert kwargs["metadata"]["mode"] == "diagnose"

    def test_framework_event_fix_mode(self, target_dir: Path) -> None:
        """Framework event mode is 'fix' when fix=True."""
        modules = _build_all_modules()
        mock_emit = MagicMock()

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation", mock_emit),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir, fix=True)

        assert mock_emit.call_args.kwargs["metadata"]["mode"] == "fix"

    def test_framework_event_tracks_fixes_applied(self, target_dir: Path) -> None:
        """Framework event includes names of checks with FIXED status."""
        hooks_mod = _make_phase_module([_fail_result("hooks-integrity", fixable=True)])
        hooks_mod.fix = MagicMock(  # type: ignore[attr-defined]
            return_value=[_fixed_result("hooks-integrity")]
        )
        modules = _build_all_modules(phase_overrides={"hooks": hooks_mod})
        mock_emit = MagicMock()

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation", mock_emit),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir, fix=True)

        assert "hooks-integrity" in mock_emit.call_args.kwargs["metadata"]["fixes_applied"]

    def test_framework_event_emitted_in_pre_install(self, target_dir_no_state: Path) -> None:
        """Framework event is emitted even in pre-install mode."""
        modules = _build_all_modules()
        mock_emit = MagicMock()

        with (
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation", mock_emit),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir_no_state)

        mock_emit.assert_called_once()
        assert mock_emit.call_args.kwargs["metadata"]["mode"] == "diagnose"


# ---------------------------------------------------------------------------
# Test 8: Report is correctly structured
# ---------------------------------------------------------------------------


class TestReportStructure:
    def test_report_has_phases_and_runtime(self, target_dir: Path) -> None:
        """Report contains both phases list and runtime list."""
        phase_overrides = {
            name: _make_phase_module([_ok_result(f"check-{name}")]) for name in PHASE_ORDER
        }
        rt_overrides = {
            name: _make_runtime_module([_ok_result(f"rt-{name}")]) for name in _RUNTIME_MODULES
        }
        modules = _build_all_modules(
            phase_overrides=phase_overrides, runtime_overrides=rt_overrides
        )

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir)

        assert isinstance(report, DoctorReport)
        assert report.installed is True
        assert len(report.phases) == len(PHASE_ORDER)
        assert all(isinstance(p, PhaseReport) for p in report.phases)
        assert len(report.runtime) == len(_RUNTIME_MODULES)
        assert all(isinstance(c, CheckResult) for c in report.runtime)

    def test_report_summary_counts(self, target_dir: Path) -> None:
        """Report summary counts checks by status."""
        phase_overrides = {PHASE_ORDER[0]: _make_phase_module([_fail_result("failing-check")])}
        modules = _build_all_modules(phase_overrides=phase_overrides)

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir)

        summary = report.summary
        assert "fail" in summary
        assert summary["fail"] >= 1
        assert "ok" in summary
        assert report.passed is False

    def test_report_passed_when_all_ok(self, target_dir: Path) -> None:
        """Report.passed is True when no FAIL status exists."""
        modules = _build_all_modules()

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation"),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            report = diagnose(target_dir)

        assert report.passed is True

    def test_framework_event_summary_fields(self, target_dir: Path) -> None:
        """Framework event metadata includes summary counters."""
        modules = _build_all_modules()
        mock_emit = MagicMock()

        with (
            patch(f"{_SVC}.load_install_state", return_value=InstallState()),
            patch(f"{_SVC}.load_manifest_config", return_value=None),
            patch(f"{_SVC}.emit_framework_operation", mock_emit),
            patch(f"{_SVC}._PHASE_MODULES", _phase_module_map(modules)),
            patch(f"{_SVC}._RUNTIME_CHECK_MODULES", _runtime_module_map(modules)),
        ):
            diagnose(target_dir)

        metadata = mock_emit.call_args.kwargs["metadata"]
        assert metadata["phases_checked"] == len(PHASE_ORDER)
        assert metadata["runtime_checked"] == len(_RUNTIME_MODULES)
        assert isinstance(metadata["summary"], dict)
        assert isinstance(metadata["fixes_applied"], list)
