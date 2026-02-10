"""Maintenance CLI commands: report, pr.

Framework maintenance operations including health reports and PR creation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from ai_engineering.maintenance.report import (
    create_maintenance_pr,
    generate_report,
)
from ai_engineering.paths import resolve_project_root


def maintenance_report(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    staleness_days: Annotated[
        int,
        typer.Option("--staleness-days", help="Days before a file is stale."),
    ] = 90,
) -> None:
    """Generate a framework maintenance report."""
    root = resolve_project_root(target)
    report = generate_report(root, staleness_days=staleness_days)

    typer.echo(report.to_markdown())


def maintenance_pr(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    branch: Annotated[
        str,
        typer.Option("--branch", "-b", help="Branch name for the PR."),
    ] = "maintenance/framework-update",
) -> None:
    """Generate a maintenance report and create a PR."""
    root = resolve_project_root(target)
    report = generate_report(root)
    success = create_maintenance_pr(root, report, branch_name=branch)

    if success:
        typer.echo("Maintenance PR created successfully.")
    else:
        typer.echo("Failed to create maintenance PR.", err=True)
        raise typer.Exit(code=1)
