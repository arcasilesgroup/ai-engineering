"""The renderer, pinned once per element so the verbs can stop pinning it each.

Every element is driven twice: undecorated, which is what a CI log and this whole suite
see, and decorated, which is what a person at a terminal sees. Only the first is asserted
byte for byte — the second is asserted to carry an escape sequence and the same words,
because pinning ANSI codes in a literal is how a test becomes unreadable and then unread.

The stream matters as much as the text. Messaging on stderr and data on stdout is a
decision in spec 006, and a decision nothing asserts is a decision that drifts back.
"""

from __future__ import annotations

import re
import sys
from types import SimpleNamespace

import pytest
from rich.style import Style

from ai_engineering import __version__, ui


@pytest.fixture
def coloured(monkeypatch):
    """A terminal that wants decoration. FORCE_COLOR is the convention for saying so past a
    pipe, and it is what a person debugging their own colours reaches for, so exercising
    the decorated path through it exercises a path users actually take."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("FORCE_COLOR", "1")
    ui.reset()
    yield
    ui.reset()


def test_messaging_goes_to_stderr_and_data_goes_to_stdout(capsys):
    """`ai-eng doctor > report.txt` has to yield the report and not the report with every
    line of chrome still attached. This is that split, at the only place that decides it."""
    ui.write("chrome")
    ui.write("payload", data=True)
    caught = capsys.readouterr()
    assert caught.err == "chrome\n"
    assert caught.out == "payload\n"


def test_a_line_is_never_wrapped_however_long_the_path(capsys):
    """Nothing this CLI prints has ever wrapped, and a path that folds at column 80 is a
    path nobody can copy out of a terminal. rich wraps at 80 by default off a pipe."""
    long = "/" + "very-long-directory/" * 12 + "settings.json"
    ui.write(long)
    assert capsys.readouterr().err == long + "\n"


@pytest.mark.parametrize(
    ("state", "glyph"), [("ok", "✓"), ("would", "·"), ("warn", "⚠"), ("fail", "✗")]
)
def test_every_step_state_has_its_own_mark(state, glyph, capsys):
    """Four states, four glyphs. Two states sharing one is a screen where the reader cannot
    find the thing that needs them."""
    ui.step(state, "CLAUDE.md", "(one line: @./AGENTS.md)")
    assert capsys.readouterr().err == f"   {glyph} CLAUDE.md (one line: @./AGENTS.md)\n"


def test_a_step_with_no_detail_does_not_trail_a_space(capsys):
    """Catches a trailing space, which no reader sees and every whole-screen assertion in
    this suite trips over."""
    ui.step("ok", "receipt")
    assert capsys.readouterr().err == "   ✓ receipt\n"


def test_a_section_opens_with_one_blank_line(capsys):
    ui.section("The wiring")
    assert capsys.readouterr().err == "\nThe wiring\n"


def test_a_note_sits_under_the_mark_it_belongs_to(capsys):
    """Two spaces past the step's indent, so a continuation reads as a continuation rather
    than as a second finding."""
    ui.note("Codex will not run it until you approve it.\n`doctor` reports it as INERT.")
    assert capsys.readouterr().err == (
        "     Codex will not run it until you approve it.\n     `doctor` reports it as INERT.\n"
    )


def test_the_survey_lines_its_three_columns_up(capsys):
    """The name, the path that proves the surface is there, and the verdict. This drifted
    out of alignment with the checklist because the two used different format widths."""
    ui.survey(
        [
            ("Claude Code", "~/.claude", "found", "ok"),
            ("VS Code Copilot", "—", "wired by name only", "muted"),
        ]
    )
    lines = capsys.readouterr().err.splitlines()
    assert lines[0].startswith("   Claude Code")
    assert lines[0].index("~/.claude") == lines[1].index("—")
    assert lines[0].index("found") == lines[1].index("wired by name only")
    # No row ends in whitespace. rich's grid pads the last column out to its own width,
    # which is invisible on screen and is a run of spaces in every log and every assertion.
    assert [line for line in lines if line != line.rstrip()] == []


def test_a_block_survives_square_brackets(capsys):
    """The CI block this installer prints contains `on: [push, pull_request]`. rich reads
    square brackets as style tags, so with markup left on it prints neither the brackets
    nor the two words inside them — and the line a person pastes is silently wrong."""
    ui.block("name: check\non: [push, pull_request]\n")
    assert capsys.readouterr().out == "name: check\non: [push, pull_request]\n"


def framed(text: str) -> list[str]:
    """Inside the panel's border, one entry per line. The box characters and the width are
    rich's and move with the terminal; the words are the product's."""
    return [row.strip("│").strip() for row in text.splitlines() if row.startswith("│")]


def test_the_report_names_what_happened_what_waits_and_what_to_run(capsys):
    """Every line of the panel, in order. Two `in` checks left most of it unheld, which is
    the same mistake this suite exists because of."""
    ui.report(
        "7 files written · 4 guard entries on this machine",
        ["install gitleaks, or every commit here is refused"],
        [
            ("ai-eng doctor", "every assertion, and the coverage line under it"),
            ("ai-eng spec new <slug>", "the first spec"),
        ],
    )
    text = capsys.readouterr().err
    # The title sits at the left corner and not centred, so the eye finds it where every
    # other heading on this screen is rather than in the middle of a rule.
    assert text.splitlines()[0].startswith("╭─ Done ─")
    assert framed(text) == [
        "7 files written · 4 guard entries on this machine",
        "⚠ still on you: install gitleaks, or every commit here is refused",
        "",
        "Next:",
        "1. ai-eng doctor",
        "every assertion, and the coverage line under it",
        "2. ai-eng spec new <slug>",
        "the first spec",
    ]


def test_a_report_with_nothing_waiting_has_no_warning_row(capsys):
    """Catches the warning block printing an empty row when the list is empty, which is a
    panel with a hole in it on the happy path — the path most people see."""
    ui.report("3 files written · 0 guard entries", [], [("ai-eng doctor", "the full check")])
    assert framed(capsys.readouterr().err) == [
        "3 files written · 0 guard entries",
        "",
        "Next:",
        "1. ai-eng doctor",
        "the full check",
    ]


@pytest.mark.parametrize(
    ("state", "word"),
    [("ok", "ok      "), ("fail", "FAIL    "), ("unknown", "?       "), ("skipped", "SKIPPED ")],
)
def test_every_verdict_state_has_its_own_word_in_its_own_column(state, word, capsys):
    """The number is right-aligned in two so 1 and 21 start the title at the same column,
    and the state word is padded so the titles line up under each other. Both drifted when
    they were four separate f-strings in doctor."""
    ui.verdict(7, state, "Liveness: the suite exercised every guard")
    assert capsys.readouterr().out == f"   7  {word} Liveness: the suite exercised every guard\n"


def test_a_verdict_with_a_reason_puts_it_under_the_title_and_not_beside_it(capsys):
    """The reason is the half a person acts on, and it is usually a sentence. Beside the
    title it wraps; under it, indented past the number, it reads."""
    ui.verdict(21, "fail", "Per-surface liveness", "Codex CLI: installed but INERT")
    assert capsys.readouterr().out == (
        "  21  FAIL     Per-surface liveness\n      Codex CLI: installed but INERT\n"
    )


def test_a_verdict_number_wider_than_two_still_lines_up(capsys):
    """Twenty-one assertions today. The alignment must not be a coincidence of the count."""
    ui.verdict(100, "ok", "t")
    assert capsys.readouterr().out == "  100  ok       t\n"


def test_a_pair_is_the_name_and_what_it_does_on_one_line(capsys):
    """The ten verbs, and anything shaped like them. This had no test at all: fifteen
    mutants of it lived, which is every character of the only help screen there is."""
    ui.pair("  init      ", "Set up this machine.")
    assert capsys.readouterr().out == "  init      Set up this machine.\n"


def bare(text: str) -> str:
    """The words, with the escape sequences taken off. Asserting the codes themselves pins
    which colour rich picked; asserting the words pins what the product says."""
    return re.sub(r"\x1b\[[0-9;:]*m", "", text)


def test_the_banner_stays_off_a_pipe(capsys):
    """It costs four lines and exists for one moment. In a log it is noise."""
    ui.banner()
    assert capsys.readouterr().err == ""


def test_the_banner_is_these_four_lines_and_no_others(coloured, capsys):
    """Whole, because it is a drawing: a box whose corners stop matching, or a line that
    loses a space, is only ever caught by looking — and nobody looks at a banner twice."""
    ui.banner()
    assert bare(capsys.readouterr().err) == (
        "\n  ┌─                    ─┐\n"
        "    { ai } e n g i n e e r i n g\n"
        "  └─                    ─┘\n"
        f"   v{__version__} · AI Governance Framework\n\n"
    )


# ── decorated ───────────────────────────────────────────────────────────────────────


def dressed(name: str, word: str) -> str:
    """`word` as this theme renders it under the style called `name`. Derived from the
    theme rather than written out, so these tests say "the failure wears the failure
    style" instead of pinning whichever escape sequence rich picked for bold red."""
    return ui.THEME.styles[name].render(word)


