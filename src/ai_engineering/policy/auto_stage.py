"""Auto-stage utility (spec-105 D-105-09).

Provides a strict-safe re-stage primitive shared by:

* The orchestrator Wave 1 (``policy/orchestrator.run_wave1``) -- after the
  ruff format / ruff check --fix / spec verify --fix passes have rewritten
  files on disk.
* The Claude Code auto-format hook
  (``.ai-engineering/scripts/hooks/auto-format.py``) -- after
  ``Edit``/``Write``/``MultiEdit`` tool calls have rewritten files on disk.

Safety invariant (D-105-09): only files that were ALREADY in the staged set
``S_pre`` AND have been modified between ``S_pre`` capture and now (``M_post``)
are re-staged. The intersection is set-strict; never a superset:

    restaged = S_pre & M_post

This rules out two failure modes:

* Files newly created by fixers (e.g. a stray ``__pycache__/foo.pyc``) being
  staged behind the user's back.
* Files that the user explicitly left unstaged but also touched -- they stay
  unstaged and surface as ``unstaged_modifications`` so the CLI can warn.

All functions are pure with respect to the filesystem outside the ``git``
calls themselves; failures (no git, missing index, dirty .git/) degrade
gracefully to empty sets so the orchestrator never blows up on unrelated
infrastructure errors.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_GIT_TIMEOUT_SECONDS: int = 10


# --- Result container -------------------------------------------------------


@dataclass(frozen=True)
class AutoStageResult:
    """Result of one ``restage_intersection`` invocation.

    Attributes:
        restaged: Sorted file paths (POSIX, relative to repo root) that were
            re-added to the index because they appeared in BOTH ``S_pre`` and
            ``M_post``.
        unstaged_modifications: Sorted file paths that were modified after
            ``S_pre`` capture but were NOT in ``S_pre`` -- they remain
            unstaged. Surfaced so callers can warn the operator.
    """

    restaged: list[str] = field(default_factory=list)
    unstaged_modifications: list[str] = field(default_factory=list)


# --- Git helpers ------------------------------------------------------------


def _run_git_name_only(repo_root: Path, *args: str) -> set[str]:
    """Run ``git <args>`` returning the null-byte-split path set.

    All callers pass ``-z`` so we split on NUL bytes; trailing NUL is ignored.
    Failures (no git, not a repo, missing index, etc.) yield an empty set --
    callers MUST handle the empty-set case as "no information available" and
    fall back to a no-op rather than treating it as a destructive truth.
    """
    cmd = ["git", "-C", str(repo_root), *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.debug("git command failed: %s", " ".join(cmd), exc_info=True)
        return set()
    if result.returncode != 0:
        logger.debug("git command non-zero exit %d: %s", result.returncode, " ".join(cmd))
        return set()
    raw = result.stdout or b""
    paths: set[str] = set()
    for chunk in raw.split(b"\x00"):
        if not chunk:
            continue
        try:
            paths.add(chunk.decode("utf-8"))
        except UnicodeDecodeError:
            # Git surrogate-escape fallback for non-UTF-8 paths -- still
            # safe to include because we only pass the string straight back
            # into ``git add``.
            paths.add(chunk.decode("utf-8", errors="surrogateescape"))
    return paths


def capture_staged_set(repo_root: Path) -> set[str]:
    """Return the current staged-file path set.

    Wraps ``git diff --cached --name-only -z``. Returned paths are relative
    to ``repo_root`` and use forward slashes (git's canonical form).
    """
    return _run_git_name_only(repo_root, "diff", "--cached", "--name-only", "-z")


def capture_modified_set(repo_root: Path) -> set[str]:
    """Return the working-tree-vs-index modified path set.

    Wraps ``git diff --name-only -z``. This is the set of files whose worktree
    contents have diverged from the index since the last add -- i.e. files
    rewritten by Wave 1 fixers or by the Claude Code edit hook.
    """
    return _run_git_name_only(repo_root, "diff", "--name-only", "-z")


# --- Public re-stage primitive ----------------------------------------------


def restage_intersection(
    repo_root: Path,
    s_pre: set[str],
    *,
    log_warning_for_unstaged: bool = True,
) -> AutoStageResult:
    """Re-stage exactly ``s_pre & m_post`` -- never a superset.

    The function captures ``M_post`` itself (one ``git diff --name-only -z``
    call) so callers only need to remember to capture ``S_pre`` BEFORE the
    fixers run. The intersection is then the safe re-stage set.

    When ``log_warning_for_unstaged`` is True (the default), files that
    appear in ``M_post`` but not in ``S_pre`` are returned as
    ``unstaged_modifications`` so the CLI can surface a warning. They are
    NEVER staged automatically -- D-105-09 strict safety.

    Args:
        repo_root: Absolute path to the git repository root.
        s_pre: The staged-file set BEFORE Wave 1 fixers ran. Must be supplied
            by the caller via :func:`capture_staged_set` (or equivalent).
        log_warning_for_unstaged: When True (default) include
            ``M_post - S_pre`` in ``unstaged_modifications`` so the CLI can
            warn the operator. When False, suppress the surfacing entirely.

    Returns:
        An :class:`AutoStageResult` describing what was actually re-staged
        and which modifications were left unstaged.
    """
    m_post = capture_modified_set(repo_root)
    intersection = sorted(s_pre & m_post)
    leftover = sorted(m_post - s_pre) if log_warning_for_unstaged else []

    if intersection:
        cmd = ["git", "-C", str(repo_root), "add", "--", *intersection]
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                timeout=_GIT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.debug("git add failed for intersection set", exc_info=True)
            # Even when the add itself fails we still report what we
            # ATTEMPTED to stage so the caller can surface the failure --
            # silently swallowing it would mask drift.

    return AutoStageResult(
        restaged=intersection,
        unstaged_modifications=leftover,
    )
