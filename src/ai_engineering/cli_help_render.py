"""spec-183 D-183-06/07/08: functional colour-grouped root ``--help``.

The root ``ai-eng`` help lists ~23 commands. A single flat list gives an
operator no signal for *which* command solves their problem. This module
renders the top-level command list as titled, distinctly-coloured **panels**
(one bordered box per category) driven by one ``{command: category}`` map:

- **Essentials** (aurora mint, hero) — get it, keep it current, check it.
- **Lifecycle** (brand teal) — build/verify/ship the framework.
- **Governance** (soft blue) — specs, decisions, risk, audit, ownership.
- **Inspection** (soft violet) — read-only status/capacity/skill probes.
- **Maintenance** (muted slate) — repo/runtime/spec housekeeping.

Design intent (boxed panels, seam fixed): the boxes give the ai-engineering
surface its grouped "flow", but naive per-panel auto-sizing makes each panel
size its own name column — so descriptions never share a vertical seam. The
fix is a single GLOBAL name-column width applied to every panel's inner grid,
so all descriptions align across boxes (the seam fix is orthogonal to the
box decision). Each panel title carries the bold category colour + a faint
inline subtitle (only where it adds non-obvious info); Options is demoted to
a quiet slate panel last (commands are what an operator scans for).

The panel LABEL (text) is always the primary grouping signal; colour is
reinforcement only, never the sole indicator (accessibility gate S1). Any
unmapped visible command falls into a dim "Other" catch-all panel so a
forgotten mapping is visible noise, not a silent gap (R-183-03). Box-drawing
glyphs use ``ROUNDED`` on the colour/TTY path and fold to ``ASCII`` on the
NO_COLOR / piped path so it never crashes a Windows cp1252 stdout. Secondary
text uses explicit hex tokens (never Rich "dim", which fails WCAG 1.4.3).

Only the ROOT group is rendered this way (it is the sole ``SmartTyperGroup``);
subcommand ``--help`` screens keep Typer's native rendering (Non-Goal 1).
"""

from __future__ import annotations

import io
import re
import shutil
import sys
from typing import cast

import click
from rich.box import ASCII, ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ai_engineering import __version__
from ai_engineering.cli_ui import _is_no_color

# Brand teal — anchors the header + the Lifecycle band (matches the SVG banner).
BRAND_TEAL = "#00D4AA"

# Secondary-text tokens with EXPLICIT hex, never Rich "dim". Rich "dim" hard-
# blends ~50% toward the background (#6d728d ≈ 3.62:1 on the dark field), which
# fails WCAG 1.4.3 (4.5:1) for meaningful body text. These pass:
_MUTED = "#9AA5B1"  # slate, 6.83:1 — readable secondary (usage, options, quiet tier)
_FAINT = "#7F85A0"  # 4.69:1 — quietest tier that still passes (subtitles, tagline)

# Trailing grid-cell pad removal: two simple passes (no backtracking).
# 1) Strip trailing spaces/tabs. 2) Strip trailing ANSI resets at EOL.
def _strip_trailing_pad(text: str) -> str:
    # Pass 1: remove trailing spaces/tabs
    text = re.sub(r"[ \t]+$", "", text)
    # Pass 2: remove trailing ANSI reset sequences (if any remain after pass 1)
    text = re.sub(r"(\x1b\[[0-9;]*m)+$", "", text)
    return text

# Ordered so bands render Essentials → Lifecycle → Governance → Inspection →
# Maintenance, with the "Other" catch-all last. D-183-08 taxonomy.
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
# but in a terminal the band colour IS the grouping signal — a teal-only
# gradient reads as "all green". So: teal ANCHORS the brand (Lifecycle), and the
# other categories take distinct, restrained cool hues (soft pastels, so they
# never buzz on the dark field per DESIGN.md's anti-buzz principle). Teal → blue
# → violet → slate are well-separated on the wheel yet harmonious. Colour is
# reinforcement; the band LABEL remains the primary signal (a11y).
_CATEGORY_STYLE: dict[str, str] = {
    "Essentials": "bold #7EF7DE",  # Aurora Mint (brightest/hero) + bold — start here
    "Lifecycle": "#00D4AA",  # Terminal Teal — the brand signal
    "Governance": "#7AA2F7",  # soft blue — authority / rules
    "Inspection": "#BB9AF7",  # soft violet — read-only insight
    "Maintenance": "#9AA5B1",  # muted slate — quiet housekeeping
    "Other": "#9AA5B1",  # muted slate
}

