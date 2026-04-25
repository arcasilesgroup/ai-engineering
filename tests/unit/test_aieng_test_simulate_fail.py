"""Unit tests for ``AIENG_TEST_SIMULATE_FAIL`` synthetic failure hook -- spec-101 T-2.17 RED.

D-101-11 reserves the env-gated test hook
``AIENG_TEST=1 AIENG_TEST_SIMULATE_FAIL=<tool>`` to deterministically
synthesize an install failure for a named tool without spawning the
real install mechanism. NG-8: the public CLI surface stays clean --
``AIENG_TEST=1`` is the gate, and without it the simulation env var
is a no-op.

The hook lives at :func:`ai_engineering.installer.user_scope_install._check_simulate_fail`:

* When ``AIENG_TEST != "1"`` -> returns ``None`` (no-op; real install
  path runs).
* When ``AIENG_TEST=1`` and ``AIENG_TEST_SIMULATE_FAIL`` does NOT list
  the tool name -> returns ``None``.
* When ``AIENG_TEST=1`` and ``AIENG_TEST_SIMULATE_FAIL`` lists the tool
  name (single name OR comma-separated list) -> returns a synthetic
  :class:`InstallResult` with ``failed=True``, ``stderr="simulated
  failure for testing"``, and ``mechanism="aieng_test_simulate_fail"``.

The hook is invoked by :class:`installer.phases.tools.ToolsPhase` BEFORE
the real ``mechanism.install()`` call so the synthetic failure flows
through the same record / EXIT 80 routing as a real install failure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.installer.mechanisms import InstallResult
from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
)
from ai_engineering.state.models import (
    InstallState,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)

# ---------------------------------------------------------------------------
# _check_simulate_fail unit-level
# ---------------------------------------------------------------------------


class TestCheckSimulateFailHelper:
    """Unit-level contract for the hook helper."""

    def test_no_env_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without ``AIENG_TEST=1``, the hook is a no-op (returns None)."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.delenv("AIENG_TEST", raising=False)
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        assert _check_simulate_fail("ruff") is None

    def test_aieng_test_set_but_no_target_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ``AIENG_TEST=1`` but no ``AIENG_TEST_SIMULATE_FAIL`` set, returns None."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.delenv("AIENG_TEST_SIMULATE_FAIL", raising=False)

        assert _check_simulate_fail("ruff") is None

    def test_target_does_not_match_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tool not in the SIMULATE_FAIL list -> hook returns None."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "gitleaks")

        assert _check_simulate_fail("ruff") is None

    def test_match_returns_synthetic_install_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Match -> returns ``InstallResult`` with the documented shape."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        result = _check_simulate_fail("ruff")

        assert result is not None
        assert isinstance(result, InstallResult)
        assert result.failed is True
        assert "simulated failure for testing" in result.stderr.lower()

    def test_comma_separated_list_matches_each_target(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``AIENG_TEST_SIMULATE_FAIL=ruff,ty`` -> both names trigger."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff,ty")

        ruff_result = _check_simulate_fail("ruff")
        ty_result = _check_simulate_fail("ty")
        gitleaks_result = _check_simulate_fail("gitleaks")

        assert ruff_result is not None and ruff_result.failed is True
        assert ty_result is not None and ty_result.failed is True
        # Untargeted tool stays a no-op.
        assert gitleaks_result is None

    def test_whitespace_in_list_tolerated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``AIENG_TEST_SIMULATE_FAIL='ruff,  ty '`` -> whitespace trimmed."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff,  ty ")

        assert _check_simulate_fail("ruff") is not None
        assert _check_simulate_fail("ty") is not None

    def test_aieng_test_other_value_disables_hook(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``AIENG_TEST=2`` (not the literal ``"1"``) keeps the hook off."""
        from ai_engineering.installer.user_scope_install import _check_simulate_fail

        monkeypatch.setenv("AIENG_TEST", "2")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        assert _check_simulate_fail("ruff") is None


# ---------------------------------------------------------------------------
# Integration: ToolsPhase consults the hook before invoking mechanism.install
# ---------------------------------------------------------------------------


