"""The report a person actually reads, pinned line by line.

Every assertion here names one way the weekly digest, the verb table, the yaml reader or
the skill contract could print something plausible and wrong. The digest is where a
rule-12 judgement is read from and where a bypass becomes visible to somebody other than
the person who took it, so its wording is behaviour: a sentence nobody asserts is a
sentence that can quietly become a different sentence.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from ai_engineering import (
    __version__,
    cli,
    exception,
    outcome,
    paths,
    text,
)
from ai_engineering import report as report_command

TODAY = date.today().isoformat()


def _ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def _event(name: str, cls: str, ts: str | None = None, session: str = "s", **data) -> dict:
    return {"name": name, "cls": cls, "ts": ts or TODAY, "session": session, "data": data}


# ------------------------------------------------------------------ digest, the parts


def test_an_event_with_no_timestamp_is_outside_every_window():
    """An event with no date is not evidence of anything happening this week. Read as the
    word "None" it sorts after every real date, so it would be counted forever."""
    undated = {"name": "a", "cls": "blocked", "session": "s", "data": {}}
    assert report_command.within([undated, _event("b", "blocked")], 7) == [_event("b", "blocked")]


def test_a_blocked_event_that_carries_no_reason_still_gets_a_line():
    """Older events, and guards that deny without a sentence, have no reason field. If
    reading them raises, one malformed event deletes the entire week's report."""
    counted = report_command.by_reason([_event("loop_guard", "blocked")], "blocked")
    assert dict(counted) == {"loop_guard — ": 1}


def test_a_very_long_reason_is_cut_at_seventy_characters():
    """The reason is a guard's whole denial message. Untrimmed it wraps the terminal and
    the counts stop lining up, so the cut is part of the report, not an accident."""
    counted = report_command.by_reason(
        [_event("loop_guard", "blocked", reason="r" * 90)], "blocked"
    )
    assert list(counted) == ["loop_guard — " + "r" * 70]


def test_the_same_name_with_two_different_reasons_is_not_the_same_judgement():
    """Rule 12 fires on a judgement that always comes out the same way. Two different
    verdicts from one guard are two judgements, and merging them invents a rule that is
    owed a script when nothing repeated at all."""
    events = [_event("loop_guard", "blocked", reason=reason) for reason in ("first", "second")] * 2
    assert report_command.repeats(events) == []


def test_three_denials_with_no_reason_are_still_three_of_the_same_thing():
    """A guard that denies without a sentence still repeats. Reading a missing reason as
    anything other than nothing either crashes the report or prints a placeholder into
    the row somebody is asked to act on."""
    bare = {"name": "loop_guard", "cls": "blocked", "ts": TODAY, "session": "s"}
    assert report_command.repeats([bare] * 3) == [
        "    loop_guard ·  3× same verdict each time → owed a script"
    ]


def test_the_reason_in_a_repeat_row_is_cut_at_fifty_characters():
    """The row has to fit on one line beside its count, so the reason is trimmed shorter
    here than in the blocked list. A row that runs past the count is a row nobody reads."""
    events = [_event("loop_guard", "blocked", reason="r" * 80)] * 3
    assert report_command.repeats(events) == [
        f"    loop_guard · {'r' * 50} 3× same verdict each time → owed a script"
    ]


# ------------------------------------------------------------------ digest, the report


