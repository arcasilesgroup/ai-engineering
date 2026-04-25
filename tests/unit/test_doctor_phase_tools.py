"""Tests for the spec-101 doctor `tools` phase refactor (T-3.1 / T-3.2).

These tests pin the manifest-driven contract: ``_check_required_tools`` reads
``load_required_tools(resolved_stacks)`` (NOT a hardcoded list), probes each
tool through ``run_verify`` (the offline-safe wrapper from
``installer.user_scope_install``), and emits actionable repair messages that
reference the mechanism dispatch path (D-101-08).

Per phase-0-notes finding #3, the doctor phase keeps the FREE-FUNCTION
pattern -- we test the module-level ``_check_required_tools`` and ``check``
helpers, not a class.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases import tools as tools_phase
from ai_engineering.state.manifest import LoadResult
from ai_engineering.state.models import (
    InstallState,
    PythonEnvMode,
    StackSpec,
    ToolScope,
    ToolSpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project root with a healthy ``.venv`` layout."""
    venv = tmp_path / ".venv"
    venv.mkdir()
    bindir = tmp_path / "fake_python_bin"
    bindir.mkdir()
    cfg = venv / "pyvenv.cfg"
    cfg.write_text(
        f"home = {bindir}\nversion = 3.12.0\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def baseline_stack() -> StackSpec:
    """Return a baseline stack with two tools (gitleaks + jq)."""
    return StackSpec(
        name="baseline",
        tools=[
            ToolSpec(name="gitleaks"),
            ToolSpec(name="jq"),
        ],
    )


@pytest.fixture()
def python_stack() -> StackSpec:
    """Return a python stack with two tools (ruff + ty)."""
    return StackSpec(
        name="python",
        tools=[
            ToolSpec(name="ruff"),
            ToolSpec(name="ty"),
        ],
    )


def _build_load_result(*tool_specs: ToolSpec) -> LoadResult:
    """Helper: build a ``LoadResult`` from a flat list of ``ToolSpec``."""
    return LoadResult(tools=list(tool_specs), skipped_stacks=[])


def _verify_pass(_spec: object) -> object:
    """Stub ``run_verify`` returning a passed result."""
    return type("_VR", (), {"passed": True, "version": "1.2.3", "stderr": "", "error": ""})()


def _verify_fail(_spec: object) -> object:
    """Stub ``run_verify`` returning a failed result."""
    return type("_VR", (), {"passed": False, "version": None, "stderr": "", "error": ""})()


# ---------------------------------------------------------------------------
# T-3.1: manifest-driven required-tools check
# ---------------------------------------------------------------------------


class TestRequiredToolsManifestDriven:
    """The phase MUST source tool names from ``load_required_tools(stacks)``.

    Direct probe of the module: ``_check_required_tools`` and ``check`` must
    NOT reference a hardcoded ``_REQUIRED_TOOLS`` list. The legacy attribute
    is removed; tests below pin the contract.
    """

    def test_module_no_longer_carries_hardcoded_required_tools(self) -> None:
        """The hardcoded ``_REQUIRED_TOOLS`` literal is REMOVED in T-3.2."""
        assert not hasattr(tools_phase, "_REQUIRED_TOOLS"), (
            "doctor.phases.tools must read tools from load_required_tools(); "
            "hardcoded _REQUIRED_TOOLS must be removed"
        )

    def test_check_passes_when_all_tools_verify(
        self,
        project: Path,
        baseline_stack: StackSpec,
        python_stack: StackSpec,
    ) -> None:
        """Every tool's ``run_verify`` passes -> ``tools-required`` OK."""
        tools = [*baseline_stack.tools, *python_stack.tools]

        ctx = DoctorContext(target=project)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(*tools),
            ),
            patch.object(tools_phase, "is_tool_available", return_value=True),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.OK

    def test_check_warns_when_tool_verify_fails(
        self,
        project: Path,
        baseline_stack: StackSpec,
    ) -> None:
        """A failing ``run_verify`` for one tool -> WARN with names listed."""
        tools = list(baseline_stack.tools)

        ctx = DoctorContext(target=project)

        def fake_verify(spec: object) -> object:
            cmd = (spec or {}).get("verify", {}).get("cmd", []) if isinstance(spec, dict) else []
            tool_name = cmd[0] if cmd else ""
            if tool_name == "gitleaks":
                return _verify_fail(spec)
            return _verify_pass(spec)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(*tools),
            ),
            patch.object(tools_phase, "is_tool_available", return_value=True),
            patch.object(tools_phase, "run_verify", side_effect=fake_verify),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.WARN
        assert required.fixable is True
        assert "gitleaks" in required.message

    def test_check_uses_resolved_stacks_from_manifest(self, project: Path) -> None:
        """Phase passes the manifest's ``providers.stacks`` into the loader.

        The loader is the single source of truth for the stack list -- the
        phase MUST NOT recompute it. Smuggle a sentinel into the manifest
        and assert the loader call observes it.
        """
        manifest_dir = project / ".ai-engineering"
        manifest_dir.mkdir(exist_ok=True)
        manifest_path = manifest_dir / "manifest.yml"
        manifest_path.write_text(
            "providers:\n  stacks: [python, typescript]\n",
            encoding="utf-8",
        )

        ctx = DoctorContext(target=project)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(),
            ) as mock_load,
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
        ):
            tools_phase.check(ctx)

        # First positional arg is ``stacks``; kwargs may include ``root``.
        assert mock_load.call_count >= 1
        call_args = mock_load.call_args_list[0]
        # ``stacks`` is positional[0]; signature is load_required_tools(stacks, *, root).
        first_positional = call_args.args[0] if call_args.args else call_args.kwargs.get("stacks")
        observed = list(first_positional or [])
        assert "python" in observed and "typescript" in observed

    def test_failed_tool_message_references_mechanism_dispatch_for_fix(
        self,
        project: Path,
    ) -> None:
        """The check message MUST hint the user toward the fix path (D-101-08).

        ``ai-eng doctor --fix --phase tools`` is the canonical mechanism-
        dispatch entry point; its hint MUST appear in the actionable
        message so the operator knows the next step.
        """
        tools = [ToolSpec(name="ruff"), ToolSpec(name="ty")]

        ctx = DoctorContext(target=project)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(*tools),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        # Actionable hint: doctor --fix is the canonical repair surface.
        assert "ai-eng doctor --fix" in required.message or "doctor --fix" in required.message

    def test_check_skips_project_local_tools(self, project: Path) -> None:
        """``project_local`` tools are NOT installed by the framework.

        D-101-15: project_local tools (npm/composer/maven-managed) are
        invoked via launchers at gate time; the doctor phase MUST NOT
        report them as missing.
        """
        tools = [
            ToolSpec(name="ruff"),  # user_global -- probed
            ToolSpec(name="prettier", scope=ToolScope.PROJECT_LOCAL),  # skipped
        ]

        ctx = DoctorContext(target=project)

        verify_calls: list[object] = []

        def record_verify(spec: object) -> object:
            verify_calls.append(spec)
            return _verify_pass(spec)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(*tools),
            ),
            patch.object(tools_phase, "is_tool_available", return_value=True),
            patch.object(tools_phase, "run_verify", side_effect=record_verify),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        # ruff probed, prettier skipped (one call total).
        assert len(verify_calls) == 1
        assert required.status == CheckStatus.OK