class _FakeLoadResult:
    """Iterable test double mirroring ``state.manifest.LoadResult``."""

    def __init__(self, tools: list[ToolSpec]) -> None:
        self.tools = tools
        self.skipped_stacks: list[Any] = []

    def __iter__(self) -> Any:
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)


def _baseline_load() -> _FakeLoadResult:
    return _FakeLoadResult(
        tools=[
            ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL),
        ],
    )


def _registry(mech_for_tool: dict[str, MagicMock]) -> dict[str, Any]:
    return {
        name: {
            "darwin": [mech],
            "linux": [mech],
            "win32": [mech],
            "verify": {"cmd": ["echo", "ok"], "regex": r"\d+\.\d+\.\d+"},
        }
        for name, mech in mech_for_tool.items()
    }


@pytest.fixture()
def context(tmp_path: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


class TestToolsPhaseHookIntegration:
    """``ToolsPhase`` honours the simulation hook before invoking mechanisms."""

    def test_aieng_test_simulate_fail_ruff_only(
        self,
        context: InstallContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``AIENG_TEST=1 AIENG_TEST_SIMULATE_FAIL=ruff``: ruff fails, gitleaks installs."""
        from ai_engineering.installer.phases import tools as tools_phase

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        context.existing_state = InstallState()

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = InstallResult(
            failed=False, stderr="", mechanism="BrewMechanism"
        )
        ruff_mech = MagicMock()
        # ruff_mech.install must NOT be called -- the hook fires before it.
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase_result = phase.execute(plan, context)

        # gitleaks installed normally.
        gitleaks_mech.install.assert_called_once()
        # ruff's mechanism was NOT invoked (the hook short-circuited).
        ruff_mech.install.assert_not_called()

        records = context.existing_state.required_tools_state
        assert records["gitleaks"].state == ToolInstallState.INSTALLED
        assert records["ruff"].state == ToolInstallState.FAILED_NEEDS_MANUAL
        assert phase_result.failed, "ruff failure aggregates into PhaseResult.failed"

    def test_without_aieng_test_simulate_fail_has_no_effect(
        self,
        context: InstallContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without ``AIENG_TEST=1``, the env var is inert."""
        from ai_engineering.installer.phases import tools as tools_phase

        monkeypatch.delenv("AIENG_TEST", raising=False)
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        context.existing_state = InstallState()

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = InstallResult(
            failed=False, stderr="", mechanism="BrewMechanism"
        )
        ruff_mech = MagicMock()
        ruff_mech.install.return_value = InstallResult(
            failed=False, stderr="", mechanism="UvToolMechanism"
        )
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # Both real mechanisms invoked -- the hook is gated off.
        gitleaks_mech.install.assert_called_once()
        ruff_mech.install.assert_called_once()

    def test_simulate_fail_ruff_and_ty(
        self,
        context: InstallContext,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``AIENG_TEST_SIMULATE_FAIL=ruff,ty``: both targets fail synthetically."""
        from ai_engineering.installer.phases import tools as tools_phase

        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff,ty")

        context.existing_state = InstallState()

        # Provide three tools: gitleaks (passes), ruff (simulated fail),
        # ty (simulated fail).
        load_result = _FakeLoadResult(
            tools=[
                ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
                ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL),
                ToolSpec(name="ty", scope=ToolScope.USER_GLOBAL_UV_TOOL),
            ],
        )

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = InstallResult(
            failed=False, stderr="", mechanism="BrewMechanism"
        )
        ruff_mech = MagicMock()
        ty_mech = MagicMock()
        registry = _registry(
            {"gitleaks": gitleaks_mech, "ruff": ruff_mech, "ty": ty_mech},
        )

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        gitleaks_mech.install.assert_called_once()
        ruff_mech.install.assert_not_called()
        ty_mech.install.assert_not_called()

        records = context.existing_state.required_tools_state
        assert records["ruff"].state == ToolInstallState.FAILED_NEEDS_MANUAL
        assert records["ty"].state == ToolInstallState.FAILED_NEEDS_MANUAL
