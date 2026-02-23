"""Skills CLI commands: list, sync, add, remove.

Manages remote skill sources and synchronisation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.paths import resolve_project_root
from ai_engineering.skills.service import (
    add_source,
    list_local_skill_status,
    list_sources,
    remove_source,
    sync_sources,
)


def skill_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List configured remote skill sources."""
    root = resolve_project_root(target)
    sources = list_sources(root)

    if not sources:
        typer.echo("No remote skill sources configured.")
        return

    for src in sources:
        trust = "trusted" if src.trusted else "untrusted"
        typer.echo(f"  - {src.url} [{trust}]")


def skill_sync(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    offline: Annotated[
        bool,
        typer.Option("--offline", help="Only use cached content."),
    ] = False,
) -> None:
    """Synchronise remote skill sources."""
    root = resolve_project_root(target)
    result = sync_sources(root, offline=offline)

    typer.echo(f"Fetched: {len(result.fetched)}")
    typer.echo(f"Cached:  {len(result.cached)}")

    if result.failed:
        typer.echo(f"Failed:  {len(result.failed)}")
        for url in result.failed:
            typer.echo(f"  ✗ {url}")

    if result.untrusted:
        typer.echo(f"Untrusted (skipped): {len(result.untrusted)}")


def skill_add(
    url: Annotated[str, typer.Argument(help="URL of the remote skill source.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    trusted: Annotated[
        bool,
        typer.Option("--trusted/--untrusted", help="Trust status."),
    ] = True,
) -> None:
    """Add a remote skill source."""
    root = resolve_project_root(target)
    try:
        add_source(root, url, trusted=trusted)
        typer.echo(f"Added source: {url}")
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def skill_remove(
    url: Annotated[str, typer.Argument(help="URL of the remote skill source.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Remove a remote skill source."""
    root = resolve_project_root(target)
    try:
        remove_source(root, url)
        typer.echo(f"Removed source: {url}")
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def skill_status(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    all_skills: Annotated[
        bool,
        typer.Option("--all", help="Show all skills, including eligible ones."),
    ] = False,
) -> None:
    """Show local skill requirement eligibility diagnostics."""
    root = resolve_project_root(target)
    statuses = list_local_skill_status(root)

    if not statuses:
        typer.echo("No local skills found under .ai-engineering/skills.")
        return

    ineligible = [status for status in statuses if not status.eligible]
    displayed = statuses if all_skills else ineligible

    if not displayed:
        typer.echo(f"All {len(statuses)} skills are eligible.")
        return

    for status in displayed:
        label = "eligible" if status.eligible else "ineligible"
        typer.echo(f"- {status.name} [{label}]")
        typer.echo(f"  file: {status.file_path}")
        for entry in status.errors:
            typer.echo(f"  error: {entry}")
        if status.missing_bins:
            typer.echo(f"  missing bins: {', '.join(status.missing_bins)}")
        if status.missing_any_bins:
            typer.echo(f"  missing anyBins: {', '.join(status.missing_any_bins)}")
        if status.missing_env:
            typer.echo(f"  missing env: {', '.join(status.missing_env)}")
        if status.missing_config:
            typer.echo(f"  missing config: {', '.join(status.missing_config)}")
        if status.missing_os:
            typer.echo(f"  unsupported os (requires one of): {', '.join(status.missing_os)}")

    typer.echo("")
    typer.echo(
        "Summary: "
        f"{len(statuses) - len(ineligible)} eligible, "
        f"{len(ineligible)} ineligible, "
        f"total {len(statuses)}"
    )