@pytest.mark.parametrize(
    ("state", "glyph"), [("ok", "✓"), ("would", "·"), ("warn", "⚠"), ("fail", "✗")]
)
def test_each_step_mark_wears_the_style_that_belongs_to_its_state(state, glyph, coloured, capsys):
    """Undecorated, every state prints the same run of characters in the same places, so
    nothing in the plain suite can tell `ok` styled as a failure from `ok` styled at all.
    The colour is the whole point of the mark and it needs its own assertion."""
    ui.step(state, "CLAUDE.md")
    assert dressed(ui.MARKS[state][1], glyph) in capsys.readouterr().err


@pytest.mark.parametrize("state", ["ok", "fail", "unknown", "skipped"])
def test_each_verdict_word_wears_the_style_that_belongs_to_its_state(state, coloured, capsys):
    """Five failures among twenty-one passes is the reason a person runs doctor. If the
    state word is styled wrong — or not styled — that is the whole feature, silently gone."""
    word, style = ui.VERDICTS[state]
    ui.verdict(7, state, "a title")
    assert dressed(style, word) in capsys.readouterr().out


def test_the_banner_and_the_verb_names_wear_the_brand(coloured, capsys):
    """The brand colour is a product decision — it is taken from this project's own banner
    — and it is the one style that appears in two places, so it is the one most able to
    drift in one of them."""
    ui.banner()
    ui.pair("  init      ", "Set up this machine.")
    caught = capsys.readouterr()
    # Without the leading newline of the first line: rich emits that outside the style,
    # which is right — a blank line has no colour.
    for line in (
        "  ┌─                    ─┐",
        "    { ai } e n g i n e e r i n g",
        "  └─                    ─┘",
    ):
        assert dressed("brand", line) in caught.err, line
    assert dressed("muted", f"   v{__version__} · AI Governance Framework") in caught.err
    assert dressed("brand", "  init      ") in caught.out


