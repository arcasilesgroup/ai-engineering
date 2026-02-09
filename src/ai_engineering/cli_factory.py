"""CLI app factory and command group composition."""

from __future__ import annotations

import typer

from ai_engineering.cli_commands import core, gate, maintenance, skills, stack_ide, workflow


def create_app() -> typer.Typer:
    """Build Typer app with all command groups."""
    app = typer.Typer(help="ai-engineering governance CLI")
    gate_app = typer.Typer(help="Run governance gate checks")
    acho_app = typer.Typer(help="Acho command contract")
    skill_app = typer.Typer(help="Remote skills lock/cache operations")
    maintenance_app = typer.Typer(help="Maintenance and context health workflows")
    stack_app = typer.Typer(help="Manage framework stack templates")
    ide_app = typer.Typer(help="Manage IDE instruction templates")

    app.add_typer(gate_app, name="gate")
    app.add_typer(acho_app, name="acho")
    app.add_typer(skill_app, name="skill")
    app.add_typer(maintenance_app, name="maintenance")
    app.add_typer(stack_app, name="stack")
    app.add_typer(ide_app, name="ide")

    core.register(app)
    workflow.register(app, acho_app)
    gate.register(gate_app)
    skills.register(skill_app)
    maintenance.register(maintenance_app)
    stack_ide.register(stack_app, ide_app)
    return app
