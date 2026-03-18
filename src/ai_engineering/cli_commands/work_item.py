"""Work-item CLI commands: sync specs to external issue trackers."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, info, kv, success
from ai_engineering.paths import resolve_project_root


def work_item_sync(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without writing."),
    ] = False,
) -> None:
    """Sync specs to external work items (GitHub Issues / Azure DevOps Boards)."""
    root = resolve_project_root(target)

    from ai_engineering.work_items.service import sync_spec_issues

    report = sync_spec_issues(root, dry_run=dry_run)

    if report.errors and not report.created and not report.found:
        if is_json_mode():
            emit_error(
                "ai-eng work-item sync",
                f"{len(report.errors)} errors during sync",
                "SYNC_ERRORS",
                "Check provider authentication and connectivity",
            )
        else:
            error(f"{len(report.errors)} errors during sync")
            for err in report.errors:
                info(f"  {err}")
        raise typer.Exit(code=1)

    if is_json_mode():
        emit_success(
            "ai-eng work-item sync",
            {
                "dry_run": dry_run,
                "created": report.created,
                "found": report.found,
                "closed": report.closed,
                "errors": report.errors,
            },
            [
                NextAction(
                    command="ai-eng work-item sync",
                    description="Run sync (without --dry-run)",
                ),
            ]
            if dry_run
            else None,
        )
    else:
        prefix = "[dry-run] " if dry_run else ""
        if report.created:
            success(f"{prefix}Created {len(report.created)} issue(s)")
            for spec_id in report.created:
                kv("  Created", spec_id)
        if report.found:
            info(f"{prefix}Found {len(report.found)} existing issue(s)")
        if report.closed:
            success(f"{prefix}Closed {len(report.closed)} issue(s)")
            for spec_id in report.closed:
                kv("  Closed", spec_id)
        if report.errors:
            error(f"{len(report.errors)} error(s)")
            for err in report.errors:
                info(f"  {err}")
        if not report.created and not report.found and not report.closed and not report.errors:
            info(f"{prefix}No specs found to sync")
