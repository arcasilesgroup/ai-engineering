"""CLI entrypoint for ai-engineering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import typer

from ai_engineering.__version__ import __version__
from ai_engineering.commands.workflows import (
    PrOnlyMode,
    run_commit_workflow,
    run_pr_only_workflow,
    run_pr_workflow,
)
from ai_engineering.doctor.service import run_doctor
from ai_engineering.installer.service import install
from ai_engineering.maintenance.report import create_pr_from_payload, generate_report
from ai_engineering.paths import repo_root
from ai_engineering.policy.gates import (
    gate_requirements,
    run_commit_msg,
    run_pre_commit,
    run_pre_push,
)
from ai_engineering.skills.service import export_sync_report_json, list_sources, sync_sources


app = typer.Typer(help="ai-engineering governance CLI")
gate_app = typer.Typer(help="Run governance gate checks")
acho_app = typer.Typer(help="Acho command contract")
skill_app = typer.Typer(help="Remote skills lock/cache operations")
maintenance_app = typer.Typer(help="Maintenance and context health workflows")
app.add_typer(gate_app, name="gate")
app.add_typer(acho_app, name="acho")
app.add_typer(skill_app, name="skill")
app.add_typer(maintenance_app, name="maintenance")


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


@app.command("commit")
def commit_cmd(
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    only: bool = typer.Option(False, "--only", help="Stage and commit only"),
) -> None:
    """Run governed commit workflow."""
    ok, notes = run_commit_workflow(message=message, push=not only)
    for note in notes:
        typer.echo(note)
    if not ok:
        raise typer.Exit(code=1)


@app.command("pr")
def pr_cmd(
    only: bool = typer.Option(False, "--only", help="PR-only workflow"),
    message: str = typer.Option(
        "chore: governed commit", "--message", "-m", help="Commit message for /pr"
    ),
    title: str = typer.Option("Governed update", "--title", help="PR title"),
    body: str = typer.Option(
        "Automated PR via ai-engineering command flow.", "--body", help="PR body"
    ),
    on_unpushed_branch: PrOnlyMode = typer.Option(
        "defer-pr",
        "--on-unpushed-branch",
        help="Mode for unpushed branch: auto-push|defer-pr|attempt-pr-anyway|export-pr-payload",
    ),
) -> None:
    """Run governed PR workflow."""
    if only:
        ok, notes = run_pr_only_workflow(
            title=title,
            body=body,
            mode=on_unpushed_branch,
            record_decision=True,
        )
    else:
        ok, notes = run_pr_workflow(message=message, title=title, body=body)
    for note in notes:
        typer.echo(note)
    if not ok:
        raise typer.Exit(code=1)


@acho_app.callback(invoke_without_command=True)
def acho_cmd(
    ctx: typer.Context,
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
) -> None:
    """Run /acho default contract: stage + commit + push current branch."""
    if ctx.invoked_subcommand:
        return
    ok, notes = run_commit_workflow(message=message, push=True)
    for note in notes:
        typer.echo(note)
    if not ok:
        raise typer.Exit(code=1)


@acho_app.command("pr")
def acho_pr_cmd(
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    title: str = typer.Option("Governed update", "--title", help="PR title"),
    body: str = typer.Option(
        "Automated PR via ai-engineering command flow.", "--body", help="PR body"
    ),
) -> None:
    """Run /acho pr contract: stage + commit + push + create PR."""
    ok, notes = run_pr_workflow(message=message, title=title, body=body)
    for note in notes:
        typer.echo(note)
    if not ok:
        raise typer.Exit(code=1)


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


@skill_app.command("list")
def skill_list(json_output: bool = typer.Option(False, "--json", help="Print JSON output")) -> None:
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
    offline: bool = typer.Option(False, "--offline", help="Use cache only and skip remote fetch"),
) -> None:
    """Sync skill sources and refresh lock metadata."""
    result = sync_sources(offline=offline)
    report_path = repo_root() / ".ai-engineering" / "state" / "skills_sync_report.json"
    export_sync_report_json(report_path, result)
    typer.echo(json.dumps(result, indent=2))
    summary = result.get("summary", {})
    if isinstance(summary, dict) and int(summary.get("failed", 0)) > 0:
        raise typer.Exit(code=1)


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


if __name__ == "__main__":
    app()
