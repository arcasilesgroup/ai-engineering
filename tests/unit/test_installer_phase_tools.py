"""Unit tests for ``installer/phases/tools.py`` -- spec-101 T-2.1 RED + T-2.2 GREEN.

The tools phase is rewritten in T-2.2 to:

* Read the per-stack tool union via ``state.manifest.load_required_tools(stacks)``
  (instead of the legacy ``provider_required_tools`` VCS-only call).
* Dispatch the first matching ``installer.mechanisms.*`` mechanism for each
  tool by consulting ``installer.tool_registry.TOOL_REGISTRY[name][os]``.
* Record per-tool outcomes into ``InstallState.required_tools_state`` as
  :class:`ToolInstallRecord` instances (state ``installed`` on success,
  ``failed_needs_manual`` on mechanism failure).
* Aggregate ``PhaseResult`` -- ``failed=True`` when ANY required tool failed,
  per spec-101 D-101-03 (no silent passes).

These tests verify the contract end-to-end with the loader, mechanism
selection, and state propagation all mocked so no real subprocess runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:  # pragma: no cover - typing-only
    pass

from ai_engineering.installer.mechanisms import InstallResult
from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
)
from ai_engineering.state.models import (
    ToolInstallRecord,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def context(tmp_path: Path) -> InstallContext:
    """Build a minimal ``InstallContext`` -- python stack, github VCS."""
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


def _ok_install_result(mechanism: str = "BrewMechanism") -> InstallResult:
    return InstallResult(failed=False, stderr="", mechanism=mechanism)


def _failed_install_result(
    mechanism: str = "BrewMechanism",
    stderr: str = "exit 1: install failed",
) -> InstallResult:
    return InstallResult(failed=True, stderr=stderr, mechanism=mechanism)


class _FakeLoadResult:
    """Iterable test double mirroring ``state.manifest.LoadResult``."""

    def __init__(
        self,
        tools: list[ToolSpec],
        skipped_stacks: list[Any] | None = None,
    ) -> None:
        self.tools = tools
        self.skipped_stacks = skipped_stacks or []

    def __iter__(self) -> Any:
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)


def _baseline_load_result() -> _FakeLoadResult:
    """Return a fake ``LoadResult`` carrying gitleaks + ruff tools."""
    gitleaks = ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL)
    ruff = ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)
    return _FakeLoadResult(tools=[gitleaks, ruff])


# ---------------------------------------------------------------------------
# Contract: load_required_tools is called with stacks from context
# ---------------------------------------------------------------------------


class TestPlanReadsLoadRequiredTools:
    """``ToolsPhase`` must enumerate tools via ``load_required_tools``."""

    def test_plan_calls_load_required_tools_with_context_stacks(
        self,
        context: InstallContext,
    ) -> None:
        """Phase plan must call ``load_required_tools(context.stacks)``."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_baseline_load_result(),
        ) as loader_mock:
            ToolsPhase().plan(context)

        loader_mock.assert_called_once()
        kwargs = loader_mock.call_args.kwargs
        positional = loader_mock.call_args.args
        # Either positional (stacks=) or kw -- both forms are valid; assert
        # the resolved-stacks list is passed in.
        passed = positional[0] if positional else kwargs.get("stacks")
        assert list(passed) == context.stacks

    def test_execute_calls_load_required_tools_with_context_stacks(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases.tools import ToolsPhase

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_baseline_load_result(),
        ) as loader_mock:
            phase = ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # plan + execute -> at least one call (caching is OK as long as
        # at least one call passed the stacks).
        assert loader_mock.called
        all_passed = [
            (call.args[0] if call.args else call.kwargs.get("stacks"))
            for call in loader_mock.call_args_list
        ]
        assert any(list(stacks) == context.stacks for stacks in all_passed)


# ---------------------------------------------------------------------------
# Contract: per-tool mechanism dispatch
# ---------------------------------------------------------------------------


class TestExecuteDispatchesMechanisms:
    """Each returned tool must dispatch a mechanism from TOOL_REGISTRY[os]."""

    def test_execute_invokes_first_mechanism_install(
        self,
        context: InstallContext,
    ) -> None:
        """The first mechanism in the per-OS list is dispatched per tool."""
        from ai_engineering.installer.phases import tools as tools_phase

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = _ok_install_result("BrewMechanism")
        ruff_mech = MagicMock()
        ruff_mech.install.return_value = _ok_install_result("UvToolMechanism")

        registry = {
            "gitleaks": {
                "darwin": [gitleaks_mech],
                "linux": [gitleaks_mech],
                "win32": [gitleaks_mech],
                "verify": {"cmd": [], "regex": ""},
            },
            "ruff": {
                "darwin": [ruff_mech],
                "linux": [ruff_mech],
                "win32": [ruff_mech],
                "verify": {"cmd": [], "regex": ""},
            },
        }

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load_result()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        gitleaks_mech.install.assert_called_once()
        ruff_mech.install.assert_called_once()


# ---------------------------------------------------------------------------
# Contract: state recording into InstallState.required_tools_state
# ---------------------------------------------------------------------------


