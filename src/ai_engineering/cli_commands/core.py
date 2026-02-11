"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.__version__ import __version__
from ai_engineering.doctor.service import diagnose
from ai_engineering.installer.service import install
from ai_engineering.paths import resolve_project_root
from ai_engineering.updater.service import _DIFF_MAX_LINES, update


def install_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    stacks: Annotated[
        list[str] | None,
        typer.Option("--stack", "-s", help="Technology stacks to enable."),
    ] = None,
    ides: Annotated[
        list[str] | None,
        typer.Option("--ide", "-i", help="IDE integrations to enable."),
    ] = None,
) -> None:
    """Install the ai-engineering governance framework."""
    root = resolve_project_root(target)
    result = install(root, stacks=stacks or [], ides=ides or [])

    typer.echo(f"Installed to: {root}")
    typer.echo(f"  Governance files created: {result.governance_files.created}")
    typer.echo(f"  Project files created: {result.project_files.created}")
    typer.echo(f"  State files created: {len(result.state_files)}")

    if result.already_installed:
        typer.echo("  (framework was already installed — skipped existing files)")


def update_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Apply changes (dry-run by default)."),
    ] = False,
    show_diff: Annotated[
        bool,
        typer.Option("--diff", "-d", help="Show unified diffs for updated files."),
    ] = False,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON."),
    ] = False,
) -> None:
    """Update framework-managed governance files."""
    root = resolve_project_root(target)
    result = update(root, dry_run=not apply)

    if output_json:
        payload = {
            "mode": "APPLIED" if not result.dry_run else "DRY-RUN",
            "root": str(root),
            "applied": result.applied_count,
            "denied": result.denied_count,
            "changes": [
                {
                    "path": str(c.path),
                    "action": c.action,
                    "diff": c.diff,
                }
                for c in result.changes
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    mode = "APPLIED" if not result.dry_run else "DRY-RUN"
    typer.echo(f"Update [{mode}]: {root}")
    typer.echo(f"  Applied: {result.applied_count}")
    typer.echo(f"  Denied:  {result.denied_count}")

    for change in result.changes:
        marker = "✓" if change.action in ("create", "update") else "✗"
        typer.echo(f"  {marker} {change.path} ({change.action})")

        if show_diff and change.diff:
            diff_text = change.diff
            lines = diff_text.splitlines(keepends=True)
            if len(lines) > _DIFF_MAX_LINES:
                lines = lines[:_DIFF_MAX_LINES]
                remaining = len(diff_text.splitlines()) - _DIFF_MAX_LINES
                lines.append(f"    ... ({remaining} more lines)\n")
            for line in lines:
                typer.echo(f"    {line}", nl=False)


def doctor_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    fix_hooks: Annotated[
        bool,
        typer.Option("--fix-hooks", help="Reinstall managed git hooks."),
    ] = False,
    fix_tools: Annotated[
        bool,
        typer.Option("--fix-tools", help="Install missing Python tools."),
    ] = False,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON."),
    ] = False,
) -> None:
    """Diagnose and optionally fix framework health."""
    root = resolve_project_root(target)
    report = diagnose(root, fix_hooks=fix_hooks, fix_tools=fix_tools)

    if output_json:
        typer.echo(json.dumps(report.to_dict(), indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        typer.echo(f"Doctor [{status}]: {root}")
        typer.echo(f"  Summary: {report.summary}")

        for check in report.checks:
            icon = {"ok": "✓", "warn": "⚠", "fail": "✗", "fixed": "🔧"}.get(check.status.value, "?")
            typer.echo(f"  {icon} {check.name}: {check.message}")

    if not report.passed:
        raise typer.Exit(code=1)


def version_cmd() -> None:
    """Show the installed ai-engineering version and lifecycle status."""
    from ai_engineering.version.checker import check_version, load_registry

    registry = load_registry()
    result = check_version(__version__, registry)
    typer.echo(f"ai-engineering {result.message}")
