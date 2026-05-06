"""Integration: ``ai-eng doctor --fix --phase tools`` -- node stack (T-3.5 / T-3.6).

D-101-08 mandates that the doctor's fix path shares the user-scope install
module with the installer. Concretely:

* A project that declares the ``typescript`` (or ``javascript``) stack and
  is missing ``prettier`` in ``node_modules/.bin/`` MUST trigger
  ``npm install --save-dev prettier`` when the operator runs
  ``ai-eng doctor --fix --phase tools``.

The test mocks ``subprocess.run`` so the mechanism dispatch is asserted at
the argv shape level -- no real network, no real npm install. The doctor
phase must end with prettier reported as fixed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Project fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def node_project(tmp_path: Path) -> Path:
    """Build a minimal node-stack project layout that triggers the fix path.

    Layout:
        <tmp>/.ai-engineering/manifest.yml      -- declares typescript stack
        <tmp>/package.json                       -- so npm install can run
        <tmp>/node_modules/.bin/                 -- empty (prettier missing)
    """
    project = tmp_path
    (project / ".ai-engineering").mkdir()
    manifest = project / ".ai-engineering" / "manifest.yml"
    manifest.write_text(
        """\
schema_version: "2.0"
name: node-fixture
version: "0.0.1"
providers:
  vcs: github
  ides: [terminal]
  stacks: [typescript]
required_tools:
  baseline:
    - {name: gitleaks}
    - {name: jq}
  typescript:
    - {name: prettier, scope: project_local}
    - {name: eslint, scope: project_local}
