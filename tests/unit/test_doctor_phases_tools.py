"""Tests for doctor/phases/tools.py -- spec-101 doctor refactor.

This module is the legacy spec-071 test surface, rewritten in spec-101
T-3.2 / T-3.4 to reflect the new contracts:

* ``tools-required`` -- manifest-driven via :func:`load_required_tools`
  (NOT a hardcoded list); per-tool probe routes through
  :func:`run_verify` (NOT ``shutil.which``-only).
* ``venv-health``    -- branches on ``python_env.mode`` (D-101-12);
  ``uv-tool`` mode (default) skips the probe.
* ``venv-python``    -- gated on ``python_env.mode != uv-tool``.
* ``fix``            -- dispatches the registry's per-OS mechanism for
  each missing tool (D-101-08), not the legacy ``RemediationEngine``.

The deeper / mechanism-dispatch coverage lives in
``test_doctor_phase_tools.py`` (singular) -- this file pins the
top-level ``check()`` surface and the four per-check status outcomes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import tools as tools_phase
from ai_engineering.state.manifest import LoadResult
from ai_engineering.state.models import (
    InstallState,
    PythonEnvMode,
    ToolSpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_load_result() -> LoadResult:
    return LoadResult(tools=[], skipped_stacks=[])


def _verify_pass(_spec: object) -> object:
    return SimpleNamespace(passed=True, version="1.2.3", stderr="", error="")


def _verify_fail(_spec: object) -> object:
    return SimpleNamespace(passed=False, version=None, stderr="", error="")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with a healthy venv."""
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
def ctx(project: Path) -> DoctorContext:
    """DoctorContext targeting the temp project with no install state."""
    return DoctorContext(target=project)


@pytest.fixture()
def ctx_github(project: Path) -> DoctorContext:
    """DoctorContext with GitHub VCS provider in install state."""
    state = InstallState(vcs_provider="github")
    return DoctorContext(target=project, install_state=state)


@pytest.fixture()
def ctx_azure(project: Path) -> DoctorContext:
    """DoctorContext with Azure DevOps VCS provider in install state."""
    state = InstallState(vcs_provider="azure_devops")
    return DoctorContext(target=project, install_state=state)


# ---------------------------------------------------------------------------
# tools-required (spec-101 manifest-driven)
# ---------------------------------------------------------------------------


class TestToolsRequiredCheck:
    def test_ok_when_all_tools_verify(self, ctx: DoctorContext) -> None:
        load_result = LoadResult(
            tools=[ToolSpec(name="ruff"), ToolSpec(name="ty")],
            skipped_stacks=[],
        )
        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.OK

    def test_warn_when_tools_missing(self, ctx: DoctorContext) -> None:
        load_result = LoadResult(
            tools=[ToolSpec(name="gitleaks"), ToolSpec(name="ruff")],
            skipped_stacks=[],
        )

        def fake_verify(spec: object) -> object:
            cmd = (spec or {}).get("verify", {}).get("cmd", []) if isinstance(spec, dict) else []
            tool_name = cmd[0] if cmd else ""
            if tool_name == "gitleaks":
                return _verify_fail(spec)
            return _verify_pass(spec)

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=fake_verify),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.WARN
        assert required.fixable is True
        assert "gitleaks" in required.message

    def test_warn_when_all_tools_missing(self, ctx: DoctorContext) -> None:
        load_result = LoadResult(
            tools=[ToolSpec(name="ruff"), ToolSpec(name="ty")],
            skipped_stacks=[],
        )
        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
        ):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.WARN


# ---------------------------------------------------------------------------
# tools-vcs (unchanged from spec-071; preserved verbatim)
# ---------------------------------------------------------------------------


class TestToolsVcsCheck:
    def test_ok_when_no_install_state(self, ctx: DoctorContext) -> None:
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", return_value=True),
        ):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "skipping" in vcs.message

    def test_ok_when_github_and_gh_available(self, ctx_github: DoctorContext) -> None:
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", return_value=True),
        ):
            results = tools_phase.check(ctx_github)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "gh" in vcs.message

    def test_warn_when_github_and_gh_missing(self, ctx_github: DoctorContext) -> None:
        def mock_available(name: str) -> bool:
            return name != "gh"

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", side_effect=mock_available),
        ):
            results = tools_phase.check(ctx_github)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.WARN
        assert "gh" in vcs.message

    def test_ok_when_azure_and_az_available(self, ctx_azure: DoctorContext) -> None:
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", return_value=True),
        ):
            results = tools_phase.check(ctx_azure)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "az" in vcs.message

    def test_warn_when_azure_and_az_missing(self, ctx_azure: DoctorContext) -> None:
        def mock_available(name: str) -> bool:
            return name != "az"

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", side_effect=mock_available),
        ):
            results = tools_phase.check(ctx_azure)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.WARN
        assert "az" in vcs.message

    def test_ok_when_no_vcs_provider(self, project: Path) -> None:
        state = InstallState(vcs_provider=None)
        ctx = DoctorContext(target=project, install_state=state)

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", return_value=True),
        ):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK

    def test_ok_when_unknown_vcs_provider(self, project: Path) -> None:
        state = InstallState(vcs_provider="bitbucket")
        ctx = DoctorContext(target=project, install_state=state)

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(tools_phase, "is_tool_available", return_value=True),
        ):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "unknown" in vcs.message