@pytest.fixture
def report(tmp_path, monkeypatch, capsys):
    """Everything the digest reads and writes, moved inside tmp_path: the events, the
    coverage line, the repository it reports on and the home folder it stamps."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    emit = paths.load("_emit")
    monkeypatch.setattr(emit, "repo_root", lambda start=None: None)
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    state = SimpleNamespace(
        root=root,
        home=tmp_path / "home",
        events=[],
        coverage=["    claude code   BLOCKS", "    codex         UNPROVEN"],
        asked=[],
        emit=emit,
    )

    def events(passed):
        state.asked.append(("events", passed))
        return state.events

    def coverage(passed):
        state.asked.append(("coverage", passed))
        return state.coverage

    monkeypatch.setattr(report_command.doctor, "events", events)
    monkeypatch.setattr(report_command.doctor, "coverage", coverage)

    def run(*argv):
        execution = report_command.main(["digest", *argv])
        assert type(execution) is outcome.Execution
        assert execution.result == outcome.result("PASS")
        assert execution.checks
        assert execution.changes[0].status == "APPLIED"
        return capsys.readouterr().out.splitlines()

    state.run = run
    return state


def test_the_report_is_about_the_repository_you_are_standing_in(report):
    """The chain is per repository. A digest that read the events of no repository, or of
    a different one, would report a quiet week for a repository that had a loud one."""
    report.run()
    assert ("events", report.root) in report.asked
    assert ("coverage", report.root) in report.asked


def test_the_heading_names_the_window_and_counts_the_sessions(report):
    """Two sessions that blocked once each is a different week from one session that
    blocked twice, and the heading is the only place the difference is visible."""
    report.events = [
        _event("loop_guard", "blocked", session="one"),
        _event("loop_guard", "blocked", session="two"),
    ]
    assert "Week of " + _ago(7) + " " * 30 + "2 sessions" in report.run()


def test_two_weeks_means_fourteen_days_and_not_a_day_more(report):
    """--weeks is a multiplier on seven days. Divided instead of multiplied it silently
    narrows the window; widened by one it reports events from before the window under a
    heading that names the window."""
    report.events = [
        _event("loop_guard", "blocked", ts=_ago(10), reason="inside"),
        _event("loop_guard", "blocked", ts=_ago(15), reason="outside"),
    ]
    printed = report.run("--weeks", "2")
    assert "Week of " + _ago(14) + " " * 30 + "1 sessions" in printed
    assert "  Blocked 1 times:" in printed
    assert "    1× loop_guard — inside" in printed
    assert "    1× loop_guard — outside" not in printed


def test_the_help_names_the_command_it_is_help_for(capsys):
    """`ai-eng report digest --help` reached through the verb table names the command it
    is describing; argparse otherwise names whatever binary started the process."""
    with pytest.raises(SystemExit):
        report_command.main(["digest", "--help"])
    assert capsys.readouterr().out.startswith("usage: ai-eng report digest")


def test_a_week_with_nothing_in_it_says_which_two_things_that_could_mean(report):
    """Zero blocks is either a quiet week or a control that has stopped firing, and the
    report must not let a reader take the first reading. Every line here is written for
    somebody to act on, so every line is asserted whole."""
    printed = report.run()
    assert "  Blocked 0 times:" in printed
    assert "    nothing. Either a quiet week, or a control that is no longer firing —" in printed
    assert "    assertion 7 is what tells the two apart." in printed
    assert "  Bypassed 0 times." in printed
    assert "  Quiet controls — no real block this window; liveness is assertion 7's job:" in printed
    assert "    injection_guard, loop_guard, no_verify_guard, self_protect" in printed
    assert "  Commands: none" in printed
    assert "  Errors: 0" in printed


def test_a_control_that_blocked_this_week_is_not_listed_as_quiet(report):
    """The quiet list is the liveness reading. A guard that fired and is still named
    there tells the reader to go looking for a fault that is not present."""
    report.events = [_event("loop_guard", "blocked", reason="no plan")]
    assert "    injection_guard, no_verify_guard, self_protect" in report.run()


def test_only_the_six_loudest_blocks_are_printed(report):
    """The list is capped so the paragraph stays a paragraph. Uncapped, one noisy guard
    pushes everything else off the screen; capped one short, the sixth loudest vanishes."""
    report.events = [
        _event(f"guard{rank}", "blocked", reason=f"reason {rank}")
        for rank in range(1, 8)
        for _ in range(rank)
    ]
    printed = report.run()
    assert "    7× guard7 — reason 7" in printed
    assert "    2× guard2 — reason 2" in printed
    assert "    1× guard1 — reason 1" not in printed


def test_only_the_four_loudest_bypasses_are_printed_and_three_is_the_warning(report):
    """A bypass is a person's act at a keyboard. Three of them is the line at which the
    guard is the problem, and that sentence is the whole point of the section."""
    report.events = [
        _event(f"guard{rank}", "bypassed", reason=f"reason {rank}")
        for rank in range(1, 6)
        for _ in range(rank)
    ]
    printed = report.run()
    assert "  Bypassed 15 times." in printed
    assert "    5× guard5 — reason 5" in printed
    assert "    2× guard2 — reason 2" in printed
    assert "    1× guard1 — reason 1" not in printed
    assert "    A guard you bypass three times is a guard to fix or to delete." in printed


def test_the_commands_used_and_the_latest_error_are_named(report):
    """A week with no blocks and no commands is a week nobody worked in; a week with no
    blocks and forty commands is a control that has stopped firing. The error line is the
    same reading for crashes, and it carries the last message rather than a count alone."""
    report.events = [
        _event("digest", "command"),
        _event("digest", "command"),
        _event("plan", "command"),
        _event("cli", "error", error="first"),
        _event("cli", "error", error="e" * 90),
    ]
    printed = report.run()
    assert "  Commands: digest 2  plan 1" in printed
    assert "  Errors: 2 (latest: " + "e" * 60 + ")" in printed


def test_an_error_with_no_message_says_nothing_rather_than_a_placeholder(report):
    """A crash recorded without a message is common — the process was on its way out.
    The report shows the empty message, and never invents one."""
    report.events = [_event("cli", "error")]
    assert "  Errors: 1 (latest: )" in report.run()


def test_two_repeated_judgements_are_two_separate_rows(report):
    """Rule 12's list is read one line at a time and acted on one line at a time. Rows
    run together on a single line are rows that cannot be acted on."""
    report.events = [_event("loop_guard", "blocked", reason="a loop")] * 3 + [
        _event("loop_guard", "bypassed", reason="shipping late")
    ] * 3
    printed = report.run()
    # The number in the heading is the constant that decides the rows under it, not a word
    # typed beside it. It read "three times or more" while `OWED_A_SCRIPT` decided the
    # threshold, so the sentence and the rule could have drifted apart in either direction
    # and this assertion would have gone on passing.
    # The heading now names what was measured as well as the threshold, because it prints on
    # every run rather than only on the runs with something to say — an empty window and an
    # absent check used to produce the same silence. Both numbers come from the run and the
    # constant, so neither can drift into a sentence that stays true after the rule changes.
    assert (
        f"  Rule 12 — 2 judgement(s) counted in this window, the most repeated 3×, "
        f"owed a script at {report_command.OWED_A_SCRIPT}×:"
    ) in printed
    assert "    loop_guard · a loop 3× same verdict each time → owed a script" in printed
    assert "    loop_guard · shipping late 3× same verdict each time → owed a script" in printed


def test_a_configured_sink_that_is_receiving_nothing_says_so(report, monkeypatch):
    """A destination configured and not receiving is the exact failure this product
    exists to cure: green reported while blind. It is read from this repository's pin,
    and the arrow is what tells a reader the line is bad news."""
    (report.root / ".ai" / "config.toml").write_text(
        '[observability]\nendpoint = "http://127.0.0.1:4318"\nprovider = "grafana"\n'
    )
    monkeypatch.setattr(paths.load("_otlp"), "probe", lambda: (False, "404, 1 rejected"))
    assert "  Sink: grafana · 404, 1 rejected  ← nothing is arriving" in report.run()


def test_a_sink_that_is_receiving_is_named_without_a_warning(report, monkeypatch):
    """The same line with the arrow attached to a working sink teaches a reader to
    ignore the arrow. A sink with no provider name is still a sink, and says so."""

    def config(passed=None):
        report.asked.append(("config", passed))
        return {"observability": {"endpoint": "http://127.0.0.1:4318"}} if passed else {}

    monkeypatch.setattr(report.emit, "config", config)
    monkeypatch.setattr(paths.load("_otlp"), "probe", lambda: (True, "200, 0 rejected"))
    printed = report.run()
    assert ("config", report.root) in report.asked
    assert "  Sink: configured · 200, 0 rejected" in printed


def test_a_repository_with_no_sink_configured_says_nothing_about_one(report):
    """Silence is the right answer for a machine that has not asked for a sink. A line
    reporting on a sink nobody configured is a line that trains the reader to skip."""
    assert not [line for line in report.run() if "Sink:" in line]


def test_the_coverage_line_is_printed_under_its_own_heading(report):
    """The coverage line is what separates a surface that blocks from one that is only
    documented. Printed without its heading, or replaced by a placeholder, the reader
    cannot tell which surfaces the numbers belong to."""
    printed = report.run()
    assert "  Coverage — what actually blocks, by surface" in printed
    assert "    claude code   BLOCKS" in printed
    assert "    codex         UNPROVEN" in printed


def test_the_stamp_lands_where_the_session_hook_looks_for_it(report):
    """The session hook reads this file to say one line out loud when the record has
    gone a week unread. Written under any other name, or refused because the home folder
    did not exist yet, the reminder never fires and nobody notices it never fires."""
    assert not report.home.exists()
    report.run()
    assert [entry.name for entry in report.home.iterdir()] == ["cache"]
    assert [entry.name for entry in (report.home / "cache").iterdir()] == ["digest.json"]
    assert json.loads((report.home / "cache" / "digest.json").read_text())["read"] <= time.time()


def test_the_report_can_be_read_twice(report):
    """Reading the record is not a one-off. If the second run raised because the stamp
    was already there, the digest would work once per machine."""
    report.run()
    report.run()


# ------------------------------------------------------------------ cli


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    """The events the verb table records, captured instead of appended to a real chain."""
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    emit = paths.load("_emit")
    monkeypatch.setattr(emit, "repo_root", lambda start=None: None)
    seen: list[tuple[str, str, dict]] = []
    monkeypatch.setattr(emit, "emit", lambda name, cls, **data: seen.append((name, cls, data)))
    return seen


def test_every_verb_is_its_own_line_in_the_help(capsys):
    """The help is the only place anybody looks for the surface. Ten verbs run together
    on one line is a list nobody can read, and a verb nobody reads does not exist."""
    assert cli.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    for verb, description in cli.VERBS.items():
        row = [line for line in lines if line.strip().startswith(verb)]
        assert len(row) == 1 and row[0].endswith(description)


@pytest.mark.parametrize("flag", ["-V", "--version", "version"])
def test_every_spelling_of_asking_for_the_version_answers(flag, capsys):
    """The version is what a bug report is filed against and what an install check greps
    for. A spelling that falls through to the verb table exits 2 and prints usage."""
    assert cli.main([flag]) == 0
    assert capsys.readouterr().out == f"ai-engineering {__version__}\n"


def test_with_no_arguments_the_table_reads_the_real_command_line(monkeypatch, capsys):
    """The entry point calls main() with nothing and lets it read sys.argv. Reading from
    the wrong offset drops the verb and turns every invocation into a help screen."""
    monkeypatch.setattr(sys, "argv", ["ai-eng", "--version"])
    assert cli.main() == 0
    assert capsys.readouterr().out == f"ai-engineering {__version__}\n"


def test_the_flags_after_the_verb_reach_the_verb(recorded, monkeypatch):
    """The table splits the verb from its flags. Split one word too far along, every
    flagged command loses its first flag and the verb fails on arguments the user gave."""
    monkeypatch.setattr(
        exception,
        "main",
        lambda argv: (
            outcome.result("PASS") if argv == ["--skip", "late"] else outcome.result("FAIL")
        ),
    )
    assert cli.main(["exception", "--skip", "late"]) == 0


def test_a_verb_that_fails_fails_the_whole_command(recorded, monkeypatch):
    """A non-zero exit is how a script calling `ai-eng` learns a gate said no. Collapsed
    to zero, every caller believes the gate passed."""
    monkeypatch.setattr(exception, "main", lambda argv: outcome.result("FAIL"))
    assert cli.main(["exception"]) == 1
    assert recorded[0][2]["exit"] == 1


def test_an_interrupted_command_says_nothing_was_written(recorded, monkeypatch, capsys):
    """Ctrl-C during a command that writes the record leaves a person wondering what
    landed. The exit code is the shell's convention for it, and the sentence is the
    answer to the question they are about to ask."""

    def stop(argv):
        raise KeyboardInterrupt

    monkeypatch.setattr(exception, "main", stop)
    assert cli.main(["exception"]) == 130
    # The will and the counted stages precede it now; what matters is that the last thing a
    # person is told is what happened to their data, and that the count stopped where the
    # run stopped rather than reporting a stage that never ran.
    said = capsys.readouterr().err
    assert said.endswith("\ninterrupted; nothing was written.\n")
    assert "will  record one design exception, at a keyboard" in said
    assert "RUNNING 2/4  run it: exception" in said
    # The count says where the run reached, not how long the list is. An interrupted run
    # never reported an outcome, so it performed three of four stages and says so.
    assert "RUNNING 3/4  record the command" in said
    assert "RUNNING 4/4" not in said


def test_the_verb_that_ran_is_the_name_on_the_event(recorded, monkeypatch):
    """The digest groups by name. An event recorded under no name at all cannot be
    grouped, so the week's command counts silently lose the verb."""
    monkeypatch.setattr(exception, "main", lambda argv: outcome.result("PASS"))
    assert cli.main(["exception"]) == 0
    assert [(name, cls) for name, cls, _ in recorded] == [("exception", "command")]
    assert recorded[0][2]["verb"] == "exception"


