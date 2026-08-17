"""The release floor, as criteria that execute rather than a level named in a document.

`EP-022` asks for AA as the release floor. `EP-085` asks that the floor be something a gate
blocks on. `EP-292` asks for coverage over enumerated critical journeys — over a list nobody
had written, which makes any coverage figure a percentage of nothing.

`policy/accessibility.toml` is that list, and it is smaller than the standard on purpose:
WCAG is written for pages, this is a command-line tool, and claiming AA over criteria about
viewports and focus order would be claiming to have met things that do not apply here. Every
criterion in the file says either how it is checked or why it cannot be, and this file is the
"how" — so a criterion marked `checked = true` whose test is missing turns the gate red.

What is deliberately not here: a contrast ratio. The colours belong to the terminal, and a
number measured on this machine would be a fact about one colour scheme. The criterion that
covers it in our hands is 1.4.1 — nothing depends on the colour arriving at all — and that is
checked against every state this CLI can print, not against a sample.
"""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering import outcome, ui

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "accessibility.toml"


def declared() -> dict:
    return tomllib.loads(POLICY.read_text(encoding="utf-8"))


def test_every_criterion_says_how_it_is_checked_or_why_it_is_not():
    """The rule that keeps the file honest, and it has no third state.

    A criterion with neither a check nor a reason is a claim about accessibility that nobody
    made and nobody can refuse — which is the shape of every false green this audit has
    found. And a checked criterion whose named test does not exist is worse: it reads as
    covered from the file alone.
    """

    policy = declared()
    body = (ROOT / "tests" / "test_accessibility.py").read_text(encoding="utf-8")

    assert policy["floor"]["level"] == "AA"
    assert policy["floor"]["target"] == "AAA"

    for row in policy["criterion"]:
        if row.get("checked"):
            assert row.get("means_here", "").strip(), f"{row['id']} is checked and says nothing"
            named = row["how"].rsplit("::", 1)[-1]
            assert f"def {named}(" in body, f"{row['id']} names {named}, which does not exist"
        else:
            assert len(row.get("reason", "").strip()) > 30, (
                f"{row['id']} is neither checked nor argued for. A criterion with no check "
                "and no reason is a claim about accessibility nobody made"
            )
            # And the date it was last read. `EP-293` asked for the age of an accessibility
            # exception; the answer was that none had ever been recorded, so there was
            # nothing to age. A criterion that executes is re-read by its test on every run
            # and needs no date — one held by a sentence is re-read only when somebody
            # decides to, and without a date nobody can tell when that last was.
            assert datetime.strptime(str(row["reviewed"]), "%Y-%m-%d"), row["id"]
            assert "reviewed" not in row or not row.get("checked")

    checked = [row["id"] for row in policy["criterion"] if row.get("checked")]
    assert len(checked) >= 5, "the floor is thinner than the level it claims"


def test_the_critical_journeys_are_enumerated_and_each_names_a_command():
    """`EP-292` asked for coverage over enumerated critical journeys and there was no list.

    A journey without an entry command is a journey nobody can walk, so the check is on the
    command as much as on the name — and the seven here are the seven a person actually
    takes: install, adopt, gate, diagnose, record, report, remove.
    """

    journeys = declared()["journey"]
    ids = [row["id"] for row in journeys]

    assert ids == ["install", "adopt", "gate", "diagnose", "record", "report", "remove"]
    assert len(set(ids)) == len(ids)
    for row in journeys:
        assert len(row["what"]) > 25, f"{row['id']} does not say what it is"
        assert row["entry"].strip(), f"{row['id']} names no command"


def test_no_state_is_told_by_colour_alone():
    """WCAG 1.4.1, against every state this CLI can print rather than a sample.

    The reason it is not a formality: two pairs of states share a colour today. INCOMPLETE
    and WARN are both yellow; CANCELLED and WOULD_CHANGE are both dim. A reader who could
    only see colour would be told those pairs are the same thing, and one of each pair
    blocked them while the other did not.
    """

    import json

    # Every outcome word the schema allows has a mark, read from the schema rather than
    # from a list written twice: a word added there and not here raises a KeyError at the
    # moment the program tries to tell somebody what happened.
    allowed = set(
        json.loads((ROOT / "policy" / "outcome-v1.schema.json").read_text(encoding="utf-8"))[
            "properties"
        ]["outcome"]["enum"]
    )
    assert allowed == set(ui.RESULT_MARKS), (
        f"the schema and the marks disagree: {sorted(allowed ^ set(ui.RESULT_MARKS))}"
    )

    glyphs = [glyph for glyph, _ in ui.RESULT_MARKS.values()]
    styles = [style for _, style in ui.RESULT_MARKS.values()]

    assert len(set(glyphs)) == len(glyphs), f"two states share a glyph: {glyphs}"
    assert len(set(styles)) < len(styles), (
        "no two states share a colour, so this case no longer proves what it was written "
        "for — re-read it rather than deleting it"
    )

    # And the step and verdict tables, which are the other two places a state reaches a
    # person. Each carries its own distinct non-colour signal.
    assert len({glyph for glyph, _ in ui.MARKS.values()}) == len(ui.MARKS)
    assert len({word.strip() for word, _ in ui.VERDICTS.values()}) == len(ui.VERDICTS)