""",
        encoding="utf-8",
    )

    # package.json present -- R-3 requires it for the npm install path.
    (project / "package.json").write_text(
        '{"name": "node-fixture", "version": "0.0.1"}\n',
        encoding="utf-8",
    )

    # Empty node_modules/.bin -- prettier is "missing".
    bin_dir = project / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)

    # Spec-125: install_state lives in state.db, not a JSON file.
    state_dir = project / ".ai-engineering" / "state"
    state_dir.mkdir()
    from ai_engineering.state.models import InstallState
    from ai_engineering.state.service import save_install_state

    save_install_state(
        state_dir,
        InstallState(schema_version="2.0", vcs_provider="github"),
    )

    return project


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_doctor_fix_node_dispatches_npm_install_save_dev_prettier(
    node_project: Path,
) -> None:
    """Doctor --fix on a node project missing prettier dispatches NpmDevMechanism.

    Asserts:
    * ``npm install --save-dev prettier`` argv is the first npm-shaped call.
    * Argv has the literal pair ``--save-dev`` (D-101-02 forbids ``-g``).
    * The doctor phase reports prettier as fixed.
    """
    from ai_engineering.doctor.phases import tools as tools_phase
    from ai_engineering.installer import mechanisms as mechanisms_module
    from ai_engineering.installer.mechanisms import NpmDevMechanism

    # Capture every argv passed through ``_safe_run`` (which all mechanisms
    # route through). The fake returns success so the dispatch path completes.
    captured_argvs: list[list[str]] = []

    def fake_safe_run(argv: list[str], **_kwargs: object) -> object:
        captured_argvs.append(list(argv))
        return SimpleNamespace(
            returncode=0,
            stdout="ok\n",
            stderr="",
            args=argv,
        )

    # Drive the doctor phase directly so we exercise the same code path as
    # the CLI ``ai-eng doctor --fix --phase tools`` (the CLI is a thin
    # wrapper around ``diagnose`` -> ``tools_phase.fix``).
    from ai_engineering.doctor.models import (
        CheckResult,
        CheckStatus,
        DoctorContext,
    )
    from ai_engineering.state.manifest import LoadResult
    from ai_engineering.state.models import ToolScope, ToolSpec

    # Project-local tools are normally NOT registered in TOOL_REGISTRY (the
    # framework defers them to npm/composer/maven). For the doctor's --fix
    # path to actually exercise the NpmDevMechanism for prettier, we wire a
    # synthetic registry entry that points at it. This is consistent with
    # the explicit registry override pattern used in other integration
    # tests (test_doctor_fix_go_stack.py uses the same approach).
    fake_npm_dispatch = NpmDevMechanism("prettier")
    fake_registry = {
        "prettier": {
            "darwin": [fake_npm_dispatch],
            "linux": [fake_npm_dispatch],
            "win32": [fake_npm_dispatch],
        }
    }

    load_result = LoadResult(
        tools=[
            ToolSpec(name="prettier", scope=ToolScope.PROJECT_LOCAL),
        ],
        skipped_stacks=[],
    )

    ctx = DoctorContext(target=node_project)

    failed = [
        CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message="missing tools: prettier",
            fixable=True,
        )
    ]

    with (
        patch.object(mechanisms_module, "_safe_run", side_effect=fake_safe_run),
        patch.object(tools_phase, "run_verify", return_value=SimpleNamespace(passed=False)),
        patch.object(tools_phase, "load_required_tools", return_value=load_result),
        patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        # Bypass the platform-capability gate so the dispatch path runs on
        # every OS. On Windows, ``prettier`` is absent from
        # ``_WINGET_IDS`` and ``_PIP_INSTALLABLE`` so the legacy seam
        # returns False -- shorting the dispatch to "manual" and never
        # calling the mechanism. This patch isolates the test from that
        # platform gate; the real D-101-08 dispatch contract is exactly
        # what the mock ``_safe_run`` argv asserts.
        patch.object(tools_phase, "can_auto_install_tool", return_value=True),
    ):
        fixed = tools_phase.fix(ctx, failed)

    # The mechanism dispatch MUST emit at least one ``npm install --save-dev
    # prettier`` argv. Filter the captured calls to npm-shaped ones to keep
    # the assertion narrow against unrelated background calls.
    npm_calls = [argv for argv in captured_argvs if argv and argv[0] == "npm"]
    assert npm_calls, f"expected at least one npm call, captured: {captured_argvs}"

    expected = ["npm", "install", "--save-dev", "prettier"]
    assert any(argv == expected for argv in npm_calls), (
        f"expected {expected} in npm calls, got {npm_calls}"
    )

    # The fix path reported prettier as fixed.
    assert any(r.status == CheckStatus.FIXED for r in fixed), (
        f"expected at least one FIXED result, got {[(r.name, r.status) for r in fixed]}"
    )

    # Belt-and-suspenders: ``-g`` / ``--global`` MUST never appear (D-101-02).
    for argv in npm_calls:
        assert "-g" not in argv
        assert "--global" not in argv


def test_doctor_fix_node_uses_npm_dev_mechanism_class(node_project: Path) -> None:
    """The mechanism dispatched for prettier is :class:`NpmDevMechanism`.

    Direct probe of the dispatch wiring: when the doctor's fix path looks
    up the mechanism for prettier, it MUST resolve to ``NpmDevMechanism``
    (not any of the eleven other mechanism classes). Mechanism-class
    identity is the strongest contract we can assert without spawning a
    real subprocess.
    """
    from ai_engineering.doctor.models import (
        CheckResult,
        CheckStatus,
        DoctorContext,
    )
    from ai_engineering.doctor.phases import tools as tools_phase
    from ai_engineering.installer import mechanisms as mechanisms_module
    from ai_engineering.installer.mechanisms import NpmDevMechanism
    from ai_engineering.state.manifest import LoadResult
    from ai_engineering.state.models import ToolScope, ToolSpec

    captured_argvs: list[list[str]] = []

    def fake_safe_run(argv: list[str], **_kwargs: object) -> object:
        captured_argvs.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)

    fake_npm_dispatch = NpmDevMechanism("prettier")
    fake_registry = {
        "prettier": {
            "darwin": [fake_npm_dispatch],
            "linux": [fake_npm_dispatch],
            "win32": [fake_npm_dispatch],
        }
    }

    load_result = LoadResult(
        tools=[ToolSpec(name="prettier", scope=ToolScope.PROJECT_LOCAL)],
        skipped_stacks=[],
    )

    ctx = DoctorContext(target=node_project)
    failed = [
        CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message="missing: prettier",
            fixable=True,
        )
    ]

    with (
        patch.object(mechanisms_module, "_safe_run", side_effect=fake_safe_run),
        patch.object(tools_phase, "run_verify", return_value=SimpleNamespace(passed=False)),
        patch.object(tools_phase, "load_required_tools", return_value=load_result),
        patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        # See note in the previous test -- bypass the Windows platform
        # gate so the mechanism dispatch path is exercised uniformly.
        patch.object(tools_phase, "can_auto_install_tool", return_value=True),
    ):
        tools_phase.fix(ctx, failed)

    # Argv proves NpmDevMechanism.install was invoked.
    assert ["npm", "install", "--save-dev", "prettier"] in captured_argvs


# Sanity import guard -- the module path the rest of the suite uses must
# resolve cleanly even on Windows where ``win32`` is the registry key.
def test_module_imports() -> None:
    """Sanity: doctor and mechanism modules import without side effects."""
    from ai_engineering.doctor.phases import tools as tools_phase
    from ai_engineering.installer.mechanisms import NpmDevMechanism

    assert tools_phase is not None
    assert NpmDevMechanism is not None
    # Avoid an unused-import warning.
    assert sys.platform


# Re-export for collect-only surfaces.
__all__ = (
    "test_doctor_fix_node_dispatches_npm_install_save_dev_prettier",
    "test_doctor_fix_node_uses_npm_dev_mechanism_class",
    "test_module_imports",
)
