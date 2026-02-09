"""Stack and IDE management CLI commands."""

from __future__ import annotations

import json

import typer

from ai_engineering.installer.operations import (
    add_ide,
    add_stack,
    list_stack_ide_status,
    remove_ide,
    remove_stack,
)


def register(stack_app: typer.Typer, ide_app: typer.Typer) -> None:
    """Register stack and ide command groups."""

    @stack_app.command("list")
    def stack_list() -> None:
        """List installed and available stacks."""
        typer.echo(json.dumps(list_stack_ide_status(), indent=2))

    @stack_app.command("add")
    def stack_add(name: str = typer.Argument(..., help="Stack name, e.g. python")) -> None:
        """Add a stack template set to repository."""
        result = add_stack(name)
        typer.echo(json.dumps(result, indent=2))
        if not bool(result.get("ok", False)):
            raise typer.Exit(code=1)

    @stack_app.command("remove")
    def stack_remove(name: str = typer.Argument(..., help="Stack name, e.g. python")) -> None:
        """Remove a stack template set with safe cleanup semantics."""
        result = remove_stack(name)
        typer.echo(json.dumps(result, indent=2))
        if not bool(result.get("ok", False)):
            raise typer.Exit(code=1)

    @ide_app.command("list")
    def ide_list() -> None:
        """List installed and available IDE profiles."""
        typer.echo(json.dumps(list_stack_ide_status(), indent=2))

    @ide_app.command("add")
    def ide_add(name: str = typer.Argument(..., help="IDE name")) -> None:
        """Add an IDE instruction profile."""
        result = add_ide(name)
        typer.echo(json.dumps(result, indent=2))
        if not bool(result.get("ok", False)):
            raise typer.Exit(code=1)

    @ide_app.command("remove")
    def ide_remove(name: str = typer.Argument(..., help="IDE name")) -> None:
        """Remove an IDE instruction profile with safe cleanup semantics."""
        result = remove_ide(name)
        typer.echo(json.dumps(result, indent=2))
        if not bool(result.get("ok", False)):
            raise typer.Exit(code=1)
