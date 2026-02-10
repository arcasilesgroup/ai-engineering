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
