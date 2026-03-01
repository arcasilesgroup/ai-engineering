"""Repository status analysis for branch health and PR visibility.

Provides remote branch analysis, ahead/behind tracking, open PR listing,
and stale branch detection. Consumed by the cleanup workflow and
maintenance report.

Functions:
- ``list_remote_branches`` — enumerate remote branches with metadata.
- ``get_ahead_behind`` — commit delta between two refs.
- ``list_open_prs`` — open PRs via ``gh`` CLI (graceful fallback).
- ``detect_stale_branches`` — branches with no recent commits.
- ``run_repo_status`` — orchestrate full repository status snapshot.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_engineering.git.operations import PROTECTED_BRANCHES, current_branch, run_git


@dataclass
class BranchStatus:
    """Status of a single branch relative to the default branch."""

    name: str
    ahead: int = 0
    behind: int = 0
    is_remote: bool = False
    last_commit_date: str = ""
    tracking: str | None = None


@dataclass
class PullRequestInfo:
    """Minimal metadata for an open pull request."""

    number: int
    title: str
    branch: str
    target: str
    author: str


@dataclass
class RepoStatusResult:
    """Aggregated repository health snapshot."""

    default_branch: str = "main"
    remote_branches: list[BranchStatus] = field(default_factory=list)
    local_branches: list[BranchStatus] = field(default_factory=list)
    open_prs: list[PullRequestInfo] = field(default_factory=list)
    stale_branches: list[BranchStatus] = field(default_factory=list)
    cleanup_candidates: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize the repo status as a plain dictionary for JSON output."""
        return {
            "default_branch": self.default_branch,
            "remote_branches": [
                {
                    "name": b.name,
                    "ahead": b.ahead,
                    "behind": b.behind,
                    "last_commit_date": b.last_commit_date,
                }
                for b in self.remote_branches
            ],
            "local_branches": [
                {
                    "name": b.name,
                    "ahead": b.ahead,
                    "behind": b.behind,
                    "last_commit_date": b.last_commit_date,
                    "tracking": b.tracking,
                }
                for b in self.local_branches
            ],
            "open_prs": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "branch": pr.branch,
                    "target": pr.target,
                    "author": pr.author,
                }
                for pr in self.open_prs
            ],
            "stale_branches": [
                {"name": b.name, "is_remote": b.is_remote, "last_commit_date": b.last_commit_date}
                for b in self.stale_branches
            ],
            "cleanup_candidates": self.cleanup_candidates,
            "errors": self.errors,
        }

    def to_markdown(self) -> str:
        """Render the status snapshot as Markdown.

        Returns:
            Markdown-formatted status report.
        """
        lines: list[str] = []
        lines.append("## Repository Status")
        lines.append("")
        lines.append(f"- **Default branch**: `{self.default_branch}`")
        lines.append(f"- **Remote branches**: {len(self.remote_branches)}")
        lines.append(f"- **Local branches**: {len(self.local_branches)}")
        lines.append(f"- **Open PRs**: {len(self.open_prs)}")
        lines.append(f"- **Stale branches (>30d)**: {len(self.stale_branches)}")
        lines.append(f"- **Cleanup candidates**: {len(self.cleanup_candidates)}")
        lines.append("")

        if self.open_prs:
            lines.append("### Open Pull Requests")
            lines.append("")
            lines.append("| # | Title | Branch | Target | Author |")
            lines.append("|---|-------|--------|--------|--------|")
            for pr in self.open_prs:
                lines.append(
                    f"| {pr.number} | {pr.title} | `{pr.branch}` | `{pr.target}` | {pr.author} |"
                )
            lines.append("")

        if self.stale_branches:
            lines.append("### Stale Branches")
            lines.append("")
            for b in self.stale_branches:
                loc = "remote" if b.is_remote else "local"
                lines.append(f"- `{b.name}` ({loc}, last commit: {b.last_commit_date})")
            lines.append("")

        if self.cleanup_candidates:
            lines.append("### Cleanup Candidates")
            lines.append("")
            for name in self.cleanup_candidates:
                lines.append(f"- `{name}`")
            lines.append("")

        if self.errors:
            lines.append("### Errors")
            lines.append("")
            for e in self.errors:
                lines.append(f"- {e}")
            lines.append("")

        return "\n".join(lines)


# Threshold for considering a branch stale (days).
_STALE_THRESHOLD_DAYS: int = 30


def get_ahead_behind(
    project_root: Path,
    branch: str,
    base: str,
) -> tuple[int, int]:
    """Count commits ahead and behind between *branch* and *base*.

    Args:
        project_root: Root directory of the git repository.
        branch: Branch to measure.
        base: Base branch to compare against.

    Returns:
        Tuple of (ahead, behind).
    """
    ok, output = run_git(
        ["rev-list", "--left-right", "--count", f"{base}...{branch}"],
        project_root,
    )
    if not ok or not output.strip():
        return 0, 0

    parts = output.strip().split()
    if len(parts) != 2:
        return 0, 0

    try:
        behind = int(parts[0])
        ahead = int(parts[1])
    except ValueError:
        return 0, 0

    return ahead, behind


