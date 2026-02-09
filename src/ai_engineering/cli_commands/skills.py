"""Remote skills CLI commands."""

from __future__ import annotations

import json

import typer

from ai_engineering.paths import repo_root
from ai_engineering.skills.service import export_sync_report_json, list_sources, sync_sources


def register(skill_app: typer.Typer) -> None:
    """Register skill command group."""

    @skill_app.command("list")
    def skill_list(
        json_output: bool = typer.Option(False, "--json", help="Print JSON output"),
    ) -> None:
        """List configured skill sources from lock file."""
        payload = list_sources()
        if json_output:
            typer.echo(json.dumps(payload, indent=2))
            return
        sources = payload.get("sources", [])
        if not isinstance(sources, list):
            raise typer.Exit(code=1)
        typer.echo(f"skill sources: {len(sources)}")
        for item in sources:
            if isinstance(item, dict):
                url = item.get("url")
                checksum = item.get("checksum")
                typer.echo(f"- {url} (checksum: {checksum})")

    @skill_app.command("sync")
    def skill_sync(
        offline: bool = typer.Option(
            False, "--offline", help="Use cache only and skip remote fetch"
        ),
    ) -> None:
        """Sync skill sources and refresh lock metadata."""
        result = sync_sources(offline=offline)
        report_path = repo_root() / ".ai-engineering" / "state" / "skills_sync_report.json"
        export_sync_report_json(report_path, result)
        typer.echo(json.dumps(result, indent=2))
        summary = result.get("summary", {})
        if isinstance(summary, dict) and int(summary.get("failed", 0)) > 0:
            raise typer.Exit(code=1)
