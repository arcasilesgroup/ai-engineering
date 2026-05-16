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


def render_detection(vcs: str, providers: list[str], tools: dict[str, bool]) -> None:
    """Show auto-detection results.

    spec-109 D-109-08: the ``Tools`` line is qualified with ``(PATH check)``
    so the user understands that ``\u2713`` reflects only PATH availability;
    the install pipeline may still need to run a different mechanism (e.g.
    ``uv tool install``) regardless of the PATH state.
    """
    vcs_display = vcs or "none detected"
    if _HAS_RICH and _console:
        _console.print("\n[bold]Auto-detected configuration:[/]")
        _console.print(f"  VCS provider:  [cyan]{vcs_display}[/]")
        _console.print(f"  AI providers:  [cyan]{', '.join(providers)}[/]")
        tool_lines = []
        for name, available in tools.items():
            status = "[green]\u2713[/]" if available else "[yellow]\u2717[/]"
            tool_lines.append(f"{status} {name}")
        _console.print(f"  Tools (PATH):  {' | '.join(tool_lines)}")
        _console.print("  [dim](\u2713 means tool found on PATH)[/]")
    else:
        print("\nAuto-detected configuration:", file=sys.stderr)
        print(f"  VCS provider:  {vcs_display}", file=sys.stderr)
        print(f"  AI providers:  {', '.join(providers)}", file=sys.stderr)
        for name, available in tools.items():
            status = "\u2713" if available else "\u2717"
            print(f"  Tool (PATH): {status} {name}", file=sys.stderr)
