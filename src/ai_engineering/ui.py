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

import json
import os
import sys
from collections.abc import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

from ai_engineering import __version__
from ai_engineering.outcome import Result

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
RESULT_MARKS = {
    "READY": ("◇", "brand"),
    "PASS": ("✓", "ok"),
    "WARN": ("⚠", "warn"),
    "FAIL": ("✗", "fail"),
    "INCOMPLETE": ("?", "unknown"),
    "CANCELLED": ("■", "muted"),
    "WOULD_CHANGE": ("·", "muted"),
}

_consoles: dict[bool, Console] = {}


def plain(stream=None) -> bool:
    """The three ways a terminal says it does not want to be decorated. Checked here rather
    than left to the library, because `questionary` is a second library with its own idea
    and the answer has to be one answer."""
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return True
    stream = stream or sys.stderr
    forced = os.environ.get("FORCE_COLOR") not in (None, "", "0")
    is_terminal = getattr(stream, "isatty", lambda: False)
    return not forced and not is_terminal()


def console(data: bool = False) -> Console:
    """stdout for data, stderr for everything a person reads on the way past."""
    if data not in _consoles:
        stream = sys.stdout if data else sys.stderr
        _consoles[data] = Console(
            file=stream,
            theme=THEME,
            # None and not no_color=True: no_color drops the colours and keeps bold and
            # dim, so a terminal that asked for nothing still receives escape sequences.
            color_system=None if plain(stream) else "auto",
            highlight=False,
            markup=False,
            emoji=False,
            # Never wrapped, and set once here rather than argued at every print: nothing
            # this CLI writes has ever folded, and rich folds at column 80 off a pipe, so
            # a path would break in the middle on exactly the runs that get pasted into a
            # bug report. A Panel still sizes itself; this only governs plain text.
            soft_wrap=True,
        )
    return _consoles[data]


def reset() -> None:
    """Drop the cached consoles. The suite calls this after it has redirected a stream —
    a Console holds the file object it was built with, so a cached one writes past capsys."""
    _consoles.clear()


def write(text: str = "", style: str = "", data: bool = False) -> None:
    """One line, never wrapped. Nothing here has ever wrapped and a path that suddenly
    folds at column 80 is a path nobody can copy."""
    console(data).print(Text(text, style=style) if style else Text(text))


def render_result(result: Result, *, json_mode: bool = False) -> dict[str, str | int]:
    """Render one canonical result without changing its semantics or asking a question."""
    payload = result.as_dict()
    if json_mode:
        sys.stdout.write(
            json.dumps(
                payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            )
            + "\n"
        )
        return payload

    mark, style = RESULT_MARKS[result.outcome]
    body = Text(f"{mark} {result.outcome}", style=style)
    for label, value in (
        ("Reason", result.reason),
        ("Next action", result.next_action),
        ("Exit code", str(result.exit_code)),
    ):
        body.append("\n")
        body.append(f"{label}: ", style="head")
        body.append(value)
    console(data=True).print(body)
    return payload


WORDMARK = "{ ai } e n g i n e e r i n g"


def banner() -> None:
    """Four lines, the only moment the product has a face. On a terminal only, so it never
    lands in a log or a CI transcript — and asked of the console rather than of the stream,
    because two places deciding what a terminal is will eventually disagree.

    The frame is measured from the two lines it frames rather than typed out. Typed out it
    was twenty-six columns around a thirty-two column wordmark: corners that enclosed
    nothing, printed at the top of every run for as long as the drawing has existed. A
    drawing fails only by being looked at, nobody looks at a banner twice, and the test
    that pinned it pinned the mistake — so the width is arithmetic now, and a version that
    grows a digit moves the frame with it."""
    out = console()
    if not out.is_terminal:
        return
    tag = f"v{__version__} · AI Governance Framework"
    gap = " " * (max(len(WORDMARK), len(tag)) - 2)
    out.print(Text(f"\n  ┌─{gap}─┐", style="brand"))
    out.print(Text(f"    {WORDMARK}", style="brand"))
    out.print(Text(f"  └─{gap}─┘", style="brand"))
    out.print(Text(f"    {tag}\n", style="muted"))


def section(title: str, data: bool = False) -> None:
    """A blank line and a heading. Every family gets exactly one."""
    console(data).print(Text(f"\n{title}", style="head"))


def step(state: str, name: str, detail: str = "") -> None:
    """`✓ CLAUDE.md written (one line: @./AGENTS.md)` — the mark carries the state, so the
    reader's eye finds the two warnings among the eleven ticks without reading any of it."""
    glyph, style = MARKS[state]
    line = Text("   ")
    line.append(glyph, style=style)
    line.append(f" {name}")
    if detail:
        line.append(f" {detail}", style="muted" if state == "would" else "")
    console().print(line)


VERDICTS = {
    "ok": ("ok      ", "ok"),
    "fail": ("FAIL    ", "fail"),
    "unknown": ("?       ", "unknown"),
    "skipped": ("SKIPPED ", "muted"),
}


def verdict(number: int, state: str, title: str, detail: str = "") -> None:
    """One of doctor's twenty-two lines. The state carries the colour, so the failures in a run
    stop being typographically identical to the passes — which is the whole reason a person
    runs the command."""
    word, style = VERDICTS[state]
    line = Text(f"  {number:>2}  ")
    line.append(word, style=style)
    line.append(f" {title}")
    console(data=True).print(line)
    if detail:
        console(data=True).print(Text(f"      {detail}", style="muted"))


