"""The renderer, pinned once per element so the verbs can stop pinning it each.

Every element is driven twice: undecorated, which is what a CI log and this whole suite
see, and decorated, which is what a person at a terminal sees. Only the first is asserted
byte for byte — the second is asserted to carry an escape sequence and the same words,
because pinning ANSI codes in a literal is how a test becomes unreadable and then unread.

The stream matters as much as the text. Messaging on stderr and data on stdout is a
decision in spec 006, and a decision nothing asserts is a decision that drifts back.
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from rich.style import Style

from ai_engineering import __version__, cli, outcome, ui


def test_ui_plain_rich_json_noninteractive_and_a11y_parity(monkeypatch, capsys):
    """One canonical Result has one reading order in every renderer. Colour may reinforce
    the outcome, but a textual status and mark must survive without it; machine output is
    exactly one object; and drawing a result can never ask an unattended caller anything."""
    result = outcome.result("INCOMPLETE")
    expected_lines = [
        "? INCOMPLETE",
        f"Reason: {result.reason}",
        f"Next action: {result.next_action}",
        "Exit code: 1",
    ]

    def prompt(*args, **kwargs):
        raise AssertionError("the non-interactive renderer prompted")

    monkeypatch.setattr("builtins.input", prompt)
    monkeypatch.setitem(sys.modules, "questionary", SimpleNamespace(checkbox=prompt))
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    ui.reset()
    assert not sys.stdout.isatty()
    assert ui.render_result(result) == result.as_dict()
    plain = capsys.readouterr()
    assert plain.err == ""
    assert "\x1b[" not in plain.out
    assert plain.out.splitlines() == expected_lines

    monkeypatch.setenv("FORCE_COLOR", "1")
    ui.reset()
    assert ui.render_result(result) == result.as_dict()
    rich = capsys.readouterr().out
    assert "\x1b[" in rich
    assert bare(rich) == plain.out

    for switch in (("NO_COLOR", "1"), ("TERM", "dumb")):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setenv(*switch)
        ui.reset()
        ui.render_result(result)
        quiet = capsys.readouterr().out
        assert quiet == plain.out
        assert "\x1b[" not in quiet


def test_cli_noninteractive_json_is_one_object_and_never_null(monkeypatch, capsys):
    """Global JSON is one dispatch mode, not prose with braces around it. Child output and
    prompts cannot leak, canonical Result/Execution are the only success boundaries, and an
    integer or exception stays non-green without exposing its private text."""
    verbs = (
        "init",
        "doctor",
        "update",
        "spec",
        "decide",
        "accept",
        "audit",
        "report",
        "exception",
        "uninstall",
    )
    assert tuple(cli.VERBS) == verbs
    assert "--adr" not in "\n".join(cli.VERBS.values())

    invoked = []
    behavior = {"main": None}

    def import_module(name):
        invoked.append(name)
        return SimpleNamespace(main=behavior["main"])

    events = []
    monkeypatch.setattr(cli.importlib, "import_module", import_module)
    monkeypatch.setattr(
        cli.paths,
        "load",
        lambda name: SimpleNamespace(emit=lambda *args, **kwargs: events.append((args, kwargs))),
    )

    for argv, command in (
        (["--json"], "ai-eng"),
        (["plan", "--json"], "invalid"),
        (["digest", "--json"], "invalid"),
        (["decide", "--adr", "--json"], "invalid"),
    ):
        assert cli.main(argv) == 2
        invalid = capsys.readouterr()
        assert invalid.err == "" and invalid.out.count("\n") == 1
        invalid_payload = json.loads(invalid.out)
        assert invalid_payload["command"] == command
        assert invalid_payload["error"]["code"] == "INVALID_CLI"
    assert invoked == []

    def successful(argv):
        assert argv == [] and not sys.stdin.isatty()
        print("child stdout must not leak")
        sys.stderr.write("\x1b[31mchild stderr must not leak\x1b[0m\n")
        return outcome.result("PASS")

    behavior["main"] = successful
    assert cli.main(["doctor", "--json"]) == 0
    rendered = capsys.readouterr()
    assert rendered.err == ""
    assert rendered.out.count("\n") == 1
    assert "child" not in rendered.out and "\x1b[" not in rendered.out
    payload = json.loads(rendered.out)
    # `schema` first, and it is new. The envelope carried a version number for a document
    # nobody could find — `policy/` had eight schemas and none for the one object every verb
    # prints — so a reader written against "version 1" had no way to check it was reading
    # the right kind of thing. The order is asserted rather than the set, because the first
    # field a human sees in a piped line should say what the line is.
    assert list(payload) == [
        "schema",
        "schema_version",
        "command",
        "operation_id",
        "started_at",
        "finished_at",
        "outcome",
        "summary",
        "changes",
        "checks",
        "remaining",
        "next_actions",
        "error",
    ]
    assert payload["schema"] == cli.ENVELOPE_SCHEMA
    assert payload["schema_version"] == "1" and payload["command"] == "doctor"
    assert uuid.UUID(payload["operation_id"]).version == 4
    assert payload["outcome"] == "PASS" and payload["summary"] == outcome.result("PASS").reason
    assert payload["changes"] == payload["checks"] == payload["remaining"] == []
    assert payload["next_actions"] == [outcome.result("PASS").next_action]
    assert payload["error"] is None
    for field in ("started_at", "finished_at"):
        assert payload[field].endswith("Z")
        datetime.fromisoformat(payload[field].removesuffix("Z") + "+00:00")

    behavior["main"] = lambda argv: outcome.result("FAIL")
    assert cli.main(["--json", "audit"]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["outcome"] == "FAIL" and failed["remaining"] == []
    assert failed["error"] == {
        "code": "FAIL",
        "message": outcome.result("FAIL").reason,
        "retryable": True,
        "cure": outcome.result("FAIL").next_action,
    }

    behavior["main"] = lambda argv: 0
    assert cli.main(["spec", "--json"]) == 1
    undecidable = json.loads(capsys.readouterr().out)
    assert undecidable["outcome"] == "INCOMPLETE"
    assert undecidable["error"]["code"] == "NONCANONICAL_RESULT"

    def prompts(argv):
        input("private prompt must not leak")

    behavior["main"] = prompts
    assert cli.main(["--json", "init"]) == 1
    crashed = capsys.readouterr()
    assert crashed.err == "" and "private prompt" not in crashed.out
    unexpected = json.loads(crashed.out)
    assert unexpected["outcome"] == "INCOMPLETE"
    assert unexpected["error"]["code"] == "UNEXPECTED_ERROR"
    assert all(value is not None for key, value in unexpected.items() if key != "error")
    assert invoked == [
        "ai_engineering.doctor",
        "ai_engineering.audit",
        "ai_engineering.spec",
        "ai_engineering.init",
    ]


@pytest.mark.parametrize(
    ("status", "mark"),
    [
        ("READY", "◇"),
        ("PASS", "✓"),
        ("WARN", "⚠"),
        ("FAIL", "✗"),
        ("INCOMPLETE", "?"),
        ("CANCELLED", "■"),
        ("WOULD_CHANGE", "·"),
    ],
)
def test_every_canonical_result_keeps_its_status_in_text_and_a_mark(status, mark, capsys):
    """No terminal outcome may exist only as a colour. The closed vocabulary is written
    here so deleting a mapping cannot also delete the only test that knew it existed."""
    ui.render_result(outcome.result(status))
    assert capsys.readouterr().out.splitlines()[0] == f"{mark} {status}"
    assert set(ui.RESULT_MARKS) == {
        "READY",
        "PASS",
        "WARN",
        "FAIL",
        "INCOMPLETE",
        "CANCELLED",
        "WOULD_CHANGE",
    }


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


def test_a_line_survives_square_brackets(capsys):
    """rich reads square brackets as style tags, so with markup left on, a line reading
    `on: [push, pull_request]` prints neither the brackets nor the two words inside them.
    `doctor` prints paths, commands and reasons — including from CI files written to disk —
    and any of them can carry a bracket, so markup stays off on data lines."""
    ui.write("core.hooksPath → [managed]", data=True)
    assert capsys.readouterr().out == "core.hooksPath → [managed]\n"


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


@pytest.mark.parametrize(
    ("command", "line"),
    [
        ("ai-eng init --project", "      fix: ai-eng init --project\n"),
        ("", "      you: a person does this one; no ai-eng command repairs it\n"),
    ],
    ids=["a command exists", "no command exists"],
)
def test_a_cure_is_indented_under_its_reason_and_says_so_when_there_is_none(command, line, capsys):
    """Six spaces, so it sits under the reason rather than under the title: it is the third
    thing read, after what failed and why. The empty string is not the absence of this line
    — a failure with nothing under it reads as a failure somebody forgot to finish."""
    ui.cure("FAIL", command)
    assert capsys.readouterr().out == line


def test_the_summary_frames_the_verdict_and_lines_its_labels_up(capsys):
    """A row with no label is the count, and the labels under it are a column so the two
    numbers can be compared by eye. Inside the frame, in order, because a panel matched by
    one fragment is a panel most of which nothing holds."""
    ui.summary("FAILED", [("", "16 passed"), ("needs a person", "3   assertions 5, 9, 21")], "red")
    text = capsys.readouterr().out
    assert text.startswith("\n╭─ FAILED ─")
    assert framed(text) == ["16 passed", "needs a person  3   assertions 5, 9, 21"]


def test_a_facts_row_is_a_name_a_count_and_where_it_landed(capsys):
    """The count is right-aligned so three of them read as a column, and a row with no count
    still lines its path up with the rest. This replaced a hundred-column sentence with four
    facts folded into it, so the alignment is the entire point of the shape."""
    ui.facts([("skills", "8", "/x/skills"), ("receipt", "", "/x/machine.json")])
    assert capsys.readouterr().err == (
        "   skills      8  /x/skills\n   receipt        /x/machine.json\n"
    )


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
        "\n  ┌─                              ─┐\n"
        "    { ai } e n g i n e e r i n g\n"
        "  └─                              ─┘\n"
        f"    v{__version__} · AI Governance Framework\n\n"
    )


def test_the_banner_frame_encloses_what_it_frames(coloured, capsys):
    """The assertion the drawing never had. It shipped twenty-six columns of frame around a
    thirty-two column wordmark — corners enclosing nothing — and the test above pinned that
    byte for byte without noticing, because bytes are not a shape. A release whose version
    grows a digit widens the last line, so the frame is asserted against what it contains
    rather than against a number written here."""
    ui.banner()
    top, word, bottom, tag = bare(capsys.readouterr().err).strip("\n").splitlines()
    assert top == bottom.replace("└", "┌").replace("┘", "┐")
    assert len(top) == max(len(word), len(tag))
    assert top.index("┌") < word.index("{")


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
    # Taken from what was printed rather than typed out again. Without the leading newline
    # of the first line: rich emits that outside the style, which is right — a blank line
    # has no colour. The frame widens itself, so a copy of it written here would be a
    # second place for the drawing to live and the one that goes stale.
    *frame, tag = bare(caught.err).strip("\n").splitlines()
    for line in frame:
        assert dressed("brand", line) in caught.err, line
    assert dressed("muted", tag) in caught.err
    assert tag.endswith(f"v{__version__} · AI Governance Framework")
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


def test_the_cure_dresses_the_command_and_refuses_to_dress_the_absence_of_one(coloured, capsys):
    """A failure one command repairs and a failure a person repairs are the same run of
    characters undecorated, and the difference is the only thing a reader wants from the
    line. The command wears what verb names wear, because it is the part you are about to
    type; the sentence saying there is no command must not, because there is nothing there
    to copy."""
    ui.cure("FAIL", "ai-eng init --global")
    ui.cure("INCOMPLETE", "")
    caught = capsys.readouterr().out
    assert dressed("head", "fix: ") in caught
    assert dressed("cmd", "ai-eng init --global") in caught
    assert dressed("head", "you: ") in caught
    assert dressed("muted", "a person does this one; no ai-eng command repairs it") in caught


@pytest.mark.parametrize(
    ("title", "colour"), [("FAILED", "red"), ("OK", "#00D4AA")], ids=["failed", "passed"]
)
def test_the_verdict_frame_is_red_only_when_something_actually_failed(
    title, colour, coloured, capsys
):
    """The frame is the answer to the question the command was run to ask, so its colour is
    the answer too. Undecorated both verdicts are a box, and a box that is the wrong colour
    for its contents is worse than no box: it is read before the words inside it."""
    ui.summary(title, [("", "16 passed"), ("fixable now", "2   ai-eng doctor --fix")], colour)
    text = capsys.readouterr().out
    assert dressed("head", "fixable now     ") in text
    assert Style.parse(colour).render(f"─ {title} ─").split("─")[0] in text


def test_the_facts_block_dresses_the_path_and_leaves_the_count_alone(coloured, capsys):
    """The path is the part somebody copies into a shell, and it is the only part of the
    row that is not prose. It carries the same style as every other path this product
    prints, which is the whole reason that style has a name."""
    ui.facts([("skills", "8", "/tmp/skills")])
    assert dressed("path", "/tmp/skills") in capsys.readouterr().err


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


def test_ui_will_running_and_cure_contract_is_executable(capsys):
    """The three lines a person needs from a command that changes something.

    A will they can read before anything happens, a count that means what it says, and a
    cure only under a result that actually blocked. Each of the three is a sentence this
    repository already had in prose, and prose cannot fail — so each is a function that
    raises instead.
    """

    ui.will(
        "publish one immutable acceptance record",
        reads=["specs/010-x/spec.md", "proof/risk.txt"],
        writes=["specs/010-x/acceptance-r-010-01/record.json"],
        network=[],
    )
    # On stderr, with everything else a person reads on the way past. Stdout carries the
    # one JSON object and nothing else, so a will printed there would break that contract.
    captured = capsys.readouterr()
    assert captured.out == ""
    printed = captured.err
    assert "will  publish one immutable acceptance record" in printed
    assert "reads   specs/010-x/spec.md, proof/risk.txt" in printed
    assert "writes  specs/010-x/acceptance-r-010-01/record.json" in printed
    # Absence is stated, never omitted: a missing line reads as "unknown", not as "none".
    assert "network none" in printed

    for index, name in ((1, "read the anchored sources"), (2, "publish")):
        ui.running(index, 2, name)
    counted = capsys.readouterr()
    assert counted.out == ""
    counted = counted.err
    assert "RUNNING 1/2  read the anchored sources" in counted
    assert "RUNNING 2/2  publish" in counted

    # A count that cannot be true is refused rather than printed.
    for index, total in ((3, 2), (0, 2), (1, 0), (1, -1), (True, 2), (1, True)):
        with pytest.raises(ValueError):
            ui.running(index, total, "a step")

    # A cure belongs under a result that blocked, and nowhere else.
    ui.cure("FAIL", "ai-eng init --project")
    ui.cure("INCOMPLETE", "")
    assert "fix: ai-eng init --project" in capsys.readouterr().out
    for status in ("PASS", "WARN", "READY", "CANCELLED", "WOULD_CHANGE", ""):
        with pytest.raises(ValueError):
            ui.cure(status, "ai-eng doctor --fix")

    # And a cure may never be a way around the thing that blocked.
    for bypass in (
        "git commit --no-verify",
        "ai-eng exception --skip 'it is fine'",
        "git push --force",
        "set the bypass",
        "skip the guard",
    ):
        with pytest.raises(ValueError):
            ui.cure("FAIL", bypass)


def test_the_new_renderers_keep_their_parity_with_and_without_colour(coloured, capsys):
    """39t's three renderers, driven through a terminal that asked for decoration.

    Every other family in this file is checked both ways; these three were only ever seen
    undecorated, so nothing said their words survive styling. The words are what a person
    greps for and what this suite asserts, so they have to be the same words either way.
    """

    ui.will("do one thing", ["a"], ["b"], ["c"])
    ui.running(1, 1, "the only stage")
    decorated = capsys.readouterr().err
    for fragment in ("will  do one thing", "reads   a", "writes  b", "network c"):
        assert fragment in decorated, fragment
    assert "RUNNING 1/1  the only stage" in decorated