def test_the_report_dresses_its_four_kinds_of_line(coloured, capsys):
    """A headline, a warning, a command and the sentence under it. Undecorated they are
    four runs of ordinary text and nothing can tell them apart, which is how the one that
    matters — the warning — could quietly stop looking like one."""
    ui.report("7 files written", ["install gitleaks"], [("ai-eng doctor", "the full check")])
    text = capsys.readouterr().err
    assert dressed("head", "7 files written") in text
    assert dressed("warn", "⚠ still on you: ") in text
    assert dressed("head", "Next:") in text
    assert dressed("cmd", "ai-eng doctor") in text
    assert dressed("muted", "     the full check") in text
    assert Style.parse(ui.BRAND).render("─ Done ─").split("─")[0] in text


def test_the_survey_dresses_the_path_and_the_verdict_separately(coloured, capsys):
    """Two columns, two meanings: the path is evidence and the mark is the conclusion. One
    style over both is a row where the eye cannot tell them apart."""
    ui.survey([("Claude Code", "~/.claude", "found", "ok")])
    text = capsys.readouterr().err
    assert dressed("path", "~/.claude                  ") in text
    assert dressed("ok", "found") in text


@pytest.mark.parametrize(
    "draw",
    [
        lambda long: ui.step("ok", long),
        lambda long: ui.verdict(1, "ok", long),
        lambda long: ui.pair("  init  ", long),
        lambda long: ui.note(long),
        lambda long: ui.survey([("Claude Code", "~/.claude", long, "ok")]),
    ],
    ids=["step", "verdict", "pair", "note", "survey"],
)
def test_no_element_folds_a_long_line_at_column_eighty(draw, capsys):
    """rich wraps at 80 off a pipe and every one of these can carry an absolute path. A
    folded path is a path nobody can copy, and it is invisible until the day it is long."""
    long = "/" + "very-long-directory/" * 8 + "settings.json"
    draw(long)
    caught = capsys.readouterr()
    assert long in (caught.err + caught.out)


