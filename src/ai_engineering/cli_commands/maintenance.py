"""Maintenance CLI commands: report, pr, branch-cleanup, risk-status, pipeline-compliance.

Framework maintenance operations including health reports, PR creation,
branch cleanup, risk governance status, and pipeline compliance scanning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.maintenance.branch_cleanup import run_branch_cleanup
from ai_engineering.maintenance.report import (
    create_maintenance_pr,
    generate_report,
)
from ai_engineering.paths import resolve_project_root
from ai_engineering.pipeline.compliance import scan_all_pipelines
from ai_engineering.pipeline.injector import suggest_injection
from ai_engineering.state.decision_logic import (
    list_expired_decisions,
    list_expiring_soon,
)
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore


def maintenance_report(
    target: Annotated[
        Path | None,
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
        Path | None,
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


def maintenance_branch_cleanup(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    base: Annotated[
        str,
        typer.Option("--base", "-b", help="Base branch for merge check."),
    ] = "main",
    force: Annotated[
        bool,
        typer.Option("--force", help="Force-delete unmerged branches."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List branches without deleting."),
    ] = False,
) -> None:
    """Clean up stale local branches (fetch, prune, delete merged)."""
    root = resolve_project_root(target)
    result = run_branch_cleanup(
        root,
        base_branch=base,
        force=force,
        dry_run=dry_run,
    )

    typer.echo(result.to_markdown())

    if not result.success:
        raise typer.Exit(code=1)


def maintenance_risk_status(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Show risk acceptance status (active, expiring, expired)."""
    root = resolve_project_root(target)
    ds_path = root / ".ai-engineering" / "state" / "decision-store.json"

    if not ds_path.exists():
        typer.echo("No decision store found.")
        return

    store = read_json_model(ds_path, DecisionStore)
    risk = store.risk_decisions()
    expired = list_expired_decisions(store)
    expiring = list_expiring_soon(store)
    active = [d for d in risk if d not in expired and d not in expiring]

    typer.echo("## Risk Acceptance Status\n")
    typer.echo(f"- **Total risk acceptances**: {len(risk)}")
    typer.echo(f"- **Active (current)**: {len(active)}")
    typer.echo(f"- **Expiring soon (<=7d)**: {len(expiring)}")
    typer.echo(f"- **Expired**: {len(expired)}")

    if expiring:
        typer.echo("\n### Expiring Soon\n")
        for d in expiring:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "?"
            typer.echo(f"- **{d.id}**: expires {exp} — {d.context[:80]}")

    if expired:
        typer.echo("\n### Expired (action required)\n")
        for d in expired:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "?"
            typer.echo(f"- **{d.id}**: expired {exp} — {d.context[:80]}")


def maintenance_pipeline_compliance(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    suggest: Annotated[
        bool,
        typer.Option("--suggest", help="Show injection snippets for non-compliant pipelines."),
    ] = False,
) -> None:
    """Scan CI/CD pipelines for risk governance compliance."""
    root = resolve_project_root(target)
    report = scan_all_pipelines(root)

    typer.echo(report.to_markdown())

    if suggest:
        for r in report.results:
            if not r.compliant:
                typer.echo(suggest_injection(r.pipeline))
