"""Work-item sync service.

Synchronizes local specs with external issue trackers (GitHub Issues,
Azure DevOps Boards) via the VCS provider abstraction.

Functions:
    sync_spec_issues — sync all specs to external issues.
    get_linked_issue_id — retrieve linked issue number for a spec.
    get_hierarchy_rules — read work-item hierarchy rules from manifest.
    resolve_closeable_refs — split spec refs into closeable vs mention-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.state.models import TaskLifecycleState
from ai_engineering.state.work_plane import read_task_ledger, resolve_active_work_plane
from ai_engineering.vcs.factory import get_provider
from ai_engineering.vcs.protocol import IssueContext

# Default hierarchy rules: features are never auto-closed,
# user stories / tasks / bugs close on PR merge.
_DEFAULT_HIERARCHY: dict[str, str] = {
    "feature": "never_close",
    "user_story": "close_on_pr",
    "task": "close_on_pr",
    "bug": "close_on_pr",
}

# Maps spec frontmatter ref categories to hierarchy rule keys.
_REF_CATEGORY_MAP: dict[str, str] = {
    "features": "feature",
    "user_stories": "user_story",
    "tasks": "task",
    "issues": "bug",
}

_SPEC_FILENAME = "spec.md"
_DONE_FILENAME = "done.md"
_SYNC_SKIP_ENTRIES = {"_history.md", _SPEC_FILENAME, "plan.md", "archive"}


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

    specs_dir = resolve_active_work_plane(project_root).specs_dir
    if not specs_dir.is_dir():
        return report

    for spec_id, spec_dir in _iter_sync_targets(project_root, specs_dir):
        _sync_target_issue(
            report=report,
            project_root=project_root,
            spec_id=spec_id,
            spec_dir=spec_dir,
            dry_run=dry_run,
            provider=provider,
        )

    return report


def _sync_target_issue(
    *,
    report: SyncReport,
    project_root: Path,
    spec_id: str,
    spec_dir: Path,
    dry_run: bool,
    provider,
) -> None:
    """Sync a single spec directory to its external work item."""
    issue_ctx = _build_issue_context(project_root, spec_id, spec_dir / _SPEC_FILENAME)
    find_result = provider.find_issue(issue_ctx)
    if not find_result.success:
        report.errors.append(f"{spec_id}: find failed — {find_result.output}")
        return

    issue_id = find_result.output.strip()
    if issue_id:
        _handle_existing_issue(
            report=report,
            spec_id=spec_id,
            issue_ctx=issue_ctx,
            issue_id=issue_id,
            done_md=spec_dir / _DONE_FILENAME,
            dry_run=dry_run,
            provider=provider,
        )
        return

    _handle_missing_issue(
        report=report,
        spec_id=spec_id,
        issue_ctx=issue_ctx,
        dry_run=dry_run,
        provider=provider,
    )


def _build_issue_context(project_root: Path, spec_id: str, spec_md: Path) -> IssueContext:
    """Build an issue context from a spec file."""
    title, body = _parse_spec_for_issue(spec_md, spec_id)
    return IssueContext(
        project_root=project_root,
        spec_id=spec_id,
        title=title,
        body=body,
        labels=(f"spec-{spec_id}",),
    )


def _handle_existing_issue(
    *,
    report: SyncReport,
    spec_id: str,
    issue_ctx: IssueContext,
    issue_id: str,
    done_md: Path,
    dry_run: bool,
    provider,
) -> None:
    """Update report state for an already-linked issue."""
    report.found.append(spec_id)
    if not done_md.exists():
        return
    if dry_run:
        report.closed.append(spec_id)
        return

    close_result = provider.close_issue(issue_ctx, issue_id=issue_id)
    if close_result.success:
        report.closed.append(spec_id)
        return

    report.errors.append(f"{spec_id}: close failed — {close_result.output}")


def _handle_missing_issue(
    *,
    report: SyncReport,
    spec_id: str,
    issue_ctx: IssueContext,
    dry_run: bool,
    provider,
) -> None:
    """Create or preview creation for a missing issue."""
    if dry_run:
        report.created.append(spec_id)
        return

    create_result = provider.create_issue(issue_ctx)
    if create_result.success:
        report.created.append(spec_id)
        return

    report.errors.append(f"{spec_id}: create failed — {create_result.output}")


def _iter_sync_targets(project_root: Path, specs_dir: Path) -> list[tuple[str, Path]]:
    """Return syncable spec roots for legacy and spec-local work planes."""
    if _is_active_spec_dir(project_root, specs_dir):
        return [(specs_dir.name, specs_dir)]

    return [
        (entry.name, entry)
        for entry in sorted(specs_dir.iterdir())
        if entry.name not in _SYNC_SKIP_ENTRIES and entry.is_dir()
    ]


def _is_active_spec_dir(project_root: Path, specs_dir: Path) -> bool:
    """Return True when ``specs_dir`` is itself the active spec work plane."""
    spec_md = specs_dir / _SPEC_FILENAME
    if not spec_md.exists():
        return False

    try:
        text = spec_md.read_text(encoding="utf-8").lstrip()
    except OSError:
        return False

    if not text:
        return False
    if not text.startswith("# No active spec"):
        return True

    ledger = read_task_ledger(project_root)
    if ledger is None:
        return False
    return any(task.status != TaskLifecycleState.DONE for task in ledger.tasks)


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


def get_hierarchy_rules(project_root: Path) -> dict[str, str]:
    """Read work-item hierarchy rules from the project manifest.

    Looks for ``work_items.hierarchy`` in ``manifest.yml``.  Falls back
    to sensible defaults when the section is absent or malformed.

    Args:
        project_root: Root directory of the project.

    Returns:
        Dict mapping work-item type to disposition rule
        (e.g. ``{"feature": "never_close", "task": "close_on_pr"}``).
    """
    try:
        hierarchy = load_manifest_config(project_root).work_items.hierarchy
    except (OSError, ValueError):
        return dict(_DEFAULT_HIERARCHY)

    # Merge configured values over defaults.
    rules = dict(_DEFAULT_HIERARCHY)
    for key, value in hierarchy.model_dump().items():
        if isinstance(key, str) and isinstance(value, str):
            rules[key] = value
    return rules


def resolve_closeable_refs(
    project_root: Path,
    refs: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """Split spec frontmatter refs into closeable and mention-only lists.

    Uses hierarchy rules from the manifest to decide which work items
    should be closed on PR merge and which should only be mentioned.

    Args:
        project_root: Root directory of the project.
        refs: Dict from spec frontmatter (keys: features, user_stories,
              tasks, issues; values: lists of ref strings).

    Returns:
        Tuple of ``(closeable_refs, mention_only_refs)``.
    """
    rules = get_hierarchy_rules(project_root)
    closeable: list[str] = []
    mention_only: list[str] = []

    for category, items in refs.items():
        hierarchy_key = _REF_CATEGORY_MAP.get(category)
        if hierarchy_key is None:
            continue
        disposition = rules.get(hierarchy_key, "close_on_pr")
        for ref in items:
            if disposition == "never_close":
                mention_only.append(ref)
            else:
                closeable.append(ref)

    return closeable, mention_only


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

    parsed_title = _extract_issue_title(text)
    if parsed_title:
        title = f"[spec-{spec_id}] {parsed_title}"

    problem_text = _extract_problem_section(text)
    if problem_text:
        paragraphs = problem_text.split("\n\n")
        body = paragraphs[0].strip() if paragraphs else ""

    return title, body


def _extract_problem_section(text: str) -> str:
    """Extract the content under the first ``## Problem`` heading."""
    collecting = False
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("## "):
            if collecting:
                break
            collecting = stripped == "## Problem"
            continue
        if collecting:
            lines.append(line)

    return "\n".join(lines).strip()


def _extract_issue_title(text: str) -> str:
    """Extract the issue title from the first level-1 spec heading."""
    for line in text.splitlines():
        if not line.startswith("# "):
            continue
        _, separator, tail = line.partition(" — ")
        return tail.strip() if separator else ""
    return ""