def list_remote_branches(
    project_root: Path,
    base: str = "main",
) -> list[BranchStatus]:
    """List remote branches with ahead/behind relative to *base*.

    Args:
        project_root: Root directory of the git repository.
        base: Default branch to compare against.

    Returns:
        List of BranchStatus for remote branches.
    """
    ok, output = run_git(
        [
            "branch",
            "-r",
            "--format=%(refname:short)\t%(committerdate:iso-strict)",
        ],
        project_root,
    )
    if not ok:
        return []

    branches: list[BranchStatus] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "->" in line:
            continue

        parts = line.split("\t", 1)
        name = parts[0].strip()
        date_str = parts[1].strip() if len(parts) > 1 else ""

        # Skip the base branch remote ref
        short_name = name.removeprefix("origin/")
        if short_name in PROTECTED_BRANCHES:
            continue

        ahead, behind = get_ahead_behind(project_root, name, base)

        branches.append(
            BranchStatus(
                name=short_name,
                ahead=ahead,
                behind=behind,
                is_remote=True,
                last_commit_date=date_str[:10] if date_str else "",
                tracking=name,
            )
        )

    return branches


def list_local_branches_with_status(
    project_root: Path,
    base: str = "main",
) -> list[BranchStatus]:
    """List local branches with ahead/behind and tracking info.

    Args:
        project_root: Root directory of the git repository.
        base: Default branch to compare against.

    Returns:
        List of BranchStatus for local branches.
    """
    ok, output = run_git(
        [
            "branch",
            "--format=%(refname:short)\t%(upstream:short)\t%(committerdate:iso-strict)",
        ],
        project_root,
    )
    if not ok:
        return []

    active = current_branch(project_root)
    branches: list[BranchStatus] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t")
        name = parts[0].strip()
        tracking = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        date_str = parts[2].strip() if len(parts) > 2 else ""

        if name in PROTECTED_BRANCHES or name == active:
            continue

        ahead, behind = get_ahead_behind(project_root, name, base)

        branches.append(
            BranchStatus(
                name=name,
                ahead=ahead,
                behind=behind,
                is_remote=False,
                last_commit_date=date_str[:10] if date_str else "",
                tracking=tracking if tracking else None,
            )
        )

    return branches


def list_open_prs(project_root: Path) -> list[PullRequestInfo]:
    """List open pull requests via ``gh pr list``.

    Falls back gracefully if ``gh`` is not available.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        List of PullRequestInfo for open PRs.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--json",
                "number,title,headRefName,baseRefName,author",
                "--limit",
                "50",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        prs: list[PullRequestInfo] = []
        for item in data:
            author = item.get("author", {})
            author_login = author.get("login", "") if isinstance(author, dict) else str(author)
            prs.append(
                PullRequestInfo(
                    number=item.get("number", 0),
                    title=item.get("title", ""),
                    branch=item.get("headRefName", ""),
                    target=item.get("baseRefName", ""),
                    author=author_login,
                )
            )
        return prs

    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def detect_stale_branches(
    branches: list[BranchStatus],
    threshold_days: int = _STALE_THRESHOLD_DAYS,
) -> list[BranchStatus]:
    """Filter branches that have had no commits within *threshold_days*.

    Args:
        branches: List of branches to filter.
        threshold_days: Days of inactivity to be considered stale.

    Returns:
        Branches whose last commit is older than the threshold.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=threshold_days)
    stale: list[BranchStatus] = []

    for b in branches:
        if not b.last_commit_date:
            continue
        try:
            commit_date = datetime.fromisoformat(b.last_commit_date).replace(tzinfo=UTC)
        except ValueError:
            try:
                commit_date = datetime.strptime(b.last_commit_date, "%Y-%m-%d").replace(
                    tzinfo=UTC,
                )
            except ValueError:
                continue

        if commit_date < cutoff:
            stale.append(b)

    return stale


def run_repo_status(
    project_root: Path,
    base_branch: str = "main",
    *,
    include_prs: bool = True,
) -> RepoStatusResult:
    """Orchestrate a full repository status snapshot.

    Collects remote branches, local branches, open PRs, stale branches,
    and cleanup candidates.

    Args:
        project_root: Root directory of the git repository.
        base_branch: Default branch for comparisons.
        include_prs: Whether to query open PRs via ``gh``.

    Returns:
        RepoStatusResult with full health snapshot.
    """
    result = RepoStatusResult(default_branch=base_branch)

    # Remote branches
    result.remote_branches = list_remote_branches(project_root, base_branch)

    # Local branches
    result.local_branches = list_local_branches_with_status(project_root, base_branch)

    # Open PRs
    if include_prs:
        result.open_prs = list_open_prs(project_root)

    # Stale detection across all branches
    all_branches = result.remote_branches + result.local_branches
    result.stale_branches = detect_stale_branches(all_branches)

    # Cleanup candidates: merged (ahead=0) or stale
    stale_names = {b.name for b in result.stale_branches}
    for b in result.local_branches:
        is_candidate = (b.ahead == 0 and b.behind >= 0) or b.name in stale_names
        if is_candidate and b.name not in result.cleanup_candidates:
            result.cleanup_candidates.append(b.name)

    return result
