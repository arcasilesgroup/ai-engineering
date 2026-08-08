"""The renderer, pinned once per element so the verbs can stop pinning it each.

Every element is driven twice: undecorated, which is what a CI log and this whole suite
see, and decorated, which is what a person at a terminal sees. Only the first is asserted
byte for byte — the second is asserted to carry an escape sequence and the same words,
because pinning ANSI codes in a literal is how a test becomes unreadable and then unread.

The stream matters as much as the text. Messaging on stderr and data on stdout is a
decision in spec 006, and a decision nothing asserts is a decision that drifts back.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

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


def test_a_block_survives_square_brackets(capsys):
    """The CI block this installer prints contains `on: [push, pull_request]`. rich reads
    square brackets as style tags, so with markup left on it prints neither the brackets
    nor the two words inside them — and the line a person pastes is silently wrong."""
    ui.block("name: check\non: [push, pull_request]\n")
    assert capsys.readouterr().out == "name: check\non: [push, pull_request]\n"


def test_the_report_names_what_happened_what_waits_and_what_to_run(capsys):
    ui.report(
        "7 files written · 4 guard entries on this machine",
        ["install gitleaks, or every commit here is refused"],
        [("ai-eng doctor", "every assertion, and the coverage line under it")],
    )
    text = capsys.readouterr().err
    assert "Done" in text
    assert "7 files written · 4 guard entries on this machine" in text
    assert "⚠ still on you: install gitleaks, or every commit here is refused" in text
    assert "1. ai-eng doctor" in text
    assert "every assertion, and the coverage line under it" in text


def test_the_banner_stays_off_a_pipe(capsys):
    """It costs four lines and exists for one moment. In a log it is noise."""
    ui.banner()
    assert capsys.readouterr().err == ""


def test_the_banner_names_the_product_and_this_version_on_a_terminal(coloured, capsys):
    ui.banner()
    text = capsys.readouterr().err
    assert "{ ai } e n g i n e e r i n g" in text
    assert f"v{__version__} · AI Governance Framework" in text


# ── decorated ───────────────────────────────────────────────────────────────────────


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
