"""Command-contract workflow CLI commands."""

from __future__ import annotations

from typing import cast

import typer

from ai_engineering.commands.workflows import (
    PrOnlyMode,
    run_commit_workflow,
    run_pr_only_workflow,
    run_pr_workflow,
)


PR_ONLY_MODES = {
    "auto-push",
    "defer-pr",
    "attempt-pr-anyway",
    "export-pr-payload",
}


def register(app: typer.Typer, acho_app: typer.Typer) -> None:
    """Register workflow and acho commands."""

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
        on_unpushed_branch: str = typer.Option(
            "defer-pr",
            "--on-unpushed-branch",
            help="Mode for unpushed branch: auto-push|defer-pr|attempt-pr-anyway|export-pr-payload",
        ),
    ) -> None:
        """Run governed PR workflow."""
        if only:
            if on_unpushed_branch not in PR_ONLY_MODES:
                typer.echo(
                    "invalid --on-unpushed-branch value. "
                    "expected: auto-push|defer-pr|attempt-pr-anyway|export-pr-payload"
                )
                raise typer.Exit(code=1)
            ok, notes = run_pr_only_workflow(
                title=title,
                body=body,
                mode=cast(PrOnlyMode, on_unpushed_branch),
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