# ---------------------------------------------------------------------------
# T-3.2 GREEN: fix() dispatches mechanism, not RemediationEngine
# ---------------------------------------------------------------------------


class TestFixDispatchesMechanism:
    """``fix()`` for ``tools-required`` MUST route through the mechanism.

    D-101-08 mandates that doctor ``--fix --phase tools`` shares the same
    user-scope install module as the installer. The legacy
    ``RemediationEngine`` path is replaced; the new path resolves each
    failed tool via ``TOOL_REGISTRY`` and dispatches the first per-OS
    mechanism's ``install()``.
    """

    def test_fix_dispatches_first_mechanism_per_tool(self, project: Path) -> None:
        """Each failed tool's first registry mechanism is invoked."""
        from ai_engineering.doctor.models import CheckResult

        ctx = DoctorContext(target=project)

        installed_calls: list[str] = []

        class _FakeMechanism:
            def __init__(self, tag: str) -> None:
                self.tag = tag

            def install(self) -> object:
                installed_calls.append(self.tag)
                return type(
                    "_IR",
                    (),
                    {"failed": False, "stderr": "", "mechanism": "_FakeMechanism"},
                )()

        fake_registry = {
            "ruff": {"darwin": [_FakeMechanism("ruff")], "linux": [_FakeMechanism("ruff")]},
            "ty": {"darwin": [_FakeMechanism("ty")], "linux": [_FakeMechanism("ty")]},
        }

        load_result = _build_load_result(ToolSpec(name="ruff"), ToolSpec(name="ty"))

        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: ruff, ty",
                fixable=True,
            )
        ]

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
            patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        ):
            fixed = tools_phase.fix(ctx, failed)

        assert {"ruff", "ty"} <= set(installed_calls), (
            f"expected mechanism dispatch for both tools, got {installed_calls}"
        )
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_dry_run_does_not_invoke_mechanism(self, project: Path) -> None:
        """``dry_run=True`` MUST NOT spawn install mechanisms."""
        from ai_engineering.doctor.models import CheckResult

        ctx = DoctorContext(target=project)

        installed_calls: list[str] = []

        class _FakeMechanism:
            def install(self) -> object:
                installed_calls.append("ruff")
                return type("_IR", (), {"failed": False, "stderr": ""})()

        fake_registry = {
            "ruff": {"darwin": [_FakeMechanism()], "linux": [_FakeMechanism()]},
        }

        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: ruff",
                fixable=True,
            )
        ]

        load_result = _build_load_result(ToolSpec(name="ruff"))

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
            patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        ):
            fixed = tools_phase.fix(ctx, failed, dry_run=True)

        assert installed_calls == []
        assert fixed[0].status == CheckStatus.FIXED  # dry-run reports as if fixed.


