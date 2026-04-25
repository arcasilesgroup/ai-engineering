"""Tests for ``_check_venv_health`` python_env.mode awareness (T-3.3 / T-3.4).

D-101-12: ``python_env.mode=uv-tool`` (the spec-101 default) eliminates the
project-local ``.venv/`` entirely. The doctor's venv-health probe MUST
recognise the mode and skip the probe rather than emitting a misleading
``no .venv/pyvenv.cfg found`` warning.

Behaviour matrix:

| mode             | venv-health status        |
|------------------|---------------------------|
| ``uv-tool``      | OK (skipped, not_applicable) |
| ``venv``         | runs current probe         |
| ``shared-parent``| probes the shared-parent venv |
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases import tools as tools_phase
from ai_engineering.state.manifest import LoadResult
from ai_engineering.state.models import PythonEnvMode

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_no_venv(tmp_path: Path) -> Path:
    """Project root with NO ``.venv/`` directory."""
    return tmp_path


@pytest.fixture()
def project_with_venv(tmp_path: Path) -> Path:
    """Project root with a healthy ``.venv/pyvenv.cfg``."""
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


def _empty_load_result() -> LoadResult:
    return LoadResult(tools=[], skipped_stacks=[])


def _verify_pass(_spec: object) -> object:
    return type("_VR", (), {"passed": True, "version": "1.2.3", "stderr": "", "error": ""})()


# ---------------------------------------------------------------------------
# T-3.3: python_env.mode=uv-tool -> skip the venv-health probe
# ---------------------------------------------------------------------------


class TestVenvHealthSkipInUvToolMode:
    """``mode=uv-tool`` -> the venv-health probe is suppressed."""

    def test_uv_tool_mode_emits_ok_when_no_venv_present(
        self,
        project_no_venv: Path,
    ) -> None:
        """No ``.venv`` AND ``mode=uv-tool`` -> OK (not_applicable)."""
        ctx = DoctorContext(target=project_no_venv)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_empty_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.UV_TOOL,
            ),
        ):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        # In uv-tool mode the venv probe is NOT applicable; surface as OK
        # (not WARN) so the user is not nudged to run a needless ``uv venv``.
        assert health.status == CheckStatus.OK
        # The message should explain why the probe was skipped.
        message_lower = health.message.lower()
        assert (
            "uv-tool" in message_lower
            or "not applicable" in message_lower
            or "skipped" in message_lower
        )

    def test_uv_tool_mode_does_not_emit_fixable_warning(
        self,
        project_no_venv: Path,
    ) -> None:
        """Skipped probes MUST NOT carry ``fixable=True``.

        The fixable flag would surface ``ai-eng doctor --fix --phase tools``
        prompts that try to recreate ``.venv`` -- exactly the worktree
        re-install pain D-101-12 was written to eliminate.
        """
        ctx = DoctorContext(target=project_no_venv)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_empty_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.UV_TOOL,
            ),
        ):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.fixable is False


# ---------------------------------------------------------------------------
# T-3.3: python_env.mode=venv -> existing probes keep running
# ---------------------------------------------------------------------------


class TestVenvHealthLegacyMode:
    """``mode=venv`` -> the legacy venv-health probe still runs."""

    def test_venv_mode_warns_when_no_venv(self, project_no_venv: Path) -> None:
        """No ``.venv`` AND ``mode=venv`` -> WARN with fixable=True."""
        ctx = DoctorContext(target=project_no_venv)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_empty_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.VENV,
            ),
        ):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        assert health.status == CheckStatus.WARN
        assert health.fixable is True

    def test_venv_mode_ok_when_venv_present(self, project_with_venv: Path) -> None:
        """Healthy ``.venv`` AND ``mode=venv`` -> OK."""
        ctx = DoctorContext(target=project_with_venv)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_empty_load_result(),
            ),
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


# ---------------------------------------------------------------------------
# T-3.3: python_env.mode=shared-parent -> probe the shared-parent venv
# ---------------------------------------------------------------------------


class TestVenvHealthSharedParent:
    """``mode=shared-parent`` -> probe the SHARED-PARENT venv path.

    The shared-parent layout anchors the venv at the main checkout
    (``$(git rev-parse --git-common-dir)/../.venv``). The doctor probe
    MUST resolve through the same anchor so worktree clones inherit the
    main venv without re-creating it.
    """

    def test_shared_parent_mode_probes_parent_venv(self, tmp_path: Path) -> None:
        """Shared-parent venv at parent dir is detected as healthy."""
        # Layout:
        #   tmp_path/main/.venv/pyvenv.cfg     (the SHARED venv)
        #   tmp_path/main/.git/...              (the git common dir)
        #   tmp_path/wt2/                        (the worktree we're inside)
        main = tmp_path / "main"
        main.mkdir()
        (main / ".git").mkdir()
        venv = main / ".venv"
        venv.mkdir()
        bindir = main / "fake_bin"
        bindir.mkdir()
        (venv / "pyvenv.cfg").write_text(
            f"home = {bindir}\nversion = 3.12.0\n",
            encoding="utf-8",
        )

        wt2 = tmp_path / "wt2"
        wt2.mkdir()

        ctx = DoctorContext(target=wt2)

        with (
            patch.object(
                tools_phase,
                "load_required_tools",
                return_value=_empty_load_result(),
            ),
            patch.object(tools_phase, "run_verify", side_effect=_verify_pass),
            patch.object(
                tools_phase,
                "load_python_env_mode",
                return_value=PythonEnvMode.SHARED_PARENT,
            ),
            # Stub the git common-dir resolution so the test does not
            # rely on real git plumbing inside the temp directory.
            patch.object(
                tools_phase,
                "_resolve_shared_parent_venv",
                return_value=venv,
                create=True,
            ),
        ):
            results = tools_phase.check(ctx)

        health = next(r for r in results if r.name == "venv-health")
        # Shared-parent venv is healthy -> OK.
        assert health.status == CheckStatus.OK
