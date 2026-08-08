"""Everything a person reads, drawn in one place.

Before this, the ticks, the indents and the column widths were f-strings at forty-one call
sites in `init.py` and `doctor.py`, which is why the survey and the checklist did not line
up with each other. A verb asks here for a section, a step, a row, a panel or a question,
and never for a colour: the styles have names, the names live in one theme, and changing
how the product looks is this file.

Two consoles, because they are two streams. Messaging — questions, progress, the closing
panel — goes to stderr, so `ai-eng doctor > report.txt` yields a report rather than a
report with the chrome still attached. Data — the assertion lines, the coverage table, the
block of YAML you are meant to paste — goes to stdout, because that is what a person
redirects and what another program reads.

Styling is off unless the terminal asked for it: NO_COLOR, TERM=dumb and a stream that is
not a terminal each turn it off, which is what keeps a CI transcript diffable and what the
suite drives, so every assertion in it holds the bytes a person with no colour sees.
"""

from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from ai_engineering import __version__

# Taken from the project's own banner rather than chosen here, so the terminal and the
# README are the same product.
BRAND = "#00D4AA"

THEME = Theme(
    {
        "brand": f"bold {BRAND}",
        "ok": "green",
        "warn": "yellow",
        "fail": "bold red",
        "unknown": "yellow",
        "muted": "dim",
        "path": BRAND,
        "cmd": "cyan",
        "head": "bold",
    }
)

# ✓ happened · · would happen · ⚠ happened and wants a person · ✗ did not happen
MARKS = {"ok": ("✓", "ok"), "would": ("·", "muted"), "warn": ("⚠", "warn"), "fail": ("✗", "fail")}

_consoles: dict[bool, Console] = {}


def plain() -> bool:
    """The three ways a terminal says it does not want to be decorated. Checked here rather
    than left to the library, because `questionary` is a second library with its own idea
    and the answer has to be one answer."""
    return "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb"


def console(data: bool = False) -> Console:
    """stdout for data, stderr for everything a person reads on the way past."""
    if data not in _consoles:
        _consoles[data] = Console(
            file=sys.stdout if data else sys.stderr,
            theme=THEME,
            # None and not no_color=True: no_color drops the colours and keeps bold and
            # dim, so a terminal that asked for nothing still receives escape sequences.
            color_system=None if plain() else "auto",
            highlight=False,
            markup=False,
            emoji=False,
        )
    return _consoles[data]


def reset() -> None:
    """Drop the cached consoles. The suite calls this after it has redirected a stream —
    a Console holds the file object it was built with, so a cached one writes past capsys."""
    _consoles.clear()


def write(text: str = "", style: str = "", data: bool = False) -> None:
    """One line, never wrapped. Nothing here has ever wrapped and a path that suddenly
    folds at column 80 is a path nobody can copy."""
    console(data).print(Text(text, style=style) if style else Text(text), soft_wrap=True)


def banner() -> None:
    """Four lines, the only moment the product has a face. On a terminal only, so it never
    lands in a log or a CI transcript — and asked of the console rather than of the stream,
    because two places deciding what a terminal is will eventually disagree."""
    out = console()
    if not out.is_terminal:
        return
    out.print(Text("\n  ┌─                    ─┐", style="brand"), soft_wrap=True)
    out.print(Text("    { ai } e n g i n e e r i n g", style="brand"), soft_wrap=True)
    out.print(Text("  └─                    ─┘", style="brand"), soft_wrap=True)
    out.print(Text(f"   v{__version__} · AI Governance Framework\n", style="muted"), soft_wrap=True)


def section(title: str, data: bool = False) -> None:
    """A blank line and a heading. Every family gets exactly one."""
    console(data).print(Text(f"\n{title}", style="head"), soft_wrap=True)


def step(state: str, name: str, detail: str = "") -> None:
    """`✓ CLAUDE.md written (one line: @./AGENTS.md)` — the mark carries the state, so the
    reader's eye finds the two warnings among the eleven ticks without reading any of it."""
    glyph, style = MARKS[state]
    line = Text("   ")
    line.append(glyph, style=style)
    line.append(f" {name}")
    if detail:
        line.append(f" {detail}", style="muted" if state == "would" else "")
    console().print(line, soft_wrap=True)


def note(text: str, style: str = "muted") -> None:
    """A continuation under the step it belongs to, indented past the mark."""
    for row in text.splitlines():
        console().print(Text(f"     {row}", style=style), soft_wrap=True)


def survey(rows: list[tuple[str, str, str, str]]) -> None:
    """One row per surface: the name, the path that proves it, and the verdict. Aligned by
    a table rather than by three format widths that drifted apart."""
    table = Table.grid(padding=(0, 2))
    table.add_column(width=18)
    table.add_column(width=26, style="path")
    table.add_column()
    for name, path, mark, style in rows:
        table.add_row(Text(f"   {name}"), Text(path), Text(mark, style=style))
    console().print(table)


def block(text: str, data: bool = True) -> None:
    """Verbatim, unstyled, unwrapped — a block of YAML somebody is going to paste. Markup is
    off across this module for exactly this line: rich would read `[push, pull_request]` as
    a style tag and print neither the brackets nor the words."""
    for row in text.splitlines():
        console(data).print(Text(row), soft_wrap=True)


def report(headline: str, waiting: list[str], nexts: list[tuple[str, str]]) -> None:
    """The last screen. What happened, what is still on a person, and what to run next."""
    body = Text()
    body.append(headline, style="head")
    for item in waiting:
        body.append("\n")
        body.append("⚠ still on you: ", style="warn")
        body.append(item)
    body.append("\n\nNext:", style="head")
    for index, (command, why) in enumerate(nexts, 1):
        body.append(f"\n  {index}. ")
        body.append(command, style="cmd")
        body.append(f"\n     {why}", style="muted")
    console().print(Panel(body, title="Done", border_style=BRAND, title_align="left"))


def ask(question: str, default: bool) -> bool:
    """A yes or no, with the answer Enter gives shown in capitals. The caller decides
    whether there is a person to ask; this only draws it."""
    reply = input(f"◆ {question} ({'Y/n' if default else 'y/N'}) › ").strip().lower()
    return default if not reply else reply.startswith("y")


def pick(question: str, rows: list[tuple[str, str]], checked: set[str]) -> list[str] | None:
    """A checkbox over rows, pre-ticked where the caller already knows the answer. Returns
    None when the person interrupted, which is not the same as choosing nothing.

    questionary is imported here and not at the top: it pulls prompt_toolkit, and a run with
    -y or no terminal must not pay for a widget it will never draw."""
    import questionary

    answer = questionary.checkbox(
        question,
        choices=[
            questionary.Choice(title=f"{key:<18} {detail}", value=key, checked=key in checked)
            for key, detail in rows
        ],
        instruction="(space to toggle, enter to confirm)",
    ).ask()
    return answer
