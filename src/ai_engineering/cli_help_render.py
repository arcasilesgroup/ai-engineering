"""spec-183 D-183-06/07/08: functional colour-grouped root ``--help``.

The root ``ai-eng`` help lists ~23 commands. A single flat panel gives an
operator no signal for *which* command solves their problem. This module
renders the top-level command list as four titled, distinctly-coloured
panels driven by one ``{command: category}`` map:

- **Lifecycle** (brand teal) — install/build/verify/ship the framework.
- **Governance** (violet) — specs, decisions, risk, audit, ownership.
- **Inspection** (info blue) — read-only status/capacity/skill probes.
- **Maintenance** (muted grey) — repo/runtime/spec housekeeping.

The panel TITLE (text) is always the primary grouping signal; colour is
reinforcement only, never the sole indicator (accessibility gate S1). Any
unmapped visible command falls into a dim "Other" catch-all panel so a
forgotten mapping is visible noise, not a silent gap (R-183-03).

Only the ROOT group is rendered this way (it is the sole ``SmartTyperGroup``);
subcommand ``--help`` screens keep Typer's native rendering (Non-Goal 1).
"""

from __future__ import annotations

import io
import shutil
import sys
from typing import cast

import click
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_engineering.cli_ui import _is_no_color

# Ordered so panels render Lifecycle → Governance → Inspection → Maintenance,
# with the "Other" catch-all last. D-183-08 taxonomy.
CATEGORY_ORDER: tuple[str, ...] = (
    "Essentials",
    "Lifecycle",
    "Governance",
    "Inspection",
    "Maintenance",
    "Other",
)

# The single source of truth mapping visible top-level commands → category.
# `release`, `dev`, `internal`, and the removed-verb tombstones are hidden and
# never reach this map (they are filtered out before categorisation).
COMMAND_CATEGORY: dict[str, str] = {
    # Essentials: what a new user reaches for first — get it, keep it current,
    # check it, know its version. Rendered first + brightest (see below).
    "install": "Essentials",
    "update": "Essentials",
    "doctor": "Essentials",
    "version": "Essentials",
    "check": "Lifecycle",
    "verify": "Lifecycle",
    "gate": "Lifecycle",
    "config": "Lifecycle",
    "setup": "Lifecycle",
    "commit": "Lifecycle",
    "pr": "Lifecycle",
    "spec": "Governance",
    "plan": "Governance",
    "decision": "Governance",
    "risk": "Governance",
    "issue": "Governance",
    "ownership": "Governance",
    "audit": "Governance",
    "status": "Inspection",
    "host": "Inspection",
    "skill": "Inspection",
    "maintenance": "Maintenance",
    "cleanup": "Maintenance",
}

# CLI-adapted category palette. The website DESIGN.md is strict one-hue (teal),
# but in a terminal the panel colour IS the grouping signal — a teal-only
# gradient reads as "all green". So: teal ANCHORS the brand (Lifecycle), and the
# other categories take distinct, restrained cool hues (soft pastels, so they
# never buzz on the dark field per DESIGN.md's anti-buzz principle). Teal → blue
# → violet → slate are well-separated on the wheel yet harmonious. Colour is
# reinforcement; the panel TITLE remains the primary signal (a11y).
_CATEGORY_STYLE: dict[str, str] = {
    "Essentials": "bold #7EF7DE",  # Aurora Mint (brightest/hero) + bold — start here
    "Lifecycle": "#00D4AA",  # Terminal Teal — the brand signal
    "Governance": "#7AA2F7",  # soft blue — authority / rules
    "Inspection": "#BB9AF7",  # soft violet — read-only insight
    "Maintenance": "#9AA5B1",  # muted slate — quiet housekeeping
    "Other": "#9AA5B1",  # muted slate
}


def categorize(name: str) -> str:
    """Return the category for a top-level command name ('Other' if unmapped)."""
    return COMMAND_CATEGORY.get(name, "Other")


def _should_disable_color() -> bool:
    """Colour off for NO_COLOR, TERM=dumb, or a non-TTY stdout (piped output)."""
    if _is_no_color():
        return True
    try:
        return not sys.stdout.isatty()
    except Exception:
        return True


def _visible_commands(group: click.Group, ctx: click.Context) -> list[tuple[str, str]]:
    """Return ``(name, short_help)`` for every non-hidden child command."""
    out: list[tuple[str, str]] = []
    for name in group.list_commands(ctx):
        cmd = group.get_command(ctx, name)
        if cmd is None or getattr(cmd, "hidden", False):
            continue
        out.append((name, cmd.get_short_help_str(limit=70)))
    return out


def render_root_help(ctx: click.Context) -> str:
    """Render the root help as four colour-grouped command panels.

    Returns a ready-to-echo string. Fails loud to the caller (raises) so the
    ``get_help`` override can fall back to Typer's default rendering.
    """
    # ctx.command is the root group. Use ``cast`` (compile-time only), NOT a
    # runtime ``isinstance(click.Group)`` — Typer's TyperGroup fails that check
    # on some Typer versions (>= 0.26) even though it exposes every attribute
    # used below, which previously raised and silently fell back to flat help.
    group = cast(click.Group, ctx.command)
    no_color = _should_disable_color()
    width = shutil.get_terminal_size((80, 24)).columns if not no_color else 80
    # file=StringIO: record only, never write live to stdout — the caller
    # (get_help) echoes the returned string exactly once.
    console = Console(
        file=io.StringIO(),
        record=True,
        width=width,
        color_system=None if no_color else "truecolor",
        highlight=False,
        emoji=False,
    )

    console.print(f"[b]Usage:[/b] {ctx.command_path} [OPTIONS] COMMAND [ARGS]...")
    if group.help:
        console.print()
        console.print(f" {group.help.strip()}")

    options = Table.grid(padding=(0, 2))
    options.add_column(no_wrap=True)
    options.add_column()
    for param in group.get_params(ctx):
        record = param.get_help_record(ctx)
        if record:
            options.add_row(*record)
    console.print(
        Panel(options, title="Options", title_align="left", border_style="dim", box=ROUNDED)
    )

    grouped: dict[str, list[tuple[str, str]]] = {cat: [] for cat in CATEGORY_ORDER}
    for name, short_help in _visible_commands(group, ctx):
        grouped[categorize(name)].append((name, short_help))

    for category in CATEGORY_ORDER:
        rows = grouped[category]
        if not rows:
            continue
        style = _CATEGORY_STYLE[category]
        table = Table.grid(padding=(0, 2))
        table.add_column(no_wrap=True, style=style)
        table.add_column()
        for name, short_help in rows:
            table.add_row(name, short_help)
        console.print(
            Panel(
                table,
                title=category,
                title_align="left",
                border_style=style,
                box=ROUNDED,
            )
        )

    if group.epilog:
        console.print(group.epilog)

    return console.export_text(styles=not no_color)
