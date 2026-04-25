"""RED tests for spec-101 T-2.19/T-2.20: ``installer.python_env`` configurator.

Drives the design of the per-mode environment configurator. Per D-101-12, the
installer must dispatch on ``PythonEnvMode`` to produce a typed config that
captures everything the downstream phases (tools install, hook generation)
need to know about the active Python environment:

* ``uv-tool`` (default): no project ``.venv/`` is created. Pytest runs via
  ``uv tool install``. ``configure_python_env`` returns a config with
  ``venv_path=None``, no PATH additions, no env vars. Worktree creation never
  triggers a ``.venv/`` re-install (that's the whole point of the mode).
* ``venv``: legacy-style per-cwd ``.venv/``. The configurator returns the
  expected venv root and the platform-aware bin/Scripts directory in
  ``path_additions``. The ``.venv`` itself is created later by an explicit
  ``uv venv .venv`` mechanism call (T-2.23+); this configurator only declares
  the shape.
* ``shared-parent``: one ``.venv/`` per repository, rooted at
  ``$(git rev-parse --git-common-dir)/../.venv``. Worktrees share that one
  venv via the ``UV_PROJECT_ENVIRONMENT`` env var. Outside a git repo the
  configurator raises ``NonGitFallbackError`` -- the operator must
  ``git init`` first, or switch to ``mode=venv`` for a non-git layout.

These tests intentionally fail (RED phase) -- ``installer/python_env.py`` is
introduced by T-2.20.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ai_engineering.installer.python_env import (
    NonGitFallbackError,
    PythonEnvConfig,
    _detect_git_common_dir,
    configure_python_env,
)
from ai_engineering.state.models import PythonEnvMode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_init(root: Path) -> None:
    """Initialise a bare-bones git repo at ``root`` for shared-parent tests."""
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=root,
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# PythonEnvConfig shape -- frozen Pydantic model
# ---------------------------------------------------------------------------


class TestPythonEnvConfigShape:
    """``PythonEnvConfig`` carries mode + venv + PATH + env-var projections."""

    def test_is_frozen(self) -> None:
        config = PythonEnvConfig(
            mode=PythonEnvMode.UV_TOOL,
            venv_path=None,
            path_additions=(),
            env_vars={},
        )
        with pytest.raises((TypeError, ValueError)):
            config.mode = PythonEnvMode.VENV  # type: ignore[misc]

    def test_carries_mode(self) -> None:
        config = PythonEnvConfig(
            mode=PythonEnvMode.VENV,
            venv_path=Path("/tmp/.venv"),
            path_additions=(Path("/tmp/.venv/bin"),),
            env_vars={},
        )
        assert config.mode is PythonEnvMode.VENV

    def test_path_additions_is_tuple(self) -> None:
        # Tuple guarantees the additions cannot be mutated post-construction.
        config = PythonEnvConfig(
            mode=PythonEnvMode.UV_TOOL,
            venv_path=None,
            path_additions=(),
            env_vars={},
        )
        assert isinstance(config.path_additions, tuple)


# ---------------------------------------------------------------------------
# Mode dispatch -- uv-tool (default)
# ---------------------------------------------------------------------------


class TestConfigureUvToolMode:
    """``mode=uv-tool`` returns the empty-projection config (no venv)."""

    def test_returns_no_venv_path(self, tmp_path: Path) -> None:
        config = configure_python_env(PythonEnvMode.UV_TOOL, tmp_path)
        assert config.venv_path is None

    def test_returns_no_path_additions(self, tmp_path: Path) -> None:
        config = configure_python_env(PythonEnvMode.UV_TOOL, tmp_path)
        assert config.path_additions == ()

    def test_returns_no_env_vars(self, tmp_path: Path) -> None:
        config = configure_python_env(PythonEnvMode.UV_TOOL, tmp_path)
        assert config.env_vars == {}

    def test_does_not_create_venv_directory(self, tmp_path: Path) -> None:
        configure_python_env(PythonEnvMode.UV_TOOL, tmp_path)
        # The configurator MUST NOT create a project .venv -- that defeats the
        # whole purpose of uv-tool mode (worktree creation triggering re-install).
        assert not (tmp_path / ".venv").exists()


# ---------------------------------------------------------------------------
# Mode dispatch -- venv (legacy)
# ---------------------------------------------------------------------------


class TestConfigureVenvMode:
    """``mode=venv`` returns the legacy per-cwd ``.venv/`` projection."""

    def test_returns_cwd_venv_path(self, tmp_path: Path) -> None:
        config = configure_python_env(PythonEnvMode.VENV, tmp_path)
        assert config.venv_path == tmp_path / ".venv"

    def test_returns_bin_in_path_additions(self, tmp_path: Path) -> None:
        config = configure_python_env(PythonEnvMode.VENV, tmp_path)
        # The hook generator's PATH preamble injects this directory; the
        # configurator surfaces it canonically. POSIX path is the contract --
        # the hook script handles Scripts/ vs bin/ separately.
        assert tmp_path / ".venv" / "bin" in config.path_additions

    def test_returns_no_env_vars(self, tmp_path: Path) -> None:
        # venv mode does NOT export UV_PROJECT_ENVIRONMENT (that's
        # shared-parent's contract). Hook PATH prepend is enough.
        config = configure_python_env(PythonEnvMode.VENV, tmp_path)
        assert config.env_vars == {}

    def test_does_not_create_venv_directory_itself(self, tmp_path: Path) -> None:
        # The configurator only declares the shape -- ``uv venv .venv``
        # creation is delegated to a separate mechanism (T-2.23+).
        configure_python_env(PythonEnvMode.VENV, tmp_path)
        assert not (tmp_path / ".venv").exists()


# ---------------------------------------------------------------------------
# Mode dispatch -- shared-parent (worktree-aware)
# ---------------------------------------------------------------------------


class TestConfigureSharedParentMode:
    """``mode=shared-parent`` requires a git repo and projects parent venv."""

    def test_returns_git_common_dir_parent_venv(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        config = configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)

        # ``git rev-parse --git-common-dir`` returns ``.git`` for the main
        # working tree; the venv lands at ``.git/../.venv`` => ``<root>/.venv``.
        # We compare via ``resolve()`` so symlinked tmp paths (macOS) match.
        expected = (tmp_path / ".venv").resolve()
        assert config.venv_path is not None
        assert config.venv_path.resolve() == expected

    def test_returns_uv_project_environment_env_var(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        config = configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)

        # The hook preamble exports this var so ``uv run`` resolves the same
        # venv from every worktree -- that's the load-bearing contract.
        assert "UV_PROJECT_ENVIRONMENT" in config.env_vars
        env_value = config.env_vars["UV_PROJECT_ENVIRONMENT"]
        assert env_value == str(config.venv_path)

    def test_returns_bin_in_path_additions(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        config = configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)
        assert config.venv_path is not None
        assert config.venv_path / "bin" in config.path_additions


# ---------------------------------------------------------------------------
# Non-git fallback -- shared-parent without a git repo (D-101-12 EXIT 80)
# ---------------------------------------------------------------------------


class TestSharedParentNonGitFallback:
    """Outside a git repo, ``mode=shared-parent`` raises ``NonGitFallbackError``."""

    def test_raises_outside_git_repo(self, tmp_path: Path) -> None:
        # No ``git init`` -- the directory has no ``.git/``.
        with pytest.raises(NonGitFallbackError):
            configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)

    def test_error_message_mentions_git_init_remediation(self, tmp_path: Path) -> None:
        with pytest.raises(NonGitFallbackError) as excinfo:
            configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)
        message = str(excinfo.value)
        assert "git init" in message

    def test_error_message_suggests_venv_mode(self, tmp_path: Path) -> None:
        with pytest.raises(NonGitFallbackError) as excinfo:
            configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)
        message = str(excinfo.value)
        # Operator must know they can switch to ``mode=venv`` for non-git
        # layouts -- the error is part of the user surface, not just plumbing.
        assert "mode=venv" in message

    def test_error_carries_exit_80_reference(self, tmp_path: Path) -> None:
        # D-101-12 maps the non-git fallback to EXIT 80 (tools-failed surface).
        with pytest.raises(NonGitFallbackError) as excinfo:
            configure_python_env(PythonEnvMode.SHARED_PARENT, tmp_path)
        # The class attribute carries the canonical exit code reference so
        # the CLI surface can route uniformly without string parsing.
        assert NonGitFallbackError.exit_code == 80
        # And the message names the requirement for operator clarity.
        assert "shared-parent" in str(excinfo.value)


# ---------------------------------------------------------------------------
# _detect_git_common_dir helper
# ---------------------------------------------------------------------------


class TestDetectGitCommonDir:
    """``_detect_git_common_dir`` returns absolute Path or None outside git."""

    def test_returns_path_inside_git_repo(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        result = _detect_git_common_dir(tmp_path)
        assert result is not None
        # Resolve both sides because tmp_path on macOS is a symlink under
        # ``/private/var`` while git rev-parse returns the resolved form.
        assert result.resolve() == (tmp_path / ".git").resolve()

    def test_returns_none_outside_git_repo(self, tmp_path: Path) -> None:
        # No ``git init`` -- helper returns None rather than raising.
        assert _detect_git_common_dir(tmp_path) is None

    def test_returns_path_from_subdirectory(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        nested = tmp_path / "deep" / "nested"
        nested.mkdir(parents=True)
        result = _detect_git_common_dir(nested)
        assert result is not None
        # The common dir is still rooted at the repo top, not the subdir.
        assert result.resolve() == (tmp_path / ".git").resolve()

    def test_does_not_raise_on_missing_git_binary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Empty PATH means ``git`` is unavailable -- helper must return None,
        # never raise (tests run in environments where git might be absent).
        monkeypatch.setenv("PATH", "")
        # Set HOME so subprocess invocation has a sane env even with empty PATH.
        monkeypatch.setenv("HOME", str(tmp_path))
        # Some test runners require these vars; preserve them.
        for var in ("LANG", "LC_ALL", "TERM"):
            monkeypatch.delenv(var, raising=False)
            os.environ.pop(var, None)
        # Helper must absorb the missing-git case gracefully.
        assert _detect_git_common_dir(tmp_path) is None
