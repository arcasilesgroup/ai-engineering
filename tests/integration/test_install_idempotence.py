"""Integration tests for ``ai-eng install`` idempotence -- spec-101 T-2.15 RED.

Five scenarios per D-101-07:

* **happy skip**: a tool already in state ``installed`` with a passing
  verify probe AND matching ``os_release`` AND matching
  ``python_env_mode_recorded`` is skipped on the second run; zero
  install attempts, zero state mutations beyond the verify.
* **os_release bump**: when the recorded ``os_release`` differs from the
  current capture, the skip predicate fails and the tool is re-verified
  (to detect dylib-ABI breaks the version probe alone misses).
* **--force override**: even when state matches, ``--force`` re-installs
  unconditionally. The mechanism's ``install()`` is invoked.
* **python_env mode change**: when the recorded
  ``python_env_mode_recorded`` differs from the current manifest mode,
  python-stack tools are re-evaluated.
* **failed_needs_manual retried**: a previous ``failed_needs_manual``
  entry is retried on the next install; tools that were already
  ``installed`` stay skipped.

The skip predicate (D-101-07):

    skip = (state == installed)
       AND (verify command passes)
       AND (recorded os_release == current capture)
       AND (recorded python_env_mode_recorded == current manifest mode)

Any mismatch -> attempt re-install. ``--force`` bypasses the entire
predicate and always re-installs.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    PythonEnvMode,
    ToolInstallRecord,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    """Create the ``.ai-engineering/state/`` directory under tmp_path."""
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True, exist_ok=True)
    return state


@pytest.fixture()
def context(tmp_path: Path, state_dir: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


def _ok_result(mechanism: str = "BrewMechanism") -> InstallResult:
    return InstallResult(failed=False, stderr="", mechanism=mechanism)


def _failed_result(mechanism: str = "BrewMechanism") -> InstallResult:
    return InstallResult(failed=True, stderr="exit 1", mechanism=mechanism)


class _FakeLoadResult:
    """Minimal ``LoadResult`` double for ``ToolsPhase`` tests."""

    def __init__(self, tools: list[ToolSpec]) -> None:
        self.tools = tools
        self.skipped_stacks: list[Any] = []

    def __iter__(self) -> Any:
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)


def _baseline_load() -> _FakeLoadResult:
    """Two-tool baseline: gitleaks (uv-tool) + ruff (uv-tool)."""
    return _FakeLoadResult(
        tools=[
            ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL),
        ],
    )


def _registry(mech_for_tool: dict[str, MagicMock]) -> dict[str, Any]:
    """Build a fake ``TOOL_REGISTRY`` mapping each tool to a mocked mechanism."""
    return {
        name: {
            "darwin": [mech],
            "linux": [mech],
            "win32": [mech],
            "verify": {"cmd": ["echo", "ok"], "regex": r"\d+\.\d+\.\d+"},
        }
        for name, mech in mech_for_tool.items()
    }


def _seed_state(
    state: InstallState,
    *,
    tool: str,
    record_state: ToolInstallState = ToolInstallState.INSTALLED,
    os_release: str = "14.4",
    mechanism: str = "BrewMechanism",
    version: str = "1.2.3",
) -> None:
    """Seed ``InstallState`` with a previous-install record for ``tool``."""
    state.required_tools_state[tool] = ToolInstallRecord(
        state=record_state,
        mechanism=mechanism,
        version=version,
        verified_at=datetime.now(tz=UTC),
        os_release=os_release,
    )


def _ok_verify_result() -> Any:
    """Return a passing :class:`VerifyResult`."""
    from ai_engineering.installer.user_scope_install import VerifyResult

    return VerifyResult(passed=True, version="1.2.3", stderr="", error="")


def _bad_verify_result() -> Any:
    from ai_engineering.installer.user_scope_install import VerifyResult

    return VerifyResult(passed=False, version=None, stderr="not found", error="")


# ---------------------------------------------------------------------------
# Scenario 1 -- happy skip
# ---------------------------------------------------------------------------


class TestScenario1HappySkip:
    """First install records state; second install skips all tools.

    All four parts of the skip predicate match:
    * state == installed
    * verify passes
    * os_release matches the current capture
    * python_env_mode_recorded matches the current manifest mode
    """

    def test_second_run_skips_all_tools_when_state_matches(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase

        # Seed state: both tools previously installed under os_release=14.4
        # and python_env_mode=uv-tool.
        install_state = InstallState()
        _seed_state(install_state, tool="gitleaks", os_release="14.4")
        _seed_state(install_state, tool="ruff", os_release="14.4")
        install_state.python_env_mode_recorded = PythonEnvMode.UV_TOOL
        context.existing_state = install_state

        gitleaks_mech = MagicMock()
        ruff_mech = MagicMock()
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
            patch.object(tools_phase, "capture_os_release", return_value="14.4"),
            patch.object(tools_phase, "load_python_env_mode", return_value=PythonEnvMode.UV_TOOL),
            patch.object(tools_phase, "run_verify", return_value=_ok_verify_result()),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)

        # Zero install attempts -- both tools skipped.
        gitleaks_mech.install.assert_not_called()
        ruff_mech.install.assert_not_called()

        # State remains installed for both.
        assert install_state.required_tools_state["gitleaks"].state == ToolInstallState.INSTALLED
        assert install_state.required_tools_state["ruff"].state == ToolInstallState.INSTALLED

        # PhaseResult acknowledges the skip.
        skipped_names = {
            entry.split(":")[1] for entry in result.skipped if entry.startswith("tool:")
        }
        assert {"gitleaks", "ruff"}.issubset(skipped_names)
        # And no failures.
        assert not result.failed


# ---------------------------------------------------------------------------
# Scenario 2 -- os_release bump invalidates skip
# ---------------------------------------------------------------------------


class TestScenario2OsReleaseBump:
    """A bumped ``os_release`` triggers re-verify on the next run."""

    def test_os_release_mismatch_triggers_reverify(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase

        install_state = InstallState()
        _seed_state(install_state, tool="gitleaks", os_release="14.4")
        _seed_state(install_state, tool="ruff", os_release="14.4")
        install_state.python_env_mode_recorded = PythonEnvMode.UV_TOOL
        context.existing_state = install_state

        gitleaks_mech = MagicMock()
        ruff_mech = MagicMock()
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        verify_calls: list[Any] = []

        def _spy_verify(spec: dict[str, Any]) -> Any:
            verify_calls.append(spec)
            return _ok_verify_result()

        # Capture os_release returns 14.5 (one minor bump).
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
            patch.object(tools_phase, "capture_os_release", return_value="14.5"),
            patch.object(tools_phase, "load_python_env_mode", return_value=PythonEnvMode.UV_TOOL),
            patch.object(tools_phase, "run_verify", side_effect=_spy_verify),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # Verify was called for both tools (re-verify on os_release mismatch).
        assert len(verify_calls) == 2

        # The new os_release is recorded.
        for tool in ("gitleaks", "ruff"):
            assert install_state.required_tools_state[tool].os_release == "14.5"


# ---------------------------------------------------------------------------
# Scenario 3 -- --force override
# ---------------------------------------------------------------------------


class TestScenario3ForceOverride:
    """``--force`` re-installs every tool, ignoring the skip predicate."""

    def test_force_flag_reinstalls_even_when_state_matches(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase

        install_state = InstallState()
        _seed_state(install_state, tool="gitleaks", os_release="14.4")
        _seed_state(install_state, tool="ruff", os_release="14.4")
        install_state.python_env_mode_recorded = PythonEnvMode.UV_TOOL
        context.existing_state = install_state
        # Wire the --force flag onto the context.
        context.force = True  # type: ignore[attr-defined]

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = _ok_result()
        ruff_mech = MagicMock()
        ruff_mech.install.return_value = _ok_result()
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
            patch.object(tools_phase, "capture_os_release", return_value="14.4"),
            patch.object(tools_phase, "load_python_env_mode", return_value=PythonEnvMode.UV_TOOL),
            patch.object(tools_phase, "run_verify", return_value=_ok_verify_result()),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        gitleaks_mech.install.assert_called_once()
        ruff_mech.install.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario 4 -- python_env mode change
# ---------------------------------------------------------------------------


class TestScenario4PythonEnvModeChange:
    """A change in ``python_env.mode`` invalidates the skip for python tools."""

    def test_mode_change_uv_tool_to_venv_triggers_reverify(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase

        install_state = InstallState()
        _seed_state(install_state, tool="gitleaks", os_release="14.4")
        _seed_state(install_state, tool="ruff", os_release="14.4")
        install_state.python_env_mode_recorded = PythonEnvMode.UV_TOOL
        context.existing_state = install_state

        gitleaks_mech = MagicMock()
        ruff_mech = MagicMock()
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        verify_calls: list[Any] = []

        def _spy_verify(spec: dict[str, Any]) -> Any:
            verify_calls.append(spec)
            return _ok_verify_result()

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
            patch.object(tools_phase, "capture_os_release", return_value="14.4"),
            # Manifest now declares mode=venv.
            patch.object(tools_phase, "load_python_env_mode", return_value=PythonEnvMode.VENV),
            patch.object(tools_phase, "run_verify", side_effect=_spy_verify),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # python_env_mode mismatch -> re-verify both tools.
        assert len(verify_calls) == 2
        # The new mode is now recorded.
        assert install_state.python_env_mode_recorded == PythonEnvMode.VENV


# ---------------------------------------------------------------------------
# Scenario 5 -- failed_needs_manual is retried
# ---------------------------------------------------------------------------


class TestScenario5FailedNeedsManualRetried:
    """A previous ``failed_needs_manual`` entry is retried on the next run.

    Tools whose state is ``installed`` with a passing verify stay skipped;
    only the failed tool is re-attempted.
    """

    def test_failed_tool_is_retried_others_skipped(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase

        install_state = InstallState()
        # gitleaks previously failed; ruff installed successfully.
        _seed_state(
            install_state,
            tool="gitleaks",
            record_state=ToolInstallState.FAILED_NEEDS_MANUAL,
            os_release="14.4",
        )
        _seed_state(install_state, tool="ruff", os_release="14.4")
        install_state.python_env_mode_recorded = PythonEnvMode.UV_TOOL
        context.existing_state = install_state

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = _ok_result()  # retry succeeds.
        ruff_mech = MagicMock()
        # ruff should NOT have install() called (it's already installed).
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
            patch.object(tools_phase, "capture_os_release", return_value="14.4"),
            patch.object(tools_phase, "load_python_env_mode", return_value=PythonEnvMode.UV_TOOL),
            patch.object(tools_phase, "run_verify", return_value=_ok_verify_result()),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # gitleaks (previously failed) is retried; install() called.
        gitleaks_mech.install.assert_called_once()
        # ruff is skipped because state==installed and verify passed.
        ruff_mech.install.assert_not_called()

        # Final state: gitleaks is now installed.
        assert install_state.required_tools_state["gitleaks"].state == ToolInstallState.INSTALLED


# ---------------------------------------------------------------------------
# Bonus -- verify failure on otherwise-matching state triggers reinstall
# ---------------------------------------------------------------------------


class TestVerifyFailureForcesReinstall:
    """A failing verify probe (e.g. binary missing on disk) triggers reinstall.

    This is the "hidden break" scenario: state==installed and os_release
    matches but the verify command fails because someone deleted the
    binary. The skip predicate's verify-pass clause catches this.
    """

    def test_verify_fail_triggers_reinstall_attempt(
        self,
        context: InstallContext,
    ) -> None:
        from ai_engineering.installer.phases import tools as tools_phase

        install_state = InstallState()
        _seed_state(install_state, tool="gitleaks", os_release="14.4")
        _seed_state(install_state, tool="ruff", os_release="14.4")
        install_state.python_env_mode_recorded = PythonEnvMode.UV_TOOL
        context.existing_state = install_state

        gitleaks_mech = MagicMock()
        gitleaks_mech.install.return_value = _ok_result()
        ruff_mech = MagicMock()
        ruff_mech.install.return_value = _ok_result()
        registry = _registry({"gitleaks": gitleaks_mech, "ruff": ruff_mech})

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_baseline_load()),
            patch.object(tools_phase, "TOOL_REGISTRY", registry),
            patch.object(tools_phase, "capture_os_release", return_value="14.4"),
            patch.object(tools_phase, "load_python_env_mode", return_value=PythonEnvMode.UV_TOOL),
            patch.object(tools_phase, "run_verify", return_value=_bad_verify_result()),
        ):
            phase = tools_phase.ToolsPhase()
            plan = phase.plan(context)
            phase.execute(plan, context)

        # Both tools' verify failed; both attempt re-install.
        gitleaks_mech.install.assert_called_once()
        ruff_mech.install.assert_called_once()
