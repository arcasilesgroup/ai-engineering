"""Branch cleanup for repository hygiene.

Provides automated cleanup of stale local branches. Fetches from origin,
prunes remote-tracking refs, deletes merged local branches, and removes
squash-merged branches whose remote tracking ref is ``[gone]``.

Functions:
- ``fetch_and_prune`` — run ``git fetch --prune`` to sync remote state.
- ``list_merged_branches`` — local branches already merged into a base.
- ``list_gone_branches`` — branches whose upstream is ``[gone]``.
- ``commits_ahead`` — count commits a branch has ahead of a base ref.
- ``delete_branches`` — safely remove a list of local branches.
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.git.operations import (
    PROTECTED_BRANCHES,
    current_branch,
    run_git,
)


def fetch_and_prune(project_root: Path) -> tuple[bool, int]:
    """Fetch from origin and prune stale remote-tracking references.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        Tuple of (success, number_of_pruned_refs).
    """
    ok, output = run_git(["fetch", "--prune"], project_root, timeout=60)
    if not ok:
        return False, 0

    pruned = sum(1 for line in output.splitlines() if "[deleted]" in line or "- [deleted]" in line)
    return True, pruned


def list_merged_branches(
    project_root: Path,
    base: str = "main",
) -> list[str]:
    """List local branches that have been merged into the base branch.

    Excludes protected branches and the current branch.

    Args:
        project_root: Root directory of the git repository.
        base: Base branch to check against.

    Returns:
        List of branch names that are merged and safe to delete.
    """
    ok, output = run_git(["branch", "--merged", base], project_root)
    if not ok:
        return []

    active = current_branch(project_root)
    branches: list[str] = []
    for line in output.splitlines():
        name = line.strip().lstrip("* ").strip()
        if not name:
            continue
        if name in PROTECTED_BRANCHES:
            continue
        if name == active:
            continue
        branches.append(name)

    return branches


def list_all_local_branches(project_root: Path) -> list[str]:
    """List all local branch names.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        List of all local branch names.
    """
    ok, output = run_git(["branch", "--format=%(refname:short)"], project_root)
    if not ok:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def list_gone_branches(project_root: Path) -> list[str]:
    """List local branches whose upstream tracking ref is ``[gone]``.

    These are branches whose remote was deleted (typically after a PR merge/squash).
    Excludes protected branches and the current branch.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        List of branch names with gone upstream.
    """
    ok, output = run_git(["branch", "-vv"], project_root)
    if not ok:
        return []

    active = current_branch(project_root)
    gone_pattern = re.compile(r"^[\s*]*(\S+)\s+\S+\s+\[[^\]]+: gone\]")
    branches: list[str] = []
    for line in output.splitlines():
        m = gone_pattern.match(line)
        if not m:
            continue
        name = m.group(1)
        if name in PROTECTED_BRANCHES or name == active:
            continue
        branches.append(name)

    return branches


def commits_ahead(project_root: Path, base_ref: str, branch: str) -> int:
    """Count commits ``branch`` has ahead of ``base_ref``.

    Args:
        project_root: Root directory of the git repository.
        base_ref: Reference to compare against (e.g. ``origin/main``).
        branch: Branch name to check.

    Returns:
        Number of commits ahead, or -1 if the comparison fails.
    """
    ok, output = run_git(
        ["rev-list", "--count", f"{base_ref}..{branch}"],
        project_root,
    )
    if not ok:
        return -1
    try:
        return int(output.strip())
    except ValueError:
        return -1


def has_unmerged_changes(project_root: Path, base_ref: str, branch: str) -> bool | None:
    """Check if ``branch`` has changes not present in ``base_ref``.

    Uses ``git diff`` to compare the branch tip against the base. This correctly
    handles squash-merged branches where commit SHAs differ but content is identical.

    Args:
        project_root: Root directory of the git repository.
        base_ref: Reference to compare against (e.g. ``origin/main``).
        branch: Branch name to check.

    Returns:
        True if the branch has unmerged changes, False if all changes are on base,
        None if the comparison fails.
    """
    ok, output = run_git(
        ["diff", "--stat", f"{base_ref}..{branch}"],
        project_root,
    )
    if not ok:
        return None
    return len(output.strip()) > 0


def delete_branches(
    project_root: Path,
    branches: list[str],
    *,
    force: bool = False,
) -> tuple[list[str], list[str]]:
    """Delete a list of local branches.

    Args:
        project_root: Root directory of the git repository.
        branches: Branch names to delete.
        force: If True, use ``-D`` (force delete); otherwise ``-d`` (safe).

    Returns:
        Tuple of (deleted_branches, failed_branches).
    """
    flag = "-D" if force else "-d"
    deleted: list[str] = []
    failed: list[str] = []

    for branch in branches:
        if branch in PROTECTED_BRANCHES:
            failed.append(branch)
            continue
        ok, _ = run_git(["branch", flag, branch], project_root)
        if ok:
            deleted.append(branch)
        else:
            failed.append(branch)

    return deleted, failed