class TestStateRecording:
    """Successful and failed mechanisms record :class:`ToolInstallRecord`."""

    def test_successful_install_records_installed_state(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase
        from ai_engineering.state.models import InstallState

        install_state = InstallState()
        context.existing_state = install_state

        ok_mech = MagicMock()
        ok_mech.install.return_value = _ok_install_result("BrewMechanism")
        registry = {
            "gitleaks": {
                "darwin": [ok_mech],
                "linux": [ok_mech],
                "win32": [ok_mech],
                "verify": {"cmd": [], "regex": ""},
            },
            "ruff": {
                "darwin": [ok_mech],
                "linux": [ok_mech],
                "win32": [ok_mech],
                "verify": {"cmd": [], "regex": ""},
            },
        }

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load_result()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        records = install_state.required_tools_state
        assert "gitleaks" in records
        assert "ruff" in records
        assert isinstance(records["gitleaks"], ToolInstallRecord)
        assert records["gitleaks"].state == ToolInstallState.INSTALLED
        assert records["ruff"].state == ToolInstallState.INSTALLED

    def test_failed_install_records_failed_needs_manual(
        self,
        context: InstallContext,
    ) -> None:
        """A mechanism returning ``failed=True`` -> state failed_needs_manual."""
        from ai_engineering.installer.phases import tools as tools_phase
        from ai_engineering.state.models import InstallState

        install_state = InstallState()
        context.existing_state = install_state

        bad_mech = MagicMock()
        bad_mech.install.return_value = _failed_install_result(
            "BrewMechanism", stderr="brew bottle not found"
        )
        registry = {
            "gitleaks": {
                "darwin": [bad_mech],
                "linux": [bad_mech],
                "win32": [bad_mech],
                "verify": {"cmd": [], "regex": ""},
            },
            "ruff": {
                "darwin": [bad_mech],
                "linux": [bad_mech],
                "win32": [bad_mech],
                "verify": {"cmd": [], "regex": ""},
            },
        }

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load_result()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)

        records = install_state.required_tools_state
        assert "gitleaks" in records
        assert records["gitleaks"].state == ToolInstallState.FAILED_NEEDS_MANUAL
        # Per-tool error captured in result.failed (and warnings carry detail).
        assert result.failed, "PhaseResult.failed must list failed tools"


# ---------------------------------------------------------------------------
# Contract: PhaseResult.failed indicates aggregate failure
# ---------------------------------------------------------------------------


class TestPhaseResultAggregation:
    """``PhaseResult.failed`` aggregates per-tool failures (D-101-03)."""

    def test_phase_result_failed_when_any_tool_fails(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase
        from ai_engineering.state.models import InstallState

        context.existing_state = InstallState()

        ok_mech = MagicMock()
        ok_mech.install.return_value = _ok_install_result()
        bad_mech = MagicMock()
        bad_mech.install.return_value = _failed_install_result()

        registry = {
            "gitleaks": {
                "darwin": [ok_mech],
                "linux": [ok_mech],
                "win32": [ok_mech],
                "verify": {"cmd": [], "regex": ""},
            },
            "ruff": {
                "darwin": [bad_mech],
                "linux": [bad_mech],
                "win32": [bad_mech],
                "verify": {"cmd": [], "regex": ""},
            },
        }

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load_result()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)
            verdict = phase.verify(result, context)

        assert result.failed, "Aggregate failed list must contain failing tools"
        assert verdict.passed is False, (
            "PhaseVerdict.passed must be False when any required tool failed"
        )

    def test_phase_result_passes_when_all_tools_succeed(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase
        from ai_engineering.state.models import InstallState

        context.existing_state = InstallState()

        ok_mech = MagicMock()
        ok_mech.install.return_value = _ok_install_result()

        registry = {
            "gitleaks": {
                "darwin": [ok_mech],
                "linux": [ok_mech],
                "win32": [ok_mech],
                "verify": {"cmd": [], "regex": ""},
            },
            "ruff": {
                "darwin": [ok_mech],
                "linux": [ok_mech],
                "win32": [ok_mech],
                "verify": {"cmd": [], "regex": ""},
            },
        }

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load_result()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)
            verdict = phase.verify(result, context)

        assert not result.failed
        assert verdict.passed is True


# ---------------------------------------------------------------------------
# Contract: stack-level platform skip is honoured
# ---------------------------------------------------------------------------


class TestStackLevelPlatformSkip:
    """Skipped stacks (e.g. swift on linux) record ``skipped_platform_unsupported_stack``."""

    def test_skipped_stack_record_marks_state(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase
        from ai_engineering.state.manifest import StackSkip
        from ai_engineering.state.models import InstallState

        context.stacks = ["swift"]
        context.existing_state = InstallState()

        # Swift tools dropped via stack-level skip.
        load_result = _FakeLoadResult(
            tools=[],  # no tools when only stack-skipped stacks are requested
            skipped_stacks=[
                StackSkip(stack="swift", reason="swiftlint has no Linux/Windows binaries"),
            ],
        )

        with patch.object(tools_phase, "load_required_tools", return_value=load_result):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # The stack-level skip has nothing to install -- but the phase must
        # not crash on an empty tool list AND must not record records for the
        # skipped stack tools.
        records = context.existing_state.required_tools_state
        assert "swiftlint" not in records
        assert "swift-format" not in records
