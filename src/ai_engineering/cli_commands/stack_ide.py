"""Stack and IDE CLI commands: add, remove, list.

Manages technology stacks and IDE integrations for an installed project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from ai_engineering.installer.operations import (
    InstallerError,
    add_ide,
    add_stack,
    list_status,
    remove_ide,
    remove_stack,
)
from ai_engineering.paths import resolve_project_root


def stack_add(
    stack: Annotated[str, typer.Argument(help="Stack name to add (e.g. python).")],
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Add a technology stack."""
    root = resolve_project_root(target)
    try:
        manifest = add_stack(root, stack)
        typer.echo(f"Added stack '{stack}'. Active stacks: {manifest.stacks}")
    except InstallerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def stack_remove(
    stack: Annotated[str, typer.Argument(help="Stack name to remove.")],
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Remove a technology stack."""
    root = resolve_project_root(target)
    try:
        manifest = remove_stack(root, stack)
        typer.echo(f"Removed stack '{stack}'. Active stacks: {manifest.stacks}")
    except InstallerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def stack_list(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active technology stacks."""
    root = resolve_project_root(target)
    try:
        manifest = list_status(root)
        if manifest.stacks:
            for s in manifest.stacks:
                typer.echo(f"  - {s}")
        else:
            typer.echo("  (no stacks configured)")
    except InstallerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def ide_add(
    ide: Annotated[str, typer.Argument(help="IDE name to add (e.g. vscode).")],
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Add an IDE integration."""
    root = resolve_project_root(target)
    try:
        manifest = add_ide(root, ide)
        typer.echo(f"Added IDE '{ide}'. Active IDEs: {manifest.ides}")
    except InstallerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def ide_remove(
    ide: Annotated[str, typer.Argument(help="IDE name to remove.")],
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Remove an IDE integration."""
    root = resolve_project_root(target)
    try:
        manifest = remove_ide(root, ide)
        typer.echo(f"Removed IDE '{ide}'. Active IDEs: {manifest.ides}")
    except InstallerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def ide_list(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active IDE integrations."""
    root = resolve_project_root(target)
    try:
        manifest = list_status(root)
        if manifest.ides:
            for i in manifest.ides:
                typer.echo(f"  - {i}")
        else:
            typer.echo("  (no IDEs configured)")
    except InstallerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
