"""Per-mode Python environment configurator (spec-101 D-101-12, T-2.20).

Dispatches on :class:`ai_engineering.state.models.PythonEnvMode` and returns
a frozen :class:`PythonEnvConfig` describing the venv root, PATH additions,
and env vars the downstream tools / hooks phases consume.

The three modes (D-101-12):

* ``uv-tool`` (default): no project ``.venv/`` created; pytest installed via
  ``uv tool install``. The configurator returns the empty projection so hook
  generators can OMIT the legacy ``.venv/bin`` PATH prepend. Worktree
  creation never triggers a ``.venv/`` re-install -- that is the load-bearing
  property of the mode.
* ``venv``: legacy per-cwd ``.venv/``. The configurator surfaces the venv
  root + ``bin/`` directory so the hook PATH preamble keeps working as it
  does today. Actual ``uv venv .venv`` creation is delegated to a separate
  mechanism call (T-2.23+).
* ``shared-parent``: one ``.venv/`` per repository, rooted at
  ``$(git rev-parse --git-common-dir)/../.venv``. Worktrees share the same
  venv via ``UV_PROJECT_ENVIRONMENT``. Outside a git repo the configurator
  raises :class:`NonGitFallbackError` (EXIT 80) and instructs the operator
  to either ``git init`` or switch to ``mode=venv`` for non-git layouts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

from ai_engineering.state.models import PythonEnvMode

__all__ = (
    "NonGitFallbackError",
    "PythonEnvConfig",
    "_detect_git_common_dir",
    "configure_python_env",
)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class PythonEnvConfig(BaseModel):
    """Frozen projection of a :class:`PythonEnvMode` decision.

    ``venv_path`` -- root of the virtualenv consumed by ``uv run``. ``None``
    when the mode declares no project venv (``uv-tool``).
    ``path_additions`` -- absolute directories prepended to PATH by the hook
    preamble. Always a tuple to prevent post-construction mutation.
    ``env_vars`` -- env vars exported by the hook preamble before any gate
    runs. Today only ``shared-parent`` populates this (with
    ``UV_PROJECT_ENVIRONMENT``).
    """

    mode: PythonEnvMode
    venv_path: Path | None = None
    path_additions: tuple[Path, ...] = ()
    env_vars: dict[str, str] = {}

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


class NonGitFallbackError(RuntimeError):
    """Raised when ``mode=shared-parent`` is selected outside a git repo.

    Per D-101-12 the non-git fallback maps to EXIT 80 so the CLI surface
    can route uniformly. The :attr:`exit_code` class attribute carries the
    canonical mapping so callers do not parse the message.
    """

    exit_code: int = 80


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_git_common_dir(cwd: Path) -> Path | None:
    """Return ``$(git rev-parse --git-common-dir)`` or ``None`` outside git.

    Resolves the absolute path against ``cwd`` so worktrees and nested
    subdirectories all surface the same canonical ``.git`` directory of the
    main working tree. Returns ``None`` when:

    * ``git`` is not on PATH (test environment without git binary), OR
    * ``cwd`` is not inside a git repository (rev-parse exit != 0).

    Total -- never raises.
    """
    git_path = shutil.which("git")
    if git_path is None:
        return None
    try:
        completed = subprocess.run(
            [git_path, "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        # Fallback: if .git/ exists at cwd (or any ancestor), trust it.
        # Hardening for parallel test environments where git rev-parse may
        # transiently fail under concurrent index lock contention.
        for anchor in (cwd, *cwd.parents):
            if (anchor / ".git").is_dir():
                return (anchor / ".git").resolve()
        return None
    raw = (completed.stdout or "").strip()
    if not raw:
        # Same fallback for empty stdout edge case.
        for anchor in (cwd, *cwd.parents):
            if (anchor / ".git").is_dir():
                return (anchor / ".git").resolve()
        return None
    candidate = Path(raw)
    # ``git rev-parse --git-common-dir`` returns a relative path (``.git``)
    # for the main working tree; rebase it against ``cwd`` so callers get an
    # absolute Path uniformly.
    if not candidate.is_absolute():
        candidate = (cwd / candidate).resolve()
    return candidate


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------


def configure_python_env(mode: PythonEnvMode, cwd: Path) -> PythonEnvConfig:
    """Return the :class:`PythonEnvConfig` for ``mode`` rooted at ``cwd``.

    Args:
        mode: The active ``PythonEnvMode`` (read from
            ``manifest.python_env.mode`` by the caller).
        cwd: Project root used for venv path resolution. For ``uv-tool``
            this is informational; for ``venv`` it anchors the per-cwd
            ``.venv/``; for ``shared-parent`` it seeds ``git rev-parse``.

    Returns:
        A frozen :class:`PythonEnvConfig` describing the mode's projection.

    Raises:
        NonGitFallbackError: ``mode=shared-parent`` selected outside a git
            repository. Carries :attr:`exit_code = 80` per D-101-12.
    """
    if mode is PythonEnvMode.UV_TOOL:
        return _configure_uv_tool()
    if mode is PythonEnvMode.VENV:
        return _configure_venv(cwd)
    # SHARED_PARENT: only remaining enum member.
    return _configure_shared_parent(cwd)


def _configure_uv_tool() -> PythonEnvConfig:
    """Empty projection -- ``uv-tool`` does not own a project venv."""
    return PythonEnvConfig(
        mode=PythonEnvMode.UV_TOOL,
        venv_path=None,
        path_additions=(),
        env_vars={},
    )


def _configure_venv(cwd: Path) -> PythonEnvConfig:
    """Legacy per-cwd ``.venv/`` projection.

    The ``.venv`` itself is NOT created here -- the ``uv venv .venv``
    mechanism (T-2.23+) owns creation. The configurator only declares the
    shape so hook generators and the install state recorder can stay in
    sync without a side-effecting bootstrap.
    """
    venv_root = cwd / ".venv"
    return PythonEnvConfig(
        mode=PythonEnvMode.VENV,
        venv_path=venv_root,
        path_additions=(venv_root / "bin",),
        env_vars={},
    )


def _configure_shared_parent(cwd: Path) -> PythonEnvConfig:
    """Worktree-aware shared venv at ``$(git rev-parse --git-common-dir)/../.venv``.

    Raises :class:`NonGitFallbackError` outside a git repo (EXIT 80) so the
    operator gets a clear remediation pointer rather than an opaque
    "rev-parse failed" error.
    """
    common_dir = _detect_git_common_dir(cwd)
    if common_dir is None:
        raise NonGitFallbackError(
            "mode=shared-parent requires a git repository -- run `git init` "
            "in this directory first, or set `python_env.mode=venv` in "
            ".ai-engineering/manifest.yml for a non-git layout"
        )
    # Resolve the parent dir so worktrees / symlinked tmp paths all surface
    # the same canonical venv root.
    venv_root = (common_dir / ".." / ".venv").resolve()
    return PythonEnvConfig(
        mode=PythonEnvMode.SHARED_PARENT,
        venv_path=venv_root,
        path_additions=(venv_root / "bin",),
        env_vars={"UV_PROJECT_ENVIRONMENT": str(venv_root)},
    )