# ---------------------------------------------------------------------------
# python_env.mode awareness (T-3.4 prep)
# ---------------------------------------------------------------------------


class TestPythonEnvModeAwareness:
    """The required-tools check MUST honour ``python_env.mode``.

    In ``uv-tool`` mode (the spec-101 default), tools live in
    ``~/.local/share/uv/tools/`` and resolve via PATH.

    In ``venv`` mode (legacy), the project-local ``.venv/bin/`` is the
    expected resolution prefix. The phase passes ``run_verify`` either
    shape -- the test asserts the seam exists by patching
    ``load_python_env_mode`` and observing the call.
    """

    def test_check_consults_load_python_env_mode(self, project: Path) -> None:
        """``load_python_env_mode`` is invoked exactly once per ``check``."""
        ctx = DoctorContext(target=project)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.UV_TOOL,
            ) as mock_mode,
        ):
            tools_phase.check(ctx)

        # Mode probed at least once during the check.
        assert mock_mode.call_count >= 1


# ---------------------------------------------------------------------------
# Existing tools-vcs / venv-python regression coverage
# ---------------------------------------------------------------------------


class TestPhaseRegressions:
    """Pre-existing checks (``tools-vcs``, ``venv-python``) keep working."""

    def test_check_returns_four_results(self, project: Path) -> None:
        """``check`` aggregates four check results (T-3.4 keeps shape)."""
        ctx = DoctorContext(target=project)
        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
        ):
            results = tools_phase.check(ctx)

        assert len(results) == 4
        names = {r.name for r in results}
        assert names == {"tools-required", "tools-vcs", "venv-health", "venv-python"}

    def test_tools_vcs_still_warns_on_missing_gh(self, project: Path) -> None:
        """``tools-vcs`` retains its VCS-tool probe behaviour."""
        state = InstallState(vcs_provider="github")
        ctx = DoctorContext(target=project, install_state=state)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_build_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", side_effect=lambda n: n != "gh"),
        ):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.WARN
        assert "gh" in vcs.message
