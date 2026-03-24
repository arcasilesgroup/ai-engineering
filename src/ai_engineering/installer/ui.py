"""Install wizard UI rendering.

Uses Rich for decorated output. Falls back to plain text if Rich
is unavailable.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

try:
    from rich.console import Console
    from rich.panel import Panel

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

_console = Console(stderr=True) if _HAS_RICH else None


@dataclass
class StepStatus:
    """Status of a wizard step."""

    number: int
    total: int
    name: str
    description: str
    status: str  # "ok", "warn", "fail", "skip"
    detail: str = ""


def render_step(step: StepStatus) -> None:
    """Render a single wizard step line."""
    icons = {
        "ok": "[green]\u2713[/]",
        "warn": "[yellow]\u26a0[/]",
        "fail": "[red]\u2717[/]",
        "skip": "[dim]\u2013[/]",
    }
    if _HAS_RICH and _console:
        icon = icons.get(step.status, "?")
        _console.print(
            f"  [{step.number}/{step.total}] {step.name:<20} "
            f"{step.description:<40} {icon} {step.detail}"
        )
    else:
        icon_plain = {"ok": "\u2713", "warn": "\u26a0", "fail": "\u2717", "skip": "\u2013"}
        icon = icon_plain.get(step.status, "?")
        print(
            f"  [{step.number}/{step.total}] {step.name:<20} "
            f"{step.description:<40} {icon} {step.detail}",
            file=sys.stderr,
        )


def render_summary(
    files_created: int,
    hooks_installed: int,
    warnings: list[str],
    pending_setup: list[tuple[str, str]],
    next_steps: list[tuple[str, str]],
) -> None:
    """Render the install summary panel."""
    if _HAS_RICH and _console:
        lines: list[str] = []
        lines.append(f"Files created: {files_created}    Hooks: {hooks_installed}")
        if warnings:
            lines.append("")
            lines.append("[yellow]\u26a0 Pending setup:[/]")
            for cmd, desc in pending_setup:
                lines.append(f"  \u2192 {cmd:<30} ({desc})")
        lines.append("")
        lines.append("[bold]Next steps:[/]")
        for i, (cmd, desc) in enumerate(next_steps, 1):
            lines.append(f"  {i}. Run  [cyan]{cmd}[/]    {desc}")
        panel = Panel("\n".join(lines), title="Install Complete", border_style="green")
        _console.print(panel)
    else:
        print("\n--- Install Complete ---", file=sys.stderr)
        print(f"Files created: {files_created}    Hooks: {hooks_installed}", file=sys.stderr)
        if warnings:
            print("\n\u26a0 Pending setup:", file=sys.stderr)
            for cmd, desc in pending_setup:
                print(f"  \u2192 {cmd:<30} ({desc})", file=sys.stderr)
        print("\nNext steps:", file=sys.stderr)
        for i, (cmd, desc) in enumerate(next_steps, 1):
            print(f"  {i}. Run  {cmd}    {desc}", file=sys.stderr)


def render_reinstall_options() -> str:
    """Show re-install options and return user choice.

    Returns one of: 'fresh', 'repair', 'reconfigure', 'cancel'.
    """
    import click
    import click.exceptions
    import typer

    if _HAS_RICH and _console:
        _console.print("\n[bold yellow]Existing installation detected.[/]")
        _console.print(
            "  [cyan]fresh[/]       \u2014 Overwrite framework files (preserves team + state)"
        )
        _console.print("  [cyan]repair[/]      \u2014 Fill missing files without overwriting")
        _console.print("  [cyan]reconfigure[/] \u2014 Change providers/VCS/stacks")
        _console.print("  [cyan]cancel[/]      \u2014 Exit without changes")
    else:
        print("\nExisting installation detected.", file=sys.stderr)
        print(
            "  fresh       \u2014 Overwrite framework files (preserves team + state)",
            file=sys.stderr,
        )
        print("  repair      \u2014 Fill missing files without overwriting", file=sys.stderr)
        print("  reconfigure \u2014 Change providers/VCS/stacks", file=sys.stderr)
        print("  cancel      \u2014 Exit without changes", file=sys.stderr)

    try:
        choice = typer.prompt(
            "\nChoose action",
            default="repair",
            type=click.Choice(["fresh", "repair", "reconfigure", "cancel"]),
        )
        return str(choice)
    except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
        return "cancel"


def render_detection(vcs: str, providers: list[str], tools: dict[str, bool]) -> None:
    """Show auto-detection results."""
    if _HAS_RICH and _console:
        _console.print("\n[bold]Auto-detected configuration:[/]")
        _console.print(f"  VCS provider:  [cyan]{vcs}[/]")
        _console.print(f"  AI providers:  [cyan]{', '.join(providers)}[/]")
        tool_lines = []
        for name, available in tools.items():
            status = "[green]\u2713[/]" if available else "[yellow]\u2717[/]"
            tool_lines.append(f"{status} {name}")
        _console.print(f"  Tools:         {' | '.join(tool_lines)}")
    else:
        print("\nAuto-detected configuration:", file=sys.stderr)
        print(f"  VCS provider:  {vcs}", file=sys.stderr)
        print(f"  AI providers:  {', '.join(providers)}", file=sys.stderr)
        for name, available in tools.items():
            status = "\u2713" if available else "\u2717"
            print(f"  Tool: {status} {name}", file=sys.stderr)
