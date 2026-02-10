"""Typer application factory for ai-engineering CLI.

Builds the main Typer app with all command groups registered.
The factory pattern allows tests to create isolated app instances.
"""

from __future__ import annotations

import typer

from ai_engineering.cli_commands import core, gate, maintenance, skills, stack_ide


def create_app() -> typer.Typer:
    """Build and return the Typer application.

    Registers all command groups and sub-commands:
    - Core commands: install, update, doctor, version.
    - Stack/IDE commands: stack add/remove/list, ide add/remove/list.
    - Gate commands: gate pre-commit/commit-msg/pre-push.
    - Skills commands: skill list/sync/add/remove.
    - Maintenance commands: maintenance report/pr.

    Returns:
        Configured Typer application instance.
    """
    app = typer.Typer(
        name="ai-eng",
        help="AI governance framework for secure software delivery.",
        no_args_is_help=True,
        rich_markup_mode="rich",
    )

    # Core commands (top-level)
    app.command("install")(core.install_cmd)
    app.command("update")(core.update_cmd)
    app.command("doctor")(core.doctor_cmd)
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
    app.add_typer(maint_app, name="maintenance")

    return app
