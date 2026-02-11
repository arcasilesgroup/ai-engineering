"""Typer application factory for ai-engineering CLI.

Builds the main Typer app with all command groups registered.
The factory pattern allows tests to create isolated app instances.

Includes a version lifecycle callback that:
- Blocks deprecated versions on non-exempt commands (security enforcement).
- Warns about outdated versions on stderr (non-blocking).
"""

from __future__ import annotations

import sys

import typer

from ai_engineering.cli_commands import core, gate, maintenance, skills, stack_ide, validate

# Commands exempt from deprecation blocking (needed for diagnosis and remediation).
_EXEMPT_COMMANDS: frozenset[str] = frozenset({"version", "update", "doctor"})


def _version_lifecycle_callback(ctx: typer.Context) -> None:
    """App-level callback enforcing version lifecycle policy.

    - Deprecated/EOL versions: block all commands except exempt ones (D-010-2).
    - Outdated versions: print warning to stderr (non-blocking).
    - Fail-open on registry errors (D-010-3).
    """
    if ctx.invoked_subcommand is None:
        return

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


def create_app() -> typer.Typer:
    """Build and return the Typer application.

    Registers all command groups and sub-commands:
    - Core commands: install, update, doctor, version.
    - Stack/IDE commands: stack add/remove/list, ide add/remove/list.
    - Gate commands: gate pre-commit/commit-msg/pre-push/risk-check.
    - Skills commands: skill list/sync/add/remove.
    - Maintenance commands: maintenance report/pr/branch-cleanup/risk-status/pipeline-compliance.

    Returns:
        Configured Typer application instance.
    """
    app = typer.Typer(
        name="ai-eng",
        help="AI governance framework for secure software delivery.",
        no_args_is_help=True,
        rich_markup_mode="rich",
        callback=_version_lifecycle_callback,
        invoke_without_command=True,
    )

    # Core commands (top-level)
    app.command("install")(core.install_cmd)
    app.command("update")(core.update_cmd)
    app.command("doctor")(core.doctor_cmd)
    app.command("validate")(validate.validate_cmd)
    app.command("version")(core.version_cmd)

    # Stack sub-group
    stack_app = typer.Typer(
        name="stack",
        help="Manage technology stacks.",
        no_args_is_help=True,
    )
    stack_app.command("add")(stack_ide.stack_add)
    stack_app.command("remove")(stack_ide.stack_remove)
    stack_app.command("list")(stack_ide.stack_list)
    app.add_typer(stack_app, name="stack")

    # IDE sub-group
    ide_app = typer.Typer(
        name="ide",
        help="Manage IDE integrations.",
        no_args_is_help=True,
    )
    ide_app.command("add")(stack_ide.ide_add)
    ide_app.command("remove")(stack_ide.ide_remove)
    ide_app.command("list")(stack_ide.ide_list)
    app.add_typer(ide_app, name="ide")

    # Gate sub-group
    gate_app = typer.Typer(
        name="gate",
        help="Run git hook quality gate checks.",
        no_args_is_help=True,
    )
    gate_app.command("pre-commit")(gate.gate_pre_commit)
    gate_app.command("commit-msg")(gate.gate_commit_msg)
    gate_app.command("pre-push")(gate.gate_pre_push)
    gate_app.command("risk-check")(gate.gate_risk_check)
    app.add_typer(gate_app, name="gate")

    # Skill sub-group
    skill_app = typer.Typer(
        name="skill",
        help="Manage remote skill sources.",
        no_args_is_help=True,
    )
    skill_app.command("list")(skills.skill_list)
    skill_app.command("sync")(skills.skill_sync)
    skill_app.command("add")(skills.skill_add)
    skill_app.command("remove")(skills.skill_remove)
    app.add_typer(skill_app, name="skill")

    # Maintenance sub-group
    maint_app = typer.Typer(
        name="maintenance",
        help="Framework maintenance operations.",
        no_args_is_help=True,
    )
    maint_app.command("report")(maintenance.maintenance_report)
    maint_app.command("pr")(maintenance.maintenance_pr)
    maint_app.command("branch-cleanup")(maintenance.maintenance_branch_cleanup)
    maint_app.command("risk-status")(maintenance.maintenance_risk_status)
    maint_app.command("pipeline-compliance")(maintenance.maintenance_pipeline_compliance)
    app.add_typer(maint_app, name="maintenance")

    return app
