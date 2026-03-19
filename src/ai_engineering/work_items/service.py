"""Work-item sync service.

Synchronizes local specs with external issue trackers (GitHub Issues,
Azure DevOps Boards) via the VCS provider abstraction.

Functions:
    sync_spec_issues — sync all specs to external issues.
    get_linked_issue_id — retrieve linked issue number for a spec.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.vcs.factory import get_provider
from ai_engineering.vcs.protocol import IssueContext


@dataclass
class SyncReport:
    """Result of a work-item sync operation."""

    created: list[str] = field(default_factory=list)
    found: list[str] = field(default_factory=list)
    closed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def sync_spec_issues(project_root: Path, *, dry_run: bool = False) -> SyncReport:
    """Sync all specs to external work items.

    For each spec directory in ``specs/``:
    - Finds existing issue by ``spec-NNN`` label/tag.
    - Creates a new issue if none exists.
    - Closes the issue if ``done.md`` exists.

    Args:
        project_root: Root directory of the project.
        dry_run: If True, report what would happen without making changes.

    Returns:
        SyncReport with created/found/closed/errors lists.
    """
    report = SyncReport()
    provider = get_provider(project_root)

    specs_dir = project_root / ".ai-engineering" / "specs"
    if not specs_dir.is_dir():
        return report

    skip = {"_history.md", "spec.md", "plan.md"}

    for entry in sorted(specs_dir.iterdir()):
        if entry.name in skip or not entry.is_dir():
            continue

        spec_id = entry.name
        spec_md = entry / "spec.md"
        done_md = entry / "done.md"

        title, body = _parse_spec_for_issue(spec_md, spec_id)
        issue_ctx = IssueContext(
            project_root=project_root,
            spec_id=spec_id,
            title=title,
            body=body,
            labels=(f"spec-{spec_id}",),
        )

        # Find existing issue
        find_result = provider.find_issue(issue_ctx)
        if not find_result.success:
            report.errors.append(f"{spec_id}: find failed — {find_result.output}")
            continue

        issue_id = find_result.output.strip()

        if issue_id:
            report.found.append(spec_id)
            # Close if done
            if done_md.exists() and not dry_run:
                close_result = provider.close_issue(issue_ctx, issue_id=issue_id)
                if close_result.success:
                    report.closed.append(spec_id)
                else:
                    report.errors.append(f"{spec_id}: close failed — {close_result.output}")
            elif done_md.exists():
                report.closed.append(spec_id)
        else:
            # Create if not found
            if not dry_run:
                create_result = provider.create_issue(issue_ctx)
                if create_result.success:
                    report.created.append(spec_id)
                else:
                    report.errors.append(f"{spec_id}: create failed — {create_result.output}")
            else:
                report.created.append(spec_id)

    return report


def get_linked_issue_id(project_root: Path, spec_id: str) -> str | None:
    """Retrieve the linked issue number/ID for a spec.

    Args:
        project_root: Root directory of the project.
        spec_id: Spec identifier (e.g. ``"037-work-item-sync"``).

    Returns:
        Issue number/ID string, or None if not found.
    """
    provider = get_provider(project_root)
    issue_ctx = IssueContext(project_root=project_root, spec_id=spec_id)
    result = provider.find_issue(issue_ctx)
    if result.success and result.output.strip():
        return result.output.strip()
    return None


def _parse_spec_for_issue(spec_md: Path, spec_id: str) -> tuple[str, str]:
    """Extract title and body from a spec.md file.

    Args:
        spec_md: Path to the spec.md file.
        spec_id: Spec identifier for fallback title.

    Returns:
        Tuple of (title, body).
    """
    title = f"[spec-{spec_id}] {spec_id}"
    body = ""

    if not spec_md.exists():
        return title, body

    try:
        text = spec_md.read_text(encoding="utf-8")
    except OSError:
        return title, body

    # Title from "# Spec NNN — <Title>"
    title_match = re.search(r"^# [^\n]+? — (.+)$", text, re.MULTILINE)
    if title_match:
        title = f"[spec-{spec_id}] {title_match.group(1).strip()}"

    # Body from "## Problem" section
    _PROBLEM_RE = r"^## Problem[ \t]*\n(.*?)(?=(?:^## )|\Z)"
    problem_match = re.search(_PROBLEM_RE, text, re.MULTILINE | re.DOTALL)
    if problem_match:
        paragraphs = problem_match.group(1).strip().split("\n\n")
        body = paragraphs[0].strip() if paragraphs else ""

    return title, body