def test_the_verb_that_blew_up_is_the_name_on_the_error(recorded, monkeypatch):
    """Same reading for the crash: an error event with no name tells you something broke
    this week and never which command it was."""

    def boom(argv):
        raise RuntimeError("nothing was written")

    monkeypatch.setattr(exception, "main", boom)
    assert cli.main(["exception"]) == 1
    # Two events now, and the second one is the point: a crashed run used to leave the
    # error and no `command` line at all, because the traceback took the process out
    # before the dispatcher could record what had run and with what exit code.
    assert [(name, cls) for name, cls, _ in recorded] == [
        ("exception", "error"),
        ("exception", "command"),
    ]
    assert "nothing was written" in recorded[0][2]["error"]
    assert recorded[1][2]["exit"] == 1


def test_how_long_the_verb_took_is_recorded_in_milliseconds(recorded, monkeypatch):
    """The duration is the only number that says a command is getting slower. In the
    wrong unit every command reads as instant and nothing ever looks slow."""
    ticks = iter([2.0, 4.0])
    monkeypatch.setattr(cli, "time", SimpleNamespace(perf_counter=lambda: next(ticks)))
    monkeypatch.setattr(exception, "main", lambda argv: outcome.result("PASS"))
    assert cli.main(["exception"]) == 0
    assert recorded[0][2]["ms"] == 2000


