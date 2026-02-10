"""Branch cleanup for pre-implementation hygiene.

Provides automated cleanup of stale local branches before starting
new implementation work. Fetches from origin, prunes remote-tracking
refs, and deletes merged local branches.

Functions:
- ``fetch_and_prune`` — run ``git fetch --prune`` to sync remote state.
- ``list_merged_branches`` — local branches already merged into a base.
- ``delete_branches`` — safely remove a list of local branches.
- ``run_branch_cleanup`` — orchestrate the full cleanup flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.git.operations import (
    PROTECTED_BRANCHES,
    current_branch,
    run_git,
)


@dataclass
class CleanupResult:
    """Result of a branch cleanup operation."""

    fetched: bool = False
    pruned_refs: int = 0
    deleted_branches: list[str] = field(default_factory=list)
    skipped_branches: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if cleanup completed without errors."""
        return len(self.errors) == 0

    def to_markdown(self) -> str:
        """Render cleanup result as Markdown summary.

        Returns:
            Markdown-formatted cleanup summary.
        """
        lines: list[str] = []
        lines.append("## Branch Cleanup Summary")
        lines.append("")
        lines.append(f"- **Fetched**: {'yes' if self.fetched else 'no'}")
        lines.append(f"- **Pruned remote refs**: {self.pruned_refs}")
        lines.append(f"- **Deleted branches**: {len(self.deleted_branches)}")
        lines.append(f"- **Skipped branches**: {len(self.skipped_branches)}")
        lines.append("")

        if self.deleted_branches:
            lines.append("### Deleted")
            lines.append("")
            for b in sorted(self.deleted_branches):
                lines.append(f"- `{b}`")
            lines.append("")

        if self.skipped_branches:
            lines.append("### Skipped")
            lines.append("")
            for b in sorted(self.skipped_branches):
                lines.append(f"- `{b}`")
            lines.append("")

        if self.errors:
            lines.append("### Errors")
            lines.append("")
            for e in self.errors:
                lines.append(f"- {e}")
            lines.append("")

        return "\n".join(lines)


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

    pruned = sum(
        1 for line in output.splitlines()
        if "[deleted]" in line or "- [deleted]" in line
    )
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


def run_branch_cleanup(
    project_root: Path,
    *,
    base_branch: str = "main",
    force: bool = False,
    dry_run: bool = False,
) -> CleanupResult:
    """Run the full branch cleanup flow.

    Steps:
    1. Switch to base branch if not already on it.
    2. Fetch and prune remote refs.
    3. List merged branches.
    4. Delete merged branches (unless dry_run).

    Args:
        project_root: Root directory of the git repository.
        base_branch: Branch to use as merge base.
        force: Force-delete unmerged branches too.
        dry_run: If True, list branches but don't delete.

    Returns:
        CleanupResult with operation details.
    """
    result = CleanupResult()

    # Ensure we're on the base branch before cleanup
    active = current_branch(project_root)
    if active != base_branch:
        ok, output = run_git(["checkout", base_branch], project_root)
        if not ok:
            result.errors.append(f"Cannot switch to {base_branch}: {output}")
            return result

    # Pull latest on base branch
    ok, _ = run_git(["pull", "--ff-only"], project_root, timeout=60)
    if not ok:
        result.errors.append(f"Failed to pull {base_branch}")

    # Fetch and prune
    fetched, pruned = fetch_and_prune(project_root)
    result.fetched = fetched
    result.pruned_refs = pruned
    if not fetched:
        result.errors.append("git fetch --prune failed")
        return result

    # Identify candidates
    merged = list_merged_branches(project_root, base_branch)

    if dry_run:
        result.skipped_branches = merged
        return result

    # Delete
    deleted, failed = delete_branches(
        project_root,
        merged,
        force=force,
    )
    result.deleted_branches = deleted
    result.skipped_branches = failed

    return result
