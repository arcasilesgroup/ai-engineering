"""Typer application factory for ai-engineering CLI.

Builds the main Typer app with all command groups registered.
The factory pattern allows tests to create isolated app instances.

Includes:
- Global ``--json`` flag for agent-friendly structured output.
- Version lifecycle callback that blocks deprecated versions on non-exempt commands.
- Centralized exception handler that converts path-related OS errors into
  clean user-facing messages (no tracebacks).
"""

from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from typing import Annotated

import typer

from ai_engineering.cli_commands import (
    cicd,
    core,
    gate,
    maintenance,
    release,
    review,
    setup,
    skills,
    stack_ide,
    validate,
    vcs,
)

# Commands exempt from deprecation blocking (needed for diagnosis and remediation).
_EXEMPT_COMMANDS: frozenset[str] = frozenset({"version", "update", "doctor"})

# Exceptions that should produce a clean one-line error instead of a traceback.
_USER_FACING_EXCEPTIONS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    NotADirectoryError,
    PermissionError,
)


def _cli_error_boundary(func: Callable[..., object]) -> Callable[..., object]:
    """Wrap a CLI command to catch OS path errors and emit a clean message.

    Converts FileNotFoundError, NotADirectoryError, and PermissionError into
    a single-line ``Error: <message>`` on stderr with exit code 1, instead of
    a raw Python traceback.  In JSON mode, emits an error envelope instead.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        try:
            return func(*args, **kwargs)
        except _USER_FACING_EXCEPTIONS as exc:
            from ai_engineering.cli_output import is_json_mode

            if is_json_mode():
                from ai_engineering.cli_envelope import emit_error

                cmd_name = getattr(func, "__name__", "unknown")
                emit_error(
                    command=cmd_name.replace("_cmd", "").replace("_", "-"),
                    message=str(exc),
                    code=type(exc).__name__,
                    fix="Check the path exists and you have permission to access it.",
                )
            else:
                typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from None

    return wrapper


def _app_callback(
    ctx: typer.Context,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output structured JSON for agent consumption."),
    ] = False,
) -> None:
    """App-level callback: global flags + version lifecycle policy."""
    from ai_engineering.cli_output import set_json_mode

    set_json_mode(json_output)

    if ctx.invoked_subcommand is None:
        # No subcommand: show logo + help (human) or command tree (JSON)
        if json_output:
            from ai_engineering.cli_envelope import emit_success

            emit_success(
                "ai-eng",
                {
                    "commands": [
                        "install",
                        "update",
                        "doctor",
                        "validate",
                        "version",
                        "stack",
                        "ide",
                        "gate",
                        "skill",
                        "maintenance",
                        "vcs",
                        "review",
                        "cicd",
                        "setup",
                        "release",
                    ]
                },
            )
            raise typer.Exit(code=0)
        else:
            from ai_engineering.cli_ui import show_logo

            show_logo()
            typer.echo(ctx.get_help())
            raise typer.Exit(code=0)

    from ai_engineering.__version__ import __version__
    from ai_engineering.version.checker import check_version

    result = check_version(__version__)

    command = ctx.invoked_subcommand or ""

    if (result.is_deprecated or result.is_eol) and command not in _EXEMPT_COMMANDS:
        status_label = "deprecated" if result.is_deprecated else "end-of-life"
        sys.stderr.write(
            f"BLOCKED: ai-engineering {__version__} is {status_label}.\n"
            f"  {result.message}\n"
            f"  Run 'ai-eng update' to upgrade or 'ai-eng doctor' to diagnose.\n"
        )
        raise typer.Exit(code=1)

    if result.is_outdated:
        sys.stderr.write(f"WARNING: {result.message}\n  Run 'ai-eng update' to upgrade.\n")


def _safe(func: Callable) -> Callable:
    """Shorthand: apply the CLI error boundary to a command function."""
    return _cli_error_boundary(func)


def create_app() -> typer.Typer:
    """Build and return the Typer application.

    Registers all command groups and sub-commands:
    - Core commands: install, update, doctor, version.
    - Stack/IDE commands: stack add/remove/list, ide add/remove/list.
    - Gate commands: gate pre-commit/commit-msg/pre-push/risk-check.
    - Skills commands: skill list/sync/add/remove/status.
    - Maintenance commands: maintenance report/pr/branch-cleanup/risk-status/pipeline-compliance.

    Returns:
        Configured Typer application instance.
    """
    app = typer.Typer(
        name="ai-eng",
        help="AI governance framework for secure software delivery.",
        no_args_is_help=False,
        rich_markup_mode="rich",
        callback=_app_callback,
        invoke_without_command=True,
        epilog="[dim]Docs & issues:[/dim] https://github.com/arcasilesgroup/ai-engineering",
    )

    # Core commands (top-level)
    app.command("install")(_safe(core.install_cmd))
    app.command("update")(_safe(core.update_cmd))
    app.command("doctor")(_safe(core.doctor_cmd))
    app.command("validate")(_safe(validate.validate_cmd))
    app.command("version")(core.version_cmd)
    app.command("release")(_safe(release.release_cmd))

    # Stack sub-group
    stack_app = typer.Typer(
        name="stack",
        help="Manage technology stacks.",
        no_args_is_help=True,
    )
    stack_app.command("add")(_safe(stack_ide.stack_add))
    stack_app.command("remove")(_safe(stack_ide.stack_remove))
    stack_app.command("list")(_safe(stack_ide.stack_list))
    app.add_typer(stack_app, name="stack")

    # IDE sub-group
    ide_app = typer.Typer(
        name="ide",
        help="Manage IDE integrations.",
        no_args_is_help=True,
    )
    ide_app.command("add")(_safe(stack_ide.ide_add))
    ide_app.command("remove")(_safe(stack_ide.ide_remove))
    ide_app.command("list")(_safe(stack_ide.ide_list))
    app.add_typer(ide_app, name="ide")

    # Gate sub-group
    gate_app = typer.Typer(
        name="gate",
        help="Run git hook quality gate checks.",
        no_args_is_help=True,
    )
    gate_app.command("pre-commit")(_safe(gate.gate_pre_commit))
    gate_app.command("commit-msg")(_safe(gate.gate_commit_msg))
    gate_app.command("pre-push")(_safe(gate.gate_pre_push))
    gate_app.command("risk-check")(_safe(gate.gate_risk_check))
    gate_app.command("all")(_safe(gate.gate_all))
    app.add_typer(gate_app, name="gate")

    # Skill sub-group
    skill_app = typer.Typer(
        name="skill",
        help="Manage remote skill sources (registration, sync, eligibility).",
        no_args_is_help=True,
    )
    skill_app.command("list")(_safe(skills.skill_list))
    skill_app.command("sync")(_safe(skills.skill_sync))
    skill_app.command("add")(_safe(skills.skill_add))
    skill_app.command("remove")(_safe(skills.skill_remove))
    skill_app.command("status")(_safe(skills.skill_status))
    app.add_typer(skill_app, name="skill")

    # Maintenance sub-group
    maint_app = typer.Typer(
        name="maintenance",
        help="Framework maintenance operations.",
        no_args_is_help=True,
    )
    maint_app.command("report")(_safe(maintenance.maintenance_report))
    maint_app.command("pr")(_safe(maintenance.maintenance_pr))
    maint_app.command("branch-cleanup")(_safe(maintenance.maintenance_branch_cleanup))
    maint_app.command("risk-status")(_safe(maintenance.maintenance_risk_status))
    maint_app.command("pipeline-compliance")(_safe(maintenance.maintenance_pipeline_compliance))
    maint_app.command("repo-status")(_safe(maintenance.maintenance_repo_status))
    maint_app.command("spec-reset")(_safe(maintenance.maintenance_spec_reset))
    maint_app.command("all")(_safe(maintenance.maintenance_all))
    app.add_typer(maint_app, name="maintenance")

    # VCS sub-group
    vcs_app = typer.Typer(
        name="vcs",
        help="Manage VCS provider configuration.",
        no_args_is_help=True,
    )
    vcs_app.command("status")(_safe(vcs.vcs_status))
    vcs_app.command("set-primary")(_safe(vcs.vcs_set_primary))
    app.add_typer(vcs_app, name="vcs")

    # Review sub-group
    review_app = typer.Typer(
        name="review",
        help="Run provider-backed review operations.",
        no_args_is_help=True,
    )
    review_app.command("pr")(_safe(review.review_pr))
    app.add_typer(review_app, name="review")

    # CI/CD sub-group
    cicd_app = typer.Typer(
        name="cicd",
        help="Manage generated CI/CD pipelines.",
        no_args_is_help=True,
    )
    cicd_app.command("regenerate")(_safe(cicd.cicd_regenerate))
    app.add_typer(cicd_app, name="cicd")

    # Setup sub-group
    setup_app = typer.Typer(
        name="setup",
        help="Configure platform credentials for governance workflows.",
        no_args_is_help=True,
    )
    setup_app.command("platforms")(_safe(setup.setup_platforms_cmd))
    setup_app.command("github")(_safe(setup.setup_github_cmd))
    setup_app.command("sonar")(_safe(setup.setup_sonar_cmd))
    setup_app.command("azure-devops")(_safe(setup.setup_azure_devops_cmd))
    setup_app.command("sonarlint")(_safe(setup.setup_sonarlint_cmd))
    app.add_typer(setup_app, name="setup")

    return app