# ------------------------------------------------------------------ text


def test_a_tab_continues_the_line_above_it():
    """Editors write tabs. A folded description indented with one would be read as a new
    key, and the parser would reject a file that is correct."""
    assert text.flat_yaml("d: >\n\tone\n\ttwo\n") == {"d": "one two"}


def test_a_stray_indented_line_says_what_is_wrong_with_it():
    """The parser is strict so a malformed block fails now rather than in front of a
    person six weeks later, and that only helps if the error names the line."""
    with pytest.raises(ValueError, match="indents a line with no key above"):
        text.flat_yaml("  orphan\n")


def test_a_line_that_is_not_a_key_says_what_is_wrong_with_it():
    """Same reading for a list item or a stray sentence: a bare 'ValueError' sends the
    reader to the parser instead of to their own file."""
    with pytest.raises(ValueError, match="not a key"):
        text.flat_yaml("- a list item\n")


def test_only_the_quotes_around_a_value_are_stripped():
    """Stripping any other character eats the ends of real values, and a description
    that lost its first and last letter still passes every check we have."""
    assert text.flat_yaml("name: XavierX\n") == {"name": "XavierX"}


def test_a_horizontal_rule_in_the_body_does_not_end_the_frontmatter(tmp_path):
    """Markdown bodies contain `---` rules. Counted as the closing fence, the header of
    a perfectly ordinary skill file is either unreadable or read from the wrong half."""
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: ai-thing\n---\nbody\n\n---\n\nmore body\n", encoding="utf-8")
    assert text.frontmatter(path) == {"name": "ai-thing"}


