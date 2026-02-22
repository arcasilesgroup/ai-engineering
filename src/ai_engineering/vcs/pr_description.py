"""Provider-agnostic PR description builder.

Generates structured PR titles and bodies from project context:
active spec, recent commits, and branch name.

Functions:
    build_pr_title — short PR title from branch and spec.
    build_pr_description — full Markdown PR body.
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.git.operations import current_branch, run_git


def build_pr_title(project_root: Path) -> str:
    """Build a PR title from the active spec and branch name.

    Format: ``spec-NNN: <branch-slug-humanized>`` when a spec is active,
    or ``<branch-slug-humanized>`` when no spec is active.

    Args:
        project_root: Root directory of the project.

    Returns:
        Single-line PR title string.
    """
    branch = current_branch(project_root)
    slug = _humanize_branch(branch)
    spec = _read_active_spec(project_root)
    if spec:
        return f"spec-{spec}: {slug}"
    return slug


def build_pr_description(project_root: Path, *, max_commits: int = 20) -> str:
    """Build a structured Markdown PR description.

    Sections:
    - **Spec**: link to active spec (if any).
    - **Changes**: list of recent commit subjects on the branch.

    Args:
        project_root: Root directory of the project.
        max_commits: Maximum number of commit subjects to include.

    Returns:
        Multi-line Markdown string suitable for PR body.
    """
    lines: list[str] = []

    # Spec section
    spec = _read_active_spec(project_root)
    if spec:
        lines.append(f"## Spec\n\n`{spec}`\n")

    # Changes section
    commits = _recent_commit_subjects(project_root, max_commits=max_commits)
    if commits:
        lines.append("## Changes\n")
        for subject in commits:
            lines.append(f"- {subject}")
        lines.append("")

    return "\n".join(lines) if lines else "No description generated."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_active_spec(project_root: Path) -> str | None:
    """Read the active spec identifier from ``_active.md``.

    Parses the YAML frontmatter ``active:`` field.

    Args:
        project_root: Root directory of the project.

    Returns:
        Active spec identifier (e.g. ``"014-dual-vcs-provider"``),
        or None if no spec is active or file is missing.
    """
    active_path = project_root / ".ai-engineering" / "context" / "specs" / "_active.md"
    if not active_path.exists():
        return None

    try:
        text = active_path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = re.search(r'^active:\s*"(.+?)"', text, re.MULTILINE)
    if match:
        value = match.group(1).strip()
        if value.lower() == "none":
            return None
        return value
    return None


def _recent_commit_subjects(
    project_root: Path,
    *,
    max_commits: int = 20,
) -> list[str]:
    """Get recent commit subjects on the current branch vs origin/main.

    Falls back to the last ``max_commits`` commits if origin/main
    is not reachable.

    Args:
        project_root: Root directory of the project.
        max_commits: Maximum number of subjects to return.

    Returns:
        List of commit subject strings (newest first).
    """
    # Try branch diff against origin/main
    ok, output = run_git(
        ["log", "origin/main..HEAD", "--format=%s", f"-{max_commits}"],
        project_root,
    )
    if ok and output.strip():
        return [line.strip() for line in output.strip().splitlines() if line.strip()]

    # Fallback: last N commits
    ok, output = run_git(
        ["log", "--format=%s", f"-{max_commits}"],
        project_root,
    )
    if ok and output.strip():
        return [line.strip() for line in output.strip().splitlines() if line.strip()]

    return []


def _humanize_branch(branch: str) -> str:
    """Convert a branch name to a human-readable title.

    Strips common prefixes (``feat/``, ``fix/``, ``chore/``) and replaces
    hyphens/underscores with spaces, capitalizing the first word.

    Args:
        branch: Git branch name.

    Returns:
        Human-readable title string.
    """
    # Strip common prefixes
    for prefix in ("feat/", "fix/", "chore/", "refactor/", "docs/", "spec/"):
        if branch.startswith(prefix):
            branch = branch[len(prefix) :]
            break

    # Replace separators with spaces
    title = branch.replace("-", " ").replace("_", " ").strip()
    if title:
        title = title[0].upper() + title[1:]
    return title
