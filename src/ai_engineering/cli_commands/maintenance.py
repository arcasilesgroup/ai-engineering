"""Maintenance CLI commands."""

from __future__ import annotations

import json

import typer

from ai_engineering.maintenance.report import create_pr_from_payload, generate_report


def register(maintenance_app: typer.Typer) -> None:
    """Register maintenance command group."""

    @maintenance_app.command("report")
    def maintenance_report(
        approve_pr: bool = typer.Option(
            False,
            "--approve-pr",
            help="If set, generate PR payload metadata after local report",
        ),
    ) -> None:
        """Generate local maintenance report and optional PR payload draft."""
        payload = generate_report(approve_pr=approve_pr)
        typer.echo(json.dumps(payload, indent=2))

    @maintenance_app.command("pr")
    def maintenance_pr() -> None:
        """Create PR from approved maintenance payload."""
        ok, message = create_pr_from_payload()
        typer.echo(message)
        if not ok:
            raise typer.Exit(code=1)