def test_the_digest_prints_the_model_distribution_with_four_states_named(report):
    """Spec 042 / B-042-1, B-042-2: the Models lines print what the events carry, and
    name which state they are counting — reported (`model`) and routed (`tier_model`) —
    with `missing` for events that predate the field. The states are never merged."""

    # The real _emit writes `model` at the top of the event and `tier_model` inside
    # `data`; the fixture's _event helper puts kwargs in data, so build the events in the
    # shape the product writes.
    def command(name, model=None, tier=None):
        event = _event(name, "command", data={"verb": name})
        if model is not None:
            event["model"] = model
        if tier is not None:
            event["data"]["tier_model"] = tier
        return event

    report.events = [
        command("audit", model="nan/deepseek-v4-flash", tier="deepseek-v4-flash"),
        command("report", model="undetermined", tier="qwen3.8-flash"),
        command("spec"),  # no model key at all — the missing state
    ]
    printed = report.run()
    reported = next(line for line in printed if line.startswith("  Models, reported"))
    routed = next(line for line in printed if line.startswith("  Models, routed"))
    assert "nan/deepseek-v4-flash 1" in reported
    assert "undetermined 1" in reported
    assert "missing 1" in reported
    assert "deepseek-v4-flash 1" in routed
    assert "qwen3.8-flash 1" in routed
    assert "missing 1" in routed


