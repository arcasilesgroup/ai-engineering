"""Tests for doctor/phases/tools.py -- tool availability and venv health checks."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import tools as tools_phase
from ai_engineering.state.models import InstallState


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with a healthy venv."""
    venv = tmp_path / ".venv"
    venv.mkdir()
    # Create a pyvenv.cfg with a valid home directory
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


# ── tools-required ─────────────────────────────────────────────────────


class TestToolsRequiredCheck:
    def test_ok_when_all_tools_available(self, ctx: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.OK

    def test_warn_when_tools_missing(self, ctx: DoctorContext) -> None:
        def mock_available(name: str) -> bool:
            return name not in ("gitleaks", "semgrep")

        with patch.object(tools_phase, "is_tool_available", side_effect=mock_available):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.WARN
        assert required.fixable is True
        assert "gitleaks" in required.message
        assert "semgrep" in required.message

    def test_warn_when_all_tools_missing(self, ctx: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=False):
            results = tools_phase.check(ctx)

        required = next(r for r in results if r.name == "tools-required")
        assert required.status == CheckStatus.WARN


# ── tools-vcs ──────────────────────────────────────────────────────────


class TestToolsVcsCheck:
    def test_ok_when_no_install_state(self, ctx: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "skipping" in vcs.message

    def test_ok_when_github_and_gh_available(self, ctx_github: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx_github)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "gh" in vcs.message

    def test_warn_when_github_and_gh_missing(self, ctx_github: DoctorContext) -> None:
        def mock_available(name: str) -> bool:
            return name != "gh"

        with patch.object(tools_phase, "is_tool_available", side_effect=mock_available):
            results = tools_phase.check(ctx_github)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.WARN
        assert "gh" in vcs.message

    def test_ok_when_azure_and_az_available(self, ctx_azure: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx_azure)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "az" in vcs.message

    def test_warn_when_azure_and_az_missing(self, ctx_azure: DoctorContext) -> None:
        def mock_available(name: str) -> bool:
            return name != "az"

        with patch.object(tools_phase, "is_tool_available", side_effect=mock_available):
            results = tools_phase.check(ctx_azure)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.WARN
        assert "az" in vcs.message

    def test_ok_when_no_vcs_provider(self, project: Path) -> None:
        state = InstallState(vcs_provider=None)
        ctx = DoctorContext(target=project, install_state=state)

        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK

    def test_ok_when_unknown_vcs_provider(self, project: Path) -> None:
        state = InstallState(vcs_provider="bitbucket")
        ctx = DoctorContext(target=project, install_state=state)

        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        vcs = next(r for r in results if r.name == "tools-vcs")
        assert vcs.status == CheckStatus.OK
        assert "unknown" in vcs.message


# ── venv-health ────────────────────────────────────────────────────────


class TestVenvHealthCheck:
    def test_ok_with_healthy_venv(self, ctx: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.OK

    def test_warn_when_no_venv(self, tmp_path: Path) -> None:
        ctx = DoctorContext(target=tmp_path)

        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.WARN
        assert health.fixable is True

    def test_fail_when_home_missing(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("home = /nonexistent/path\n", encoding="utf-8")

        ctx = DoctorContext(target=tmp_path)
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.FAIL
        assert health.fixable is True
        assert "/nonexistent/path" in health.message

    def test_fail_when_no_home_key(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        cfg = venv / "pyvenv.cfg"
        cfg.write_text("version = 3.12.0\n", encoding="utf-8")

        ctx = DoctorContext(target=tmp_path)
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.FAIL
        assert "home" in health.message


# ── venv-python ────────────────────────────────────────────────────────


class TestVenvPythonCheck:
    def test_ok_when_no_python_version_file(self, ctx: DoctorContext) -> None:
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.OK

    def test_ok_when_version_matches(self, project: Path) -> None:
        (project / ".python-version").write_text("3.12\n", encoding="utf-8")

        ctx = DoctorContext(target=project)
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.OK

    def test_warn_when_version_mismatch(self, project: Path) -> None:
        (project / ".python-version").write_text("3.11\n", encoding="utf-8")

        ctx = DoctorContext(target=project)
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

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

        ctx = DoctorContext(target=tmp_path)
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        pyver = next(r for r in results if r.name == "venv-python")
        assert pyver.status == CheckStatus.WARN
        assert "version" in pyver.message


# ── fix() ──────────────────────────────────────────────────────────────


class TestToolsFix:
    def test_fix_installs_missing_tools(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: gitleaks, semgrep",
                fixable=True,
            )
        ]

        with (
            patch.object(
                tools_phase,
                "is_tool_available",
                side_effect=lambda n: n not in ("gitleaks", "semgrep"),
            ),
            patch.object(tools_phase, "try_install", return_value=True),
        ):
            fixed = tools_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_tools_partial_success(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: gitleaks, semgrep",
                fixable=True,
            )
        ]

        def mock_install(pkg: str) -> bool:
            return pkg == "gitleaks"

        with (
            patch.object(
                tools_phase,
                "is_tool_available",
                side_effect=lambda n: n not in ("gitleaks", "semgrep"),
            ),
            patch.object(tools_phase, "try_install", side_effect=mock_install),
        ):
            fixed = tools_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.WARN
        assert "still missing" in fixed[0].message

    def test_fix_tools_dry_run(self, ctx: DoctorContext) -> None:
        failed = [
            CheckResult(
                name="tools-required",
                status=CheckStatus.WARN,
                message="missing tools: ruff",
                fixable=True,
            )
        ]

        with patch.object(tools_phase, "try_install") as mock_install:
            fixed = tools_phase.fix(ctx, failed, dry_run=True)

        mock_install.assert_not_called()
        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_venv_recreates(self, tmp_path: Path) -> None:
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="no .venv",
                fixable=True,
            )
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["uv", "venv", ".venv"], returncode=0
            )
            fixed = tools_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["uv", "venv", ".venv"]

    def test_fix_venv_with_python_version(self, tmp_path: Path) -> None:
        (tmp_path / ".python-version").write_text("3.12\n", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.FAIL,
                message="stale home path",
                fixable=True,
            )
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["uv", "venv", "--python", "3.12", ".venv"],
                returncode=0,
            )
            fixed = tools_phase.fix(ctx, failed)

        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED
        call_args = mock_run.call_args
        assert call_args[0][0] == ["uv", "venv", "--python", "3.12", ".venv"]

    def test_fix_venv_dry_run(self, tmp_path: Path) -> None:
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="no .venv",
                fixable=True,
            )
        ]

        with patch("subprocess.run") as mock_run:
            fixed = tools_phase.fix(ctx, failed, dry_run=True)

        mock_run.assert_not_called()
        assert len(fixed) == 1
        assert fixed[0].status == CheckStatus.FIXED

    def test_fix_venv_failure(self, tmp_path: Path) -> None:
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="venv-health",
                status=CheckStatus.FAIL,
                message="stale",
                fixable=True,
            )
        ]

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "uv")):
            fixed = tools_phase.fix(ctx, failed)

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
        with patch.object(tools_phase, "is_tool_available", return_value=True):
            results = tools_phase.check(ctx)

        assert len(results) == 4
        names = {r.name for r in results}
        assert names == {"tools-required", "tools-vcs", "venv-health", "venv-python"}