# ---------------------------------------------------------------------------
# venv-health (D-101-12 mode-aware)
# ---------------------------------------------------------------------------


class TestVenvHealthCheck:
    """All venv-health probes test the legacy ``mode=venv`` path explicitly.

    The default ``uv-tool`` mode is covered by ``test_doctor_venv_health_skip.py``;
    here we pin the legacy probe behaviour by patching
    ``load_python_env_mode`` to ``VENV``.
    """

    def test_ok_with_healthy_venv(self, ctx: DoctorContext) -> None:
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.OK

    def test_warn_when_no_venv(self, tmp_path: Path) -> None:
        ctx_local = DoctorContext(target=tmp_path)

        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx_local)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.WARN
        assert health.fixable is True

    def test_fail_when_home_missing(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("home = /nonexistent/path\n", encoding="utf-8")

        ctx_local = DoctorContext(target=tmp_path)
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx_local)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.FAIL
        assert health.fixable is True
        assert "/nonexistent/path" in health.message

    def test_fail_when_no_home_key(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("version = 3.12.0\n", encoding="utf-8")

        ctx_local = DoctorContext(target=tmp_path)
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx_local)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.FAIL
        assert "home" in health.message


# ---------------------------------------------------------------------------
# venv-python (gated on mode != uv-tool)
# ---------------------------------------------------------------------------


class TestVenvPythonCheck:
    def test_ok_when_no_python_version_file(self, ctx: DoctorContext) -> None:
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.OK

    def test_ok_when_version_matches(self, project: Path) -> None:
        (project / ".python-version").write_text("3.12\n", encoding="utf-8")

        ctx_local = DoctorContext(target=project)
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx_local)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.OK

    def test_warn_when_version_mismatch(self, project: Path) -> None:
        (project / ".python-version").write_text("3.11\n", encoding="utf-8")

        ctx_local = DoctorContext(target=project)
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx_local)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.WARN
        assert "3.11" in pyver.message

    def test_warn_when_no_version_in_cfg(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        bindir = tmp_path / "fake_bin"
        bindir.mkdir()
        cfg = venv / "pyvenv.cfg"
        cfg.write_text(f"home = {bindir}\n", encoding="utf-8")
        (tmp_path / ".python-version").write_text("3.12\n", encoding="utf-8")

        ctx_local = DoctorContext(target=tmp_path)
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx_local)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.WARN
        assert "version" in pyver.message


# ---------------------------------------------------------------------------
# fix()
# ---------------------------------------------------------------------------


