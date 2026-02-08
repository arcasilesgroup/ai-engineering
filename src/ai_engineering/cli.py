"""CLI entrypoint for ai-engineering."""

from __future__ import annotations

import json
from typing import Any, cast

import typer

from ai_engineering.__version__ import __version__
from ai_engineering.doctor.service import run_doctor
from ai_engineering.installer.service import install


app = typer.Typer(help="ai-engineering governance CLI")


@app.command()
def version() -> None:
    """Show framework version."""
    typer.echo(__version__)


@app.command("install")
def install_cmd() -> None:
    """Bootstrap .ai-engineering in current repository."""
    result = install()
    typer.echo(json.dumps(result, indent=2))


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """Run readiness diagnostics."""
    result = run_doctor()
    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    typer.echo("ai-engineering doctor")
    typer.echo(f"repo: {result['repo']}")
    typer.echo(f"governance root: {'ok' if result['governanceRootExists'] else 'missing'}")
    state_checks = result["stateFiles"]
    if not isinstance(state_checks, dict):
        raise typer.Exit(code=1)
    typed_checks = cast(dict[str, Any], state_checks)
    for key, value in typed_checks.items():
        typer.echo(f"state:{key}: {'ok' if value else 'fail'}")


if __name__ == "__main__":
    app()
