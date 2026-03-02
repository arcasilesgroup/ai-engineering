"""Shared git operations for ai-engineering.

Provides reusable helpers consumed by workflows, gates, branch cleanup,
and other modules that interact with git.

Functions:
- ``current_branch`` — get the current branch name.
- ``is_branch_pushed`` — check if a branch has a remote tracking ref.
- ``get_merge_base`` — get merge-base SHA between a ref and HEAD.
- ``get_changed_files`` — list changed files relative to merge-base.
- ``run_git`` — run a git command with timeout and error handling.

Constants:
- ``PROTECTED_BRANCHES`` — branch names where direct commits are blocked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Branch names where direct commits are blocked.
PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master"})


def run_git(
    args: list[str],
    cwd: Path,
    *,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Run a git command and return (success, output).

    Args:
        args: Git subcommand and arguments (without ``git`` prefix).
        cwd: Working directory for the command.
        timeout: Maximum seconds to wait.

    Returns:
        Tuple of (passed, combined_output).
    """
    cmd = ["git", *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "git not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"git timed out after {timeout}s: {' '.join(args)}"


def _normalize_repo_path(path: str) -> str:
    """Normalize git output paths for cross-platform comparisons."""
    return path.strip().replace("\\", "/")


def get_merge_base(project_root: Path, ref: str) -> str:
    """Get merge-base SHA between ``ref`` and ``HEAD``.

    Args:
        project_root: Root directory of the git repository.
        ref: Git ref to compare against HEAD.

    Returns:
        Merge-base commit SHA.

    Raises:
        RuntimeError: If merge-base cannot be resolved.
    """
    ok, output = run_git(["merge-base", ref, "HEAD"], project_root)
    if not ok:
        raise RuntimeError(f"failed to resolve merge-base for '{ref}': {output}")

    sha = output.splitlines()[0].strip() if output else ""
    if not sha:
        raise RuntimeError(f"empty merge-base for '{ref}'")
    return sha


def get_changed_files(
    project_root: Path,
    base_ref: str,
    diff_filter: str = "ACMRT",
) -> list[str]:
    """List files changed relative to merge-base between ``base_ref`` and ``HEAD``.

    Args:
        project_root: Root directory of the git repository.
        base_ref: Ref to compare with HEAD via merge-base.
        diff_filter: Git diff-filter letters (default ``ACMRT``).

    Returns:
        Sorted, deduplicated, POSIX-normalized changed file paths.

    Raises:
        RuntimeError: If git diff fails.
    """
    merge_base = get_merge_base(project_root, base_ref)
    ok, output = run_git(
        [
            "diff",
            "--name-only",
            f"--diff-filter={diff_filter}",
            f"{merge_base}...HEAD",
        ],
        project_root,
    )
    if not ok:
        raise RuntimeError(f"failed to get changed files: {output}")

    files = [_normalize_repo_path(line) for line in output.splitlines() if line.strip()]
    return sorted(set(files))


def current_branch(project_root: Path) -> str:
    """Get the current git branch name.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        Current branch name, or ``"HEAD"`` on detached HEAD.
    """
    ok, output = run_git(
        ["rev-parse", "--abbrev-ref", "HEAD"],
        project_root,
    )
    if ok and output:
        return output.splitlines()[0].strip()
    return "HEAD"


def is_branch_pushed(project_root: Path, branch: str) -> bool:
    """Check if a branch has a remote tracking counterpart on origin.

    Args:
        project_root: Root directory of the git repository.
        branch: Branch name to check.

    Returns:
        True if ``origin/<branch>`` exists.
    """
    ok, _ = run_git(
        ["rev-parse", "--verify", f"origin/{branch}"],
        project_root,
    )
    return ok


def is_on_protected_branch(project_root: Path) -> tuple[bool, str]:
    """Check if the current branch is protected.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        Tuple of (is_protected, branch_name).
    """
    branch = current_branch(project_root)
    return branch in PROTECTED_BRANCHES, branch