# One-line navigational subtitle — only where it carries NON-obvious info
# (which commands live in the group / their nature). Maintenance and Options
# are deliberately bare: "housekeeping"/"flags" just restate the label (garnish).
# `·` separators render only on the colour path (ASCII-folded to commas
# when NO_COLOR).
_CATEGORY_SUBTITLE: dict[str, str] = {
    "Essentials": "start here",
    "Lifecycle": "build · verify · ship",
    "Governance": "specs · decisions · risk · audit",
    "Inspection": "read-only probes",
    "Other": "uncategorised",
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


def _visible_commands(group: click.Group, ctx: click.Context, limit: int) -> list[tuple[str, str]]:
    """Return ``(name, short_help)`` for every non-hidden child command.

    ``limit`` caps the short-help length; the caller sizes it to the render
    width so descriptions fill the available space before truncating.
    """
    out: list[tuple[str, str]] = []
    for name in group.list_commands(ctx):
        cmd = group.get_command(ctx, name)
        if cmd is None or getattr(cmd, "hidden", False):
            continue
        out.append((name, cmd.get_short_help_str(limit=limit)))
    return out


def _bold(style: str) -> str:
    """Bold variant of a colour style (idempotent if already bold)."""
    return style if "bold" in style else f"bold {style}"


def _print_brand_header(console: Console, no_color: bool) -> None:
    """Print the branded logo: corner-bracket banner + version + tagline.

    Mirrors ``cli_ui.show_logo`` (which itself mirrors the SVG banner
    ``.github/assets/banner-dark.svg``): corner brackets, ``{ai}`` mark with
    teal braces, letter-spaced engineering text. Shown on both bare ``ai-eng``
    and ``ai-eng --help`` (single source of branding for the root surface).
    ASCII on the NO_COLOR / piped path. The corner brackets are decorative
    chrome (WCAG 1.4.3 exempt); the tagline uses ``_FAINT`` so it still passes.
    """
    ver = f"v{__version__}"
    if no_color:
        console.print()
        console.print("  +--                                  --+")
        console.print("      { ai }   e n g i n e e r i n g")
        console.print("  +--                                  --+")
        console.print(f"  {ver} - AI Governance Framework")
        console.print()
        return
    console.print()
    console.print(Text("  \u250c\u2500" + " " * 34 + "\u2500\u2510", style="dim #00D4AA"))
    console.print(
        Text.assemble(
            ("      { ", f"bold {BRAND_TEAL}"),
            ("ai", "bold white"),
            (" }", f"bold {BRAND_TEAL}"),
            ("   e n g i n e e r i n g", f"bold {BRAND_TEAL}"),
        )
    )
    console.print(Text("  \u2514\u2500" + " " * 34 + "\u2500\u2518", style="dim #00D4AA"))
    console.print(Text(f"  {ver} \u00b7 AI Governance Framework", style=_FAINT))
    console.print()


def render_root_help(ctx: click.Context) -> str:
    """Render the root help as colour-grouped, bordered command panels.

    Returns a ready-to-echo string. Fails loud to the caller (raises) so the
    ``get_help`` override can fall back to Typer's default rendering.
    """
    group = cast(click.Group, ctx.command)
    no_color = _should_disable_color()
    width = 80 if no_color else max(40, min(shutil.get_terminal_size((80, 24)).columns, 100))
    console = Console(
        file=io.StringIO(),
        record=True,
        width=width,
        color_system=None if no_color else "truecolor",
        highlight=False,
        emoji=False,
    )

    _print_brand_header(console, no_color)

    console.print(
        Text.assemble(
            ("Usage  ", "bold"),
            (f"{ctx.command_path} [OPTIONS] COMMAND [ARGS]...", _MUTED),
        )
    )
    if group.help:
        console.print()
        console.print(f"  {group.help.strip()}")
    console.print()

    names = [n for n, _ in _visible_commands(group, ctx, limit=1)]
    name_w = max((len(n) for n in names), default=8)
    help_limit = max(8, width - (2 + name_w + 2) - 1)
    visible = _visible_commands(group, ctx, limit=help_limit)

    _render_command_panels(console, visible, name_w, no_color)
    _render_options_panel(console, group, ctx, no_color)
    _render_footer(console, ctx, group, no_color)

    text = console.export_text(styles=not no_color)
    return "\n".join(_strip_trailing_pad(ln) for ln in text.splitlines()) + "\n"


def _render_command_panels(
    console: Console,
    visible: list[tuple[str, str]],
    name_w: int,
    no_color: bool,
) -> None:
    """Render all command category panels."""
    grouped: dict[str, list[tuple[str, str]]] = {cat: [] for cat in CATEGORY_ORDER}
    for name, short_help in visible:
        grouped[categorize(name)].append((name, short_help))

    box = ASCII if no_color else ROUNDED
    for category in CATEGORY_ORDER:
        rows = grouped[category]
        if not rows:
            continue
        _render_single_category_panel(console, category, rows, name_w, box, no_color)


def _render_single_category_panel(
    console: Console,
    category: str,
    rows: list[tuple[str, str]],
    name_w: int,
    box: type,
    no_color: bool,
) -> None:
    """Render a single category panel."""
    style = _CATEGORY_STYLE[category]
    table = Table.grid()
    table.add_column(width=2 + name_w + 2, no_wrap=True, style=style)
    desc_style = _MUTED if category == "Maintenance" else None
    table.add_column(overflow="fold", style=desc_style)
    for name, short_help in rows:
        table.add_row(f"  {name}", short_help)
    sub = _CATEGORY_SUBTITLE.get(category, "")
    sub_display = sub.replace(" \u00b7 ", ", ") if no_color else sub
    title = Text.assemble(
        (category, _bold(style)),
        (f"   {sub_display}" if sub_display else "", _FAINT),
    )
    console.print(
        Panel(
            table,
            title=title,
            title_align="left",
            border_style=style,
            box=box,
            padding=(1, 1),
        )
    )
    console.print()


def _render_options_panel(
    console: Console,
    group: click.Group,
    ctx: click.Context,
    no_color: bool,
) -> None:
    """Render the Options panel."""
    option_records = [p.get_help_record(ctx) for p in group.get_params(ctx)]
    option_rows = [rec for rec in option_records if rec]
    if not option_rows:
        return

    box = ASCII if no_color else ROUNDED
    opts = Table.grid(padding=(0, 2))
    opts.add_column(no_wrap=True, style=_MUTED)
    opts.add_column(overflow="fold", style=_MUTED)
    for flag, help_text in option_rows:
        opts.add_row(f"  {flag}", help_text)
    console.print(
        Panel(
            opts,
            title=Text("Options", style=_bold(_MUTED)),
            title_align="left",
            border_style=_MUTED,
            box=box,
            padding=(1, 1),
        )
    )
    console.print()


def _render_footer(
    console: Console,
    ctx: click.Context,
    group: click.Group,
    no_color: bool,
) -> None:
    """Render the footer: drill-in hint and epilog."""
    console.print(
        Text.assemble(
            ("Run  ", _MUTED),
            (f"{ctx.command_path} COMMAND --help", BRAND_TEAL),
            ("  for details on a command.", _MUTED),
        )
    )
    if group.epilog:
        console.print(group.epilog)
