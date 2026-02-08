"""CLI entrypoint for ai-engineering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import typer

from ai_engineering.__version__ import __version__
from ai_engineering.doctor.service import run_doctor
from ai_engineering.installer.service import install
from ai_engineering.paths import repo_root
from ai_engineering.policy.gates import (
    gate_requirements,
    run_commit_msg,
    run_pre_commit,
    run_pre_push,
)


app = typer.Typer(help="ai-engineering governance CLI")
gate_app = typer.Typer(help="Run governance gate checks")
app.add_typer(gate_app, name="gate")


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


@gate_app.command("pre-commit")
def gate_pre_commit() -> None:
    """Run pre-commit gate checks."""
    ok, messages = run_pre_commit()
    for message in messages:
        typer.echo(message)
    if not ok:
        raise typer.Exit(code=1)


@gate_app.command("commit-msg")
def gate_commit_msg(commit_msg_file: str) -> None:
    """Run commit-msg gate checks."""
    message_path = Path(commit_msg_file)
    if not message_path.exists():
        typer.echo(f"missing commit message file: {commit_msg_file}")
        raise typer.Exit(code=1)
    ok, messages = run_commit_msg(message_path)
    for message in messages:
        typer.echo(message)
    if not ok:
        raise typer.Exit(code=1)


@gate_app.command("pre-push")
def gate_pre_push() -> None:
    """Run pre-push gate checks."""
    ok, messages = run_pre_push()
    for message in messages:
        typer.echo(message)
    if not ok:
        raise typer.Exit(code=1)


@gate_app.command("list")
def gate_list(json_output: bool = typer.Option(False, "--json", help="Print JSON output")) -> None:
    """Show configured mandatory gate requirements."""
    requirements = gate_requirements(repo_root())
    if json_output:
        typer.echo(json.dumps(requirements, indent=2))
        return

    protected_raw = requirements.get("protectedBranches", [])
    protected = protected_raw if isinstance(protected_raw, list) else []
    protected_names = [str(item) for item in protected]
    typer.echo(f"protected branches: {', '.join(protected_names) if protected_names else 'none'}")
    stages = requirements.get("stages", {})
    if isinstance(stages, dict):
        for stage, checks in stages.items():
            typer.echo(f"{stage}:")
            if isinstance(checks, list):
                for check in checks:
                    if isinstance(check, dict):
                        typed_check = cast(dict[str, Any], check)
                        tool_raw = typed_check.get("tool")
                        tool = str(tool_raw) if tool_raw is not None else "unknown"
                        typer.echo(f"  - {tool}")


if __name__ == "__main__":
    app()