def test_a_terminal_gets_colour_and_the_words_do_not_change(coloured, capsys):
    """The one assertion on the decorated path. It checks that styling happens at all and
    that it did not eat any of the text — not which escape sequence rich chose, because a
    literal full of those is a test nobody re-reads."""
    ui.step("fail", "CLAUDE.md", "(missing)")
    text = capsys.readouterr().err
    assert "\x1b[" in text
    assert "✗" in text and "CLAUDE.md" in text and "(missing)" in text


@pytest.mark.parametrize("switch", [("NO_COLOR", "1"), ("TERM", "dumb")])
def test_the_two_ways_a_terminal_says_it_wants_no_decoration(switch, monkeypatch, capsys):
    """NO_COLOR and TERM=dumb are the two conventions, and honouring one of them is
    honouring neither: whichever is unhandled is somebody's terminal full of escape codes."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")  # a terminal, so only the switch can quiet it
    monkeypatch.setenv(*switch)
    ui.reset()
    ui.step("fail", "CLAUDE.md")
    assert capsys.readouterr().err == "   ✗ CLAUDE.md\n"


# ── the question and the picker ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("reply", "default", "answer"),
    [("y", False, True), ("", True, True), ("", False, False), ("n", True, False)],
)
def test_the_yes_or_no_shows_which_answer_enter_gives(reply, default, answer, monkeypatch):
    """Catches the prompt losing the capital that tells a person what Enter does, and an
    Enter that stops meaning the safe default."""
    seen = []
    monkeypatch.setattr("builtins.input", lambda prompt="": seen.append(prompt) or reply)
    assert ui.ask("Set up?", default) is answer
    assert seen == [f"◆ Set up? ({'Y/n' if default else 'y/N'}) › "]


def test_the_picker_preselects_what_was_already_found(monkeypatch):
    """The rows the caller already knows about arrive ticked; nothing else does. A widget
    that pre-ticks everything is a widget whose default writes to eight surfaces."""
    seen = {}

    class Fake:
        def __init__(self, question, choices, instruction):
            seen["question"] = question
            seen["choices"] = choices

        def ask(self):
            return ["claude-code"]

    monkeypatch.setitem(sys.modules, "questionary", SimpleNamespace(checkbox=Fake, Choice=dict))
    picked = ui.pick("Which?", [("claude-code", "~/.claude"), ("zed", "—")], {"claude-code"})
    assert picked == ["claude-code"]
    assert [choice["checked"] for choice in seen["choices"]] == [True, False]
    assert [choice["value"] for choice in seen["choices"]] == ["claude-code", "zed"]


def test_an_interrupted_picker_returns_none_rather_than_an_empty_choice(monkeypatch):
    """questionary answers None on Ctrl-C, and None is not the same as "I chose nothing":
    one means write nothing and stop, the other means write nothing and carry on."""
    monkeypatch.setitem(
        sys.modules,
        "questionary",
        SimpleNamespace(checkbox=lambda *a, **k: SimpleNamespace(ask=lambda: None), Choice=dict),
    )
    assert ui.pick("Which?", [("claude-code", "~/.claude")], set()) is None
