"""Core install/update/doctor CLI commands."""

from __future__ import annotations

import json
from typing import Any, cast

import typer

from ai_engineering.__version__ import __version__
from ai_engineering.doctor.service import run_doctor
from ai_engineering.installer.service import install
from ai_engineering.updater import run_update


def register(app: typer.Typer) -> None:
    """Register core top-level commands."""

    @app.command()
    def version() -> None:
        """Show framework version."""
        typer.echo(__version__)

    @app.command("install")
    def install_cmd() -> None:
        """Bootstrap .ai-engineering in current repository."""
        result = install()
        typer.echo(json.dumps(result, indent=2))

    @app.command("update")
    def update_cmd(
        apply: bool = typer.Option(False, "--apply", help="Apply updates (default is dry-run)"),
    ) -> None:
        """Run ownership-safe framework update."""
        result = run_update(apply=apply)
        typer.echo(json.dumps(result, indent=2))

    @app.command()
    def doctor(
        json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
        fix_hooks: bool = typer.Option(
            False,
            "--fix-hooks",
            help="Repair framework-managed git hooks before readiness checks",
        ),
        fix_tools: bool = typer.Option(
            False,
            "--fix-tools",
            help="Attempt auto-remediation for missing Python tooling",
        ),
    ) -> None:
        """Run readiness diagnostics."""
        result = run_doctor(fix_hooks=fix_hooks, fix_tools=fix_tools)
        if json_output:
            typer.echo(json.dumps(result, indent=2))
            return

        typer.echo("ai-engineering doctor")
        typer.echo(f"repo: {result['repo']}")
        typer.echo(f"governance root: {'ok' if result['governanceRootExists'] else 'missing'}")
        branch_policy_raw = result.get("branchPolicy")
        if isinstance(branch_policy_raw, dict):
            branch_policy = cast(dict[str, Any], branch_policy_raw)
            current_raw = branch_policy.get("currentBranch")
            protected_raw = branch_policy.get("currentBranchProtected")
            current = str(current_raw) if current_raw is not None else "unknown"
            protected = bool(protected_raw)
            typer.echo(f"branch: {current} ({'protected' if protected else 'unprotected'})")
        state_checks = result["stateFiles"]
        if not isinstance(state_checks, dict):
            raise typer.Exit(code=1)
        typed_checks = cast(dict[str, Any], state_checks)
        for key, value in typed_checks.items():
            typer.echo(f"state:{key}: {'ok' if value else 'fail'}")