class TestToolsFix:
    """Mechanism-dispatch coverage; spec-101 D-101-08."""

    def test_fix_installs_missing_tools(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: ruff, ty",
                fixable=True,
            )
        ]

        installed: list[str] = []

        class _FakeMechanism:
            def __init__(self, tag: str) -> None:
                self.tag = tag

            def install(self) -> object:
                installed.append(self.tag)
                return SimpleNamespace(failed=False, stderr="")

        fake_registry = {
            "ruff": {
                "darwin": [_FakeMechanism("ruff")],
                "linux": [_FakeMechanism("ruff")],
                "win32": [_FakeMechanism("ruff")],
            },
            "ty": {
                "darwin": [_FakeMechanism("ty")],
                "linux": [_FakeMechanism("ty")],
                "win32": [_FakeMechanism("ty")],
            },
        }

        load_result = LoadResult(
            tools=[ToolSpec(name="ruff"), ToolSpec(name="ty")],
            skipped_stacks=[],
        )

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
            patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        ):
            fixed = tools_phase.fix(ctx, failed)

        assert {"ruff", "ty"} <= set(installed)
        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_tools_partial_success(self, ctx: DoctorContext) -> None:
        """Mechanism dispatch reports per-tool failure precisely.

        When one tool's mechanism succeeds but another's fails, the result
        is WARN with both ``installed:`` and ``install failed:`` parts.
        """
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: ruff, ty",
                fixable=True,
            )
        ]

        class _FakeMechanism:
            def __init__(self, *, succeed: bool) -> None:
                self.succeed = succeed

            def install(self) -> object:
                return SimpleNamespace(failed=not self.succeed, stderr="")

        fake_registry = {
            "ruff": {
                "darwin": [_FakeMechanism(succeed=True)],
                "linux": [_FakeMechanism(succeed=True)],
                "win32": [_FakeMechanism(succeed=True)],
            },
            "ty": {
                "darwin": [_FakeMechanism(succeed=False)],
                "linux": [_FakeMechanism(succeed=False)],
                "win32": [_FakeMechanism(succeed=False)],
            },
        }

        load_result = LoadResult(
            tools=[ToolSpec(name="ruff"), ToolSpec(name="ty")],
            skipped_stacks=[],
        )

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
            patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        ):
            fixed = tools_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.WARN
        # Mixed outcome surfaces both halves in the message.
        assert "ruff" in fixed[0].message
        assert "ty" in fixed[0].message

    def test_fix_tools_uses_manual_guidance_for_unsupported_tool(
        self,
        ctx: DoctorContext,
    ) -> None:
        """Tools without a registry entry surface ``manual follow-up required``."""
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: not-in-registry",
                fixable=True,
            )
        ]

        load_result = LoadResult(
            tools=[ToolSpec(name="not-in-registry")],
            skipped_stacks=[],
        )

        # Empty registry forces the "no-mechanism" branch.
        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
            patch.object(tools_phase, "TOOL_REGISTRY", {}),
        ):
            fixed = tools_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.WARN
        assert "manual follow-up required: not-in-registry" in fixed[0].message

    def test_fix_tools_dry_run(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: ruff",
                fixable=True,
            )
        ]

        class _FakeMechanism:
            def install(self) -> object:  # pragma: no cover - dry-run
                raise AssertionError("install must NOT be called in dry_run mode")

        fake_registry = {
            "ruff": {
                "darwin": [_FakeMechanism()],
                "linux": [_FakeMechanism()],
                "win32": [_FakeMechanism()],
            },
        }

        load_result = LoadResult(tools=[ToolSpec(name="ruff")], skipped_stacks=[])

        with (
            patch.object(tools_phase, "load_required_tools", return_value=load_result),
            patch.object(tools_phase, "run_verify", side_effect=_verify_fail),
            patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
        ):
            fixed = tools_phase.fix(ctx, failed, dry_run=True)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_venv_recreates(self, tmp_path: Path) -> None:
        ctx_local = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="no .venv",
                fixable=True,
            )
        ]

        with (
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["uv", "venv", ".venv"], returncode=0
            )
            fixed = tools_phase.fix(ctx_local, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["uv", "venv", ".venv"]

    def test_fix_venv_with_python_version(self, tmp_path: Path) -> None:
        (tmp_path / ".python-version").write_text("3.12\n", encoding="utf-8")
        ctx_local = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.FAIL,
                message="stale home path",
                fixable=True,
            )
        ]

        with (
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=["uv", "venv", "--python", "3.12", ".venv"],
                returncode=0,
            )
            fixed = tools_phase.fix(ctx_local, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED
        call_args = mock_run.call_args
        assert call_args[0][0] == ["uv", "venv", "--python", "3.12", ".venv"]

    def test_fix_venv_dry_run(self, tmp_path: Path) -> None:
        ctx_local = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="no .venv",
                fixable=True,
            )
        ]

        with (
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
            patch("subprocess.run") as mock_run,
        ):
            fixed = tools_phase.fix(ctx_local, failed, dry_run=True)

        mock_run.assert_not_called()
        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_venv_failure(self, tmp_path: Path) -> None:
        ctx_local = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.FAIL,
                message="stale",
                fixable=True,
            )
        ]

        with (
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
            patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "uv")),
        ):
            fixed = tools_phase.fix(ctx_local, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FAIL
        assert "failed to recreate" in fixed[0].message

    def test_fix_passes_through_non_fixable(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="tools-vcs",
                status=CheckStatus.WARN,
                message="gh not found",
            ),
            CheckResult(
                name="venv-python",
                status=CheckStatus.WARN,
                message="version mismatch",
            ),
        ]

        fixed = tools_phase.fix(ctx, failed)
        assert len(fixed) == 2
        assert all(r.status == CheckStatus.WARN for r in fixed)

    def test_check_returns_four_results(self, ctx: DoctorContext) -> None:
        with (
            patch.object(tools_phase, "load_required_tools", return_value=_empty_load_result()),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
        ):
            results = tools_phase.check(ctx)

        assert len(results) == 4
        names = {r.name for r in results}
        assert names == {"tools-required", "tools-vcs", "venv-health", "venv-python"}