CURABLE = ("FAIL", "INCOMPLETE")
# A cure is an instruction to a person under a result that blocked them. These are the ways
# a "cure" stops being a repair and becomes a way around the thing that blocked, which is
# the one sentence this product may never print.
BYPASS_WORDS = ("--no-verify", "--force", "bypass", "exception --skip", "skip the", "ignore the")


def will(
    action: str,
    reads: Sequence[str],
    writes: Sequence[str],
    network: Sequence[str],
) -> None:
    """What this command is about to do, before it does any of it.

    Printed ahead of the first mutation, not after it. A person who reads this and stops has
    lost nothing; the same words printed afterwards are a description of something they
    were never given the chance to refuse.
    """

    console().print(Text("\n  will  ", style="head").append(action, style=""))
    for label, values in (("reads", reads), ("writes", writes), ("network", network)):
        line = Text(f"        {label:<8}")
        line.append(", ".join(values) if values else "none", style="muted" if not values else "")
        console().print(line)


def running(index: int, total: int, name: str) -> None:
    """`RUNNING 2/5  the thing being done` — counted, and counted honestly.

    `n` is the number of steps the caller declared it would run, so a progress line that
    reaches 5/5 means five things happened. An index past the total, or a total below one,
    is a caller whose count is a decoration; that raises here rather than printing a number
    nobody should trust.
    """

    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        raise ValueError("a counted step needs a real total")
    if not isinstance(index, int) or isinstance(index, bool) or not 1 <= index <= total:
        raise ValueError(f"step {index} is outside a run of {total}")
    line = Text("  RUNNING ", style="head")
    line.append(f"{index}/{total}", style="")
    line.append(f"  {name}")
    console().print(line)


def cure(status: str, command: str) -> None:
    """Under a failure, the exact thing to type — or the sentence that says nothing can be
    typed. Four of the twenty checks named their cure inside their prose and sixteen named
    nothing, so a reader had to work out for themselves which failures were theirs to fix by
    hand and which were one command away. That is now a column and not a guess.

    It renders only under a result that actually blocked. A cure offered beside a `PASS`
    tells a person to repair something that is not broken, and a cure that names a way past
    the gate is not a cure at all — both raise rather than print.
    """

    if status not in CURABLE:
        raise ValueError(f"a cure belongs under {' or '.join(CURABLE)}, not {status}")
    lowered = command.lower()
    if any(word in lowered for word in BYPASS_WORDS):
        raise ValueError("a cure may not name a way around the thing that blocked")
    line = Text("      ")
    if command:
        line.append("fix: ", style="head")
        line.append(command, style="cmd")
    else:
        line.append("you: ", style="head")
        # Not "the line above says what to do". Four of these failures name their remedy in
        # prose and the rest only name the problem, so a line promising an instruction that
        # is not there sends the reader back up the screen to look for it.
        line.append("a person does this one; no ai-eng command repairs it", style="muted")
    console(data=True).print(line)


def summary(title: str, rows: list[tuple[str, str]], style: str) -> None:
    """The verdict, in the same frame as `init`'s last screen. It was a bare line under the
    coverage block before, in the same weight as the eight rows above it, and it was read
    as more of the table — a person who had just run twenty-two checks could not say
    whether they had passed. A frame is not decoration when it is the answer."""
    body = Text()
    for index, (label, detail) in enumerate(rows):
        if index:
            body.append("\n")
        if label:
            body.append(f"{label:<16}", style="head")
        body.append(detail)
    console(data=True).print()
    console(data=True).print(Panel(body, title=title, border_style=style, title_align="left"))


def pair(key: str, text: str, data: bool = True) -> None:
    """A name and what it does, on one line: the ten verbs, and anything else shaped the
    same. The key carries the brand style, because it is the part you are going to type."""
    line = Text()
    line.append(key, style="brand")
    line.append(text)
    console(data).print(line)


def note(text: str, style: str = "muted") -> None:
    """A continuation under the step it belongs to, indented past the mark."""
    for row in text.splitlines():
        console().print(Text(f"     {row}", style=style))


def survey(rows: list[tuple[str, str, str, str]]) -> None:
    """One row per surface: the name, the path that proves it is there, and the verdict.

    Widths, and not a `Table.grid`, which was the first attempt: rich pads the final column
    out to its own width, so every row ends in a run of spaces nobody can see and every
    whole-line assertion trips on. The widths live here, once, which was the only thing the
    table was buying — they were three format strings at three call sites that drifted."""
    for name, path, mark, style in rows:
        line = Text(f"   {name:<18} ")
        line.append(f"{path:<26} ", style="path")
        line.append(mark, style=style)
        console().print(line)


def facts(rows: list[tuple[str, str, str]]) -> None:
    """A name, a count and where it landed. What this shape replaced was a hundred-column
    sentence with four facts and a path folded into it, which is a line a person scans for
    the one number they came for and does not find. Widths live here, as everywhere else in
    this module, because four of them at a call site is how the last two screens drifted."""
    for name, value, detail in rows:
        line = Text(f"   {name:<10}{value:>3}  ")
        line.append(detail, style="path")
        console().print(line)


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

    # The key column is as wide as the widest key and no wider. It was a literal 18, which
    # every surface id fits inside and `.github/workflows/check.yml` does not — one row
    # overflowing a fixed column pushes its own detail out of line with every other row's.
    width = max(len(key) for key, _ in rows)
    answer = questionary.checkbox(
        question,
        choices=[
            questionary.Choice(title=f"{key:<{width}} {detail}", value=key, checked=key in checked)
            for key, detail in rows
        ],
        instruction="(space to toggle, enter to confirm)",
    ).ask()
    return answer
