"""Git context extraction (branch + commit SHA).

Provides a lightweight snapshot of the current git state used by
observability dashboards, commit messages, and signal metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_engineering.git.operations import run_git

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GitContext:
    """Minimal git state snapshot."""

    branch: str
    commit_sha: str


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_cached_context: GitContext | None = None
_cache_populated: bool = False

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_git_context(project_root: Path) -> GitContext | None:
    """Return the current branch name and short commit SHA.

    Uses a module-level cache — git is queried only once per process
    lifetime.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        ``GitContext`` with branch and 8-char SHA, or ``None`` on
        failure.
    """
    global _cached_context, _cache_populated

    if _cache_populated:
        return _cached_context

    try:
        ok_branch, branch_out = run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            project_root,
        )
        if not ok_branch or not branch_out:
            _cache_populated = True
            return None

        ok_sha, sha_out = run_git(
            ["rev-parse", "--short=8", "HEAD"],
            project_root,
        )
        if not ok_sha or not sha_out:
            _cache_populated = True
            return None

        branch = branch_out.splitlines()[0].strip()
        commit_sha = sha_out.splitlines()[0].strip()

        _cached_context = GitContext(branch=branch, commit_sha=commit_sha)
        _cache_populated = True
        return _cached_context
    except Exception:
        _cache_populated = True
        return None


def _reset_cache() -> None:
    """Reset the module-level cache (used by tests)."""
    global _cached_context, _cache_populated
    _cached_context = None
    _cache_populated = False