def test_the_rule_twelve_row_relabels_the_escalation_as_already_scripted(report):
    """Spec 042 / B-042-4: a denial the guard marked escalated=True is the script rule 12
    owes, so it prints as 'already escalated' and is subtracted from the owed-ones pool —
    the same judgement is never counted twice."""
    report.events = (
        [
            _event("loop_guard", "blocked", reason="this exact call has been made 3 times")
            for _ in range(3)
        ]
        + [
            _event("loop_guard", "blocked", reason="Bash:pytest — denied", escalated=True)
            for _ in range(10)
        ]
        + [
            _event("loop_guard", "blocked", reason="Bash:pytest — denied", escalated=True)
            for _ in range(5)
        ]
    )
    printed = report.run()
    rows = [line for line in printed if "owed a script" in line or "already escalated" in line]
    assert any("same verdict each time → owed a script" in line for line in rows)
    assert any("already escalated" in line for line in rows)
    # The 15 escalated denials all carry the same key; they must appear as ONE relabelled
    # row, and the owed pool must not contain them.
    scripted_rows = [line for line in rows if "already escalated" in line]
    assert any("15×" in line for line in scripted_rows)
    owed = [line for line in rows if "same verdict each time" in line]
    assert not any("Bash:pytest" in line for line in owed), (
        "the escalated judgement must not also appear in the owed-ones pool"
    )