def test_the_word_survives_where_the_glyph_does_not(capsys, monkeypatch):
    """The plain path, which is where 1.4.1 is actually load bearing.

    A non-interactive stream drops the styling, and on a Windows console the glyphs
    themselves cannot always be encoded — that is a real crash this repository has already
    had. So the state has to arrive as a word, and this asserts it does for every one of the
    seven, in the output a person or a log actually receives.
    """

    ui.reset()
    for word in ui.RESULT_MARKS:
        ui.render_result(outcome.result(word))
        said = capsys.readouterr().out
        assert word in said, f"{word} did not appear as a word"
        assert "Exit code:" in said, f"{word} printed no exit code"
    ui.reset()


def test_a_result_names_itself_before_it_explains_itself(capsys):
    """WCAG 2.4.6, in the only form it has here: the outcome word comes first, and every
    field after it is introduced by its label rather than by position. A reader arriving in
    the middle of a log has to be able to tell what they are looking at."""

    ui.reset()
    ui.render_result(outcome.result("FAIL"))
    lines = [one for one in capsys.readouterr().out.splitlines() if one.strip()]

    assert "FAIL" in lines[0], f"the first line does not name the outcome: {lines[0]!r}"
    for label in ("Reason:", "Next action:", "Exit code:"):
        assert any(one.strip().startswith(label) for one in lines[1:]), label
    ui.reset()


def test_a_refusal_is_identified_in_words(capsys):
    """WCAG 3.3.1. An exit status is not an error message. Every refusal this product can
    produce arrives as a word a person reads, and the exit code travels beside it rather
    than instead of it."""

    ui.reset()
    for word in ("FAIL", "INCOMPLETE", "CANCELLED"):
        result = outcome.result(word)
        assert result.exit_code != 0, f"{word} exits zero, so only the text says it refused"
        ui.render_result(result)
        said = capsys.readouterr().out
        assert word in said
        assert said.strip(), f"{word} printed nothing at all"
    ui.reset()


@pytest.mark.parametrize("word", ["FAIL", "INCOMPLETE"])
def test_anything_that_blocks_says_what_to_do_next(word):
    """WCAG 3.3.3, and the one criterion this product was already built around.

    `outcome.Result` carries `next_action`, and a result that blocked somebody without one
    is a dead end wearing a diagnosis. The standard has a name for the thing this repository
    calls a cure, which is worth saying out loud: the two were arrived at separately.
    """

    result = outcome.result(word)

    assert result.next_action.strip(), f"{word} blocks and offers nothing to do"
    assert result.exit_code != 0
    assert len(result.next_action) > 10, f"{word}'s next action is too short to act on"


def test_every_decision_is_taken_at_a_keyboard():
    """WCAG 2.1.1, in the form that matters here.

    Everything is reachable from the keyboard because there is nothing else. What the
    criterion is worth checking for is the inverse: the two verbs that ask a person to type
    must refuse from a pipe rather than accepting a flag in place of the person. `-y` from a
    script is exactly what those gates exist to stop.
    """

    body = {
        name: (ROOT / "src" / "ai_engineering" / f"{name}.py").read_text(encoding="utf-8")
        for name in ("update", "uninstall")
    }

    for name, source in body.items():
        assert "sys.stdin.isatty()" in source, f"{name} does not check for a terminal"
        assert "keyboard" in source or "no keyboard" in source, f"{name} says nothing about it"


def test_an_argument_that_has_gone_a_year_without_being_re_read_is_reported():
    """`EP-293`, and the branch that would otherwise never run.

    Every recorded exception is dated today, so the ageing code in `doctor` cannot fire from
    this tree — which is exactly the shape of the un-reachable rule found in the adapter
    version binding earlier today. So the age is computed here against a date that is old,
    and the boundary is checked in both directions: a year is inside, a year and a day is
    not.
    """

    from ai_engineering import doctor

    assert doctor.ACCESSIBILITY_MAX_AGE == 365

    today = datetime.now(UTC)
    for days, expected in ((0, False), (364, False), (365, False), (366, True)):
        when = today - timedelta(days=days)
        assert ((today - when).days > doctor.ACCESSIBILITY_MAX_AGE) is expected, days

    # Every exception in the shipped file is inside the window, or `doctor` is already
    # reporting one and this suite has not noticed.
    for row in declared()["criterion"]:
        if row.get("checked"):
            continue
        when = datetime.strptime(row["reviewed"], "%Y-%m-%d").replace(tzinfo=UTC)
        assert (today - when).days <= doctor.ACCESSIBILITY_MAX_AGE, (
            f"{row['id']} was last read on {row['reviewed']} and is overdue. Re-read the "
            "argument and move the date, or turn it into a check"
        )


def test_the_age_is_reported_and_never_silently_swallowed(tmp_path, monkeypatch):
    """The direction the ageing has to fail in. An overdue argument did not break anything,
    so it is not a failure — but a check that returned `None` for it would be silence, and
    silence over an argument nobody has read in a year is how the argument becomes folklore.
    """

    from ai_engineering import doctor, paths

    aged = tmp_path / "accessibility.toml"
    body = POLICY.read_text(encoding="utf-8").replace(
        'reviewed = "2026-08-17"', 'reviewed = "2000-01-01"'
    )
    aged.write_text(body, encoding="utf-8")
    monkeypatch.setattr(paths, "policy", lambda name: aged)

    with pytest.raises(doctor.Undecidable) as reported:
        doctor.accessibility_floor(ROOT)

    assert "a year without being re-read" in str(reported.value)
    assert "1.4.3" in str(reported.value)
    assert "Nothing broke" in str(reported.value)
