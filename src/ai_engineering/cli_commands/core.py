"""Core CLI commands: install, update, doctor, version.

These are the primary entry points for the ``ai-eng`` CLI.
Human-first Rich output by default; ``--json`` for agent consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
import click.exceptions
import typer

from ai_engineering.__version__ import __version__
from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import (
    file_count,
    header,
    kv,
    print_stdout,
    result_header,
    show_logo,
    status_line,
    suggest_next,
    warning,
)
from ai_engineering.doctor.service import diagnose
from ai_engineering.installer.service import install
from ai_engineering.paths import resolve_project_root
from ai_engineering.platforms.detector import detect_platforms
from ai_engineering.updater.service import _DIFF_MAX_LINES, update
from ai_engineering.vcs.factory import detect_from_remote


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
    vcs: Annotated[
        str | None,
        typer.Option("--vcs", help="Primary VCS provider: github or azure_devops."),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option(
            "--provider",
            "-p",
            help="AI providers to enable (e.g. claude_code, github_copilot).",
        ),
    ] = None,
) -> None:
    """Install the ai-engineering governance framework."""
    root = resolve_project_root(target)

    # Resolve VCS provider: explicit flag > autodetect > interactive prompt
    resolved_vcs = _resolve_vcs_provider(vcs, root)

    with spinner("Installing governance framework..."):
        result = install(
            root,
            stacks=stacks or [],
            ides=ides or [],
            vcs_provider=resolved_vcs,
            ai_providers=providers,
        )

    ai_label = ", ".join(providers) if providers else "claude_code"

    if is_json_mode():
        emit_success(
            "ai-eng install",
            {
                "root": str(root),
                "governance_files": len(result.governance_files.created),
                "project_files": len(result.project_files.created),
                "state_files": len(result.state_files),
                "vcs_provider": resolved_vcs,
                "ai_providers": providers or ["claude_code"],
                "readiness_status": result.readiness_status,
                "already_installed": result.already_installed,
                "manual_steps": result.manual_steps,
                "guide_text": result.guide_text,
            },
            [
                NextAction(command="ai-eng doctor", description="Run health diagnostics"),
                NextAction(
                    command="ai-eng setup platforms",
                    description="Configure platform credentials",
                ),
            ],
        )
    else:
        # Primary result on stdout (preserves test assertions)
        print_stdout(f"Installed to: {root}")

        # Decorated output on stderr
        file_count("Governance", len(result.governance_files.created))
        file_count("Project", len(result.project_files.created))
        kv("State", f"{len(result.state_files)} files")
        kv("VCS", resolved_vcs)
        kv("AI Providers", ai_label)
        kv("Readiness", result.readiness_status)

        if result.manual_steps:
            warning("Manual steps required:")
            for step in result.manual_steps:
                print_stdout(f"    - {step}")

        if result.already_installed:
            print_stdout("  (framework was already installed \u2014 skipped existing files)")

        next_steps = [
            ("ai-eng doctor", "Run health diagnostics"),
            ("ai-eng setup platforms", "Configure platform credentials"),
        ]
        if result.guide_text:
            next_steps.append(("ai-eng guide", "View branch policy setup guide"))
        suggest_next(next_steps)

        # Branch policy guide at the END — only when automation failed
        if result.guide_text:
            warning("Automatic branch policy application was not possible.")
            warning("You must configure branch protection manually to enforce governance gates.")
            header("Branch Policy Setup Guide")
            print_stdout(result.guide_text)

    # Optional platform onboarding prompt (D024-003: opt-in).
    if not is_json_mode():
        _offer_platform_onboarding(root)


def _resolve_vcs_provider(vcs: str | None, root: Path) -> str:
    """Resolve VCS provider from flag, remote detection, or interactive prompt.

    Args:
        vcs: Explicit --vcs flag value, or None.
        root: Project root for remote detection.

    Returns:
        Resolved VCS provider string.
    """
    if vcs is not None:
        return vcs

    # Try autodetection from git remote
    from ai_engineering.git.operations import run_git

    ok, _ = run_git(["remote", "get-url", "origin"], root)
    if ok:
        return detect_from_remote(root)

    # No remote — prompt interactively (or default in non-interactive/JSON mode)
    if is_json_mode():
        return "github"

    try:
        choice = typer.prompt(
            "No git remote detected. VCS provider",
            default="github",
            type=click.Choice(["github", "azure_devops"]),
        )
        return choice
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return "github"


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
        typer.Option("--json", help="Output report as JSON (deprecated: use global --json)."),
    ] = False,
) -> None:
    """Update framework-managed governance files."""
    root = resolve_project_root(target)
    with spinner("Checking for updates..."):
        result = update(root, dry_run=not apply)

    if is_json_mode() or output_json:
        emit_success(
            "ai-eng update",
            {
                "mode": "APPLIED" if not result.dry_run else "DRY-RUN",
                "root": str(root),
                "applied": result.applied_count,
                "denied": result.denied_count,
                "changes": [
                    {"path": str(c.path), "action": c.action, "diff": c.diff}
                    for c in result.changes
                ],
            },
            [
                NextAction(command="ai-eng doctor", description="Verify framework health"),
                NextAction(command="ai-eng update --apply", description="Apply changes"),
            ],
        )
        return

    mode = "APPLIED" if not result.dry_run else "DRY-RUN"
    # Primary result on stdout
    print_stdout(f"Update [{mode}]: {root}")

    # Decorated output on stderr
    kv("Applied", result.applied_count)
    kv("Denied", result.denied_count)

    for change in result.changes:
        st = "ok" if change.action in ("create", "update") else "fail"
        status_line(st, str(change.path), change.action)

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
        typer.Option("--json", help="Output report as JSON (deprecated: use global --json)."),
    ] = False,
) -> None:
    """Diagnose and optionally fix framework health."""
    root = resolve_project_root(target)
    with spinner("Running health diagnostics..."):
        report = diagnose(root, fix_hooks=fix_hooks, fix_tools=fix_tools)

    from ai_engineering.doctor.service import check_platforms as _check_plat

    _check_plat(root, report)

    if is_json_mode() or output_json:
        report_dict = report.to_dict()
        if is_json_mode():
            next_actions = []
            if not report.passed:
                next_actions = [
                    NextAction(
                        command="ai-eng doctor --fix-tools",
                        description="Install missing tools",
                    ),
                    NextAction(
                        command="ai-eng doctor --fix-hooks",
                        description="Reinstall git hooks",
                    ),
                ]
            emit_success("ai-eng doctor", report_dict, next_actions)
        else:
            # Legacy per-command --json: raw dict output
            import json

            typer.echo(json.dumps(report_dict, indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        # Result header on stderr (CliRunner captures both by default)
        result_header("Doctor", status, str(root))
        kv("Summary", report.summary)

        for check in report.checks:
            status_line(check.status.value, check.name, check.message)

        if not report.passed:
            suggest_next(
                [
                    ("ai-eng doctor --fix-tools", "Install missing tools"),
                    ("ai-eng doctor --fix-hooks", "Reinstall git hooks"),
                ]
            )

    if not report.passed:
        raise typer.Exit(code=1)


def version_cmd() -> None:
    """Show the installed ai-engineering version and lifecycle status."""
    from ai_engineering.version.checker import check_version, load_registry

    if is_json_mode():
        registry = load_registry()
        result = check_version(__version__, registry)
        emit_success(
            "ai-eng version",
            {"version": __version__, "message": result.message},
        )
    else:
        show_logo()
        registry = load_registry()
        result = check_version(__version__, registry)
        typer.echo(f"ai-engineering {result.message}")


def _offer_platform_onboarding(root: Path) -> None:
    """Offer optional platform credential setup after install.

    Detects platform markers and prompts the user to run setup.
    When no platforms are auto-detected, still offers manual setup.
    Always skippable (D024-003).
    """
    detected = detect_platforms(root)
    if detected:
        names = ", ".join(p.value for p in detected)
        typer.echo(f"\n  Detected platforms: {names}")
    else:
        typer.echo("\n  No platforms auto-detected.")

    try:
        run_setup = typer.confirm("  Configure platform credentials now?", default=False)
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return
    if run_setup:
        from ai_engineering.cli_commands.setup import setup_platforms_cmd

        setup_platforms_cmd(root)
