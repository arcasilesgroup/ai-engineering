"""Issue CLI commands: sync specs to external issue trackers.

Renamed from ``work-item`` per spec-132 D-132-03. Subcommand surface
(``sync``) preserved under the new top-level name. The Python module
``ai_engineering.issues`` provides the underlying sync service.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import NextAction, Renderer
from ai_engineering.paths import resolve_project_root


def issue_sync(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without writing."),
    ] = False,
) -> None:
    """Sync specs to external issues (GitHub Issues / Azure DevOps Boards)."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("issue sync")

    from ai_engineering.issues.service import sync_spec_issues

    renderer.header()
    prefix = "[dry-run] " if dry_run else ""
    renderer.action(
        "Updating",
        "external issues",
        detail="dry-run" if dry_run else None,
    )

    report = sync_spec_issues(root, dry_run=dry_run)

    if report.errors and not report.created and not report.found:
        for err in report.errors:
            renderer.step(f"  {err}")
        renderer.error(
            f"{len(report.errors)} errors during sync",
            code="SYNC_ERRORS",
            fix="Check provider authentication and connectivity.",
        )

    for spec_id in report.created:
        renderer.record("created", f"issue:{spec_id}")
    for spec_id in report.found:
        renderer.record("skipped", f"issue:{spec_id}", from_="already exists")
    for spec_id in report.closed:
        renderer.record("removed", f"issue:{spec_id}", from_="closed")
    for err in report.errors:
        renderer.step(f"  WARN: {err}")

    next_actions: list[NextAction] = []
    if dry_run:
        next_actions.append(
            NextAction(label="Run sync (without --dry-run)", command="ai-eng issue sync"),
        )

    summary_parts: list[str] = []
    if report.created:
        summary_parts.append(f"{len(report.created)} created")
    if report.found:
        summary_parts.append(f"{len(report.found)} existing")
    if report.closed:
        summary_parts.append(f"{len(report.closed)} closed")
    if report.errors:
        summary_parts.append(f"{len(report.errors)} errors")
    if not summary_parts:
        summary_parts.append("no specs to sync")

    if next_actions:
        renderer.next(next_actions)
    renderer.ok(
        f"{prefix}{'; '.join(summary_parts)}",
        result={
            "dry_run": dry_run,
            "created": report.created,
            "found": report.found,
            "closed": report.closed,
            "errors": report.errors,
        },
    )
