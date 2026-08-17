"""The reader, held to what specification 015 says it must refuse.

Every case here mutates a copy of the register and asserts the reader catches it. A reader
tested only on the register that already passes is a reader nobody has seen say no.
"""

from __future__ import annotations

import copy
import subprocess
import sys
import tomllib
from pathlib import Path

import pilot_register

ROOT = Path(__file__).resolve().parents[1]


def register() -> dict:
    return tomllib.loads((ROOT / "policy" / "pilot-register.toml").read_text(encoding="utf-8"))


def test_the_register_this_repository_ships_is_a_register():
    assert pilot_register.problems(register()) == []


def test_it_runs_as_a_command_and_names_every_row_that_has_no_instrument():
    """`just check` runs this file, so it has to answer as a process and not only as an
    import — and the list is named rather than counted, because a count is a thing you round
    and a list is a thing you have to answer."""
    done = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "pilot_register.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert "no_instrument  guard_p95_ms" in done.stdout
    assert "RAN register=27" in done.stdout

    # The prohibitions split too, and until now nothing printed it: the only statement of
    # how many of them can fail closed was a sentence in `specs/015` — and that sentence
    # said eleven while the register shipped seven arguing their case. Nothing compared the
    # two, so nothing could go red. Read off the register here rather than written down,
    # because a number typed into a test is the same defect one file further along.
    rows = register()["prohibition"]
    argued = [str(row["id"]) for row in rows if not row.get("check")]
    assert f"{len(rows) - len(argued)} of {len(rows)} prohibitions fail closed" in done.stdout
    for name in argued:
        assert f"reason_only    {name}" in done.stdout


def test_a_bound_beside_no_instrument_is_an_error():
    """The pair specification 015 names explicitly: a bound nobody can measure is a number
    somebody will quote."""
    broken = copy.deepcopy(register())
    for row in broken["indicator"]:
        if row.get("no_instrument"):
            row["bound"] = "under 50 ms"
            break
    assert any("that pair is an error" in line for line in pilot_register.problems(broken))


def test_a_command_with_no_bound_is_an_error():
    """An indicator whose command runs and whose result nothing compares is a number printed
    into a log, not a gate."""
    broken = copy.deepcopy(register())
    for row in broken["indicator"]:
        if row.get("command"):
            del row["bound"]
            break
    assert any("nothing can go red" in line for line in pilot_register.problems(broken))


def test_a_row_that_is_neither_instrumented_nor_excused_is_an_error():
    broken = copy.deepcopy(register())
    row = broken["indicator"][0]
    row.pop("command", None)
    row.pop("no_instrument", None)
    found = pilot_register.problems(broken)
    assert any("a command or a reason it has none" in line for line in found)


def test_a_prohibition_needs_either_a_check_or_a_reason_and_not_both():
    broken = copy.deepcopy(register())
    broken["prohibition"][0]["reason"] = "and also a reason"
    assert any("or why it cannot be" in line for line in pilot_register.problems(broken))


def test_a_missing_indicator_is_an_error_rather_than_a_shorter_register():
    broken = copy.deepcopy(register())
    broken["indicator"].pop()
    assert any("12 indicators" in line for line in pilot_register.problems(broken))


def test_a_completion_claim_cannot_stand_over_an_uninstrumented_row(tmp_path, monkeypatch):
    """The one thing this reader exists to refuse. It names every row rather than saying how
    many, and it exits non-zero: a wave does not close on the rows nobody equipped."""
    body = (ROOT / "policy" / "pilot-register.toml").read_text(encoding="utf-8")
    claimed = tmp_path / "pilot-register.toml"
    claimed.write_text(body.replace("p5_complete = false", "p5_complete = true"), encoding="utf-8")
    monkeypatch.setattr(pilot_register, "REGISTER", claimed)

    assert pilot_register.main() == 1


def test_a_register_it_cannot_read_fails_closed(tmp_path, monkeypatch):
    broken = tmp_path / "pilot-register.toml"
    broken.write_text("[claim\n", encoding="utf-8")
    monkeypatch.setattr(pilot_register, "REGISTER", broken)

    assert pilot_register.main() == 1


def test_every_indicator_the_proposal_names_has_a_row():
    """The thirteen are the proposal's own list, and a register missing one would be a
    register that decided which indicators count."""
    named = {row["id"] for row in register()["indicator"]}
    assert named == {
        "surface_proof_age",
        "guard_p95_ms",
        "mutation_score",
        "adversarial_control",
        "otlp_rejected",
        "spec_evidence",
        "skill_eval_delta",
        "repo_files_written",
        "intent_trace_coverage",
        "a11y_critical_journey",
        "aaa_exception_age",
        "coordination_overlap",
        "report_payload_unknown",
    }


def test_every_command_in_the_register_names_something_that_exists():
    """A row whose command is a sentence rather than a command is a row that reads as
    instrumented and is not. Each one is checked against the surface it claims: a verb this
    CLI has, a recipe this justfile has, or a file in this tree."""
    from ai_engineering import cli

    recipes = (ROOT / "justfile").read_text(encoding="utf-8")
    for row in register()["indicator"]:
        command = row.get("command")
        if not command:
            continue
        first, second = (command.split() + [""])[:2]
        if first == "ai-eng":
            assert second in cli.VERBS, f"{row['id']} names a verb that does not exist: {second}"
        elif first == "just":
            # `mutate *paths:` is a recipe with an argument, so the name is matched at the
            # start of a line rather than against a bare colon.
            import re

            named = re.search(rf"^{second}\b[^\n]*:", recipes, re.MULTILINE)
            assert named, f"{row['id']} names a recipe that does not exist: {second}"
        else:
            named = [word for word in command.split() if word.startswith("tests/")]
            assert named, f"{row['id']} names no verb, recipe or file: {command}"
            assert (ROOT / named[0]).exists(), f"{row['id']} names a file that is not there"


def test_a_bound_stated_twice_has_to_agree_with_itself():
    """EP-283. `surface_proof_age` said seven days in a sentence, `surface.MAX_AGE_CEILING`
    caps a receipt's own declared window at thirty-one, and nothing said which number
    governed or compared the two. That is the same shape as the manifest declaring a
    capability the gate forbade, and an audit found both on the same day.

    The bound is a number now and the reader reads the ceiling from the module that enforces
    it, so the two cannot drift. A bound looser than that ceiling is refused, because an
    indicator that goes red only after the reader has already refused the receipt is an
    indicator that never goes red."""

    from ai_engineering import surface

    rows = {str(row["id"]): row for row in register()["indicator"]}
    assert rows["surface_proof_age"]["bound_seconds"] == 7 * 24 * 3600
    assert pilot_register._CEILING == surface.MAX_AGE_CEILING

    loose = {
        "indicator": [{**rows["surface_proof_age"], "bound_seconds": surface.MAX_AGE_CEILING + 1}],
        "prohibition": [],
    }
    assert any("could never go red first" in line for line in pilot_register.problems(loose))

    wrong = {
        "indicator": [{**rows["surface_proof_age"], "bound_seconds": "seven days"}],
        "prohibition": [],
    }
    assert any("not a positive number" in line for line in pilot_register.problems(wrong))


def test_a_requirement_nobody_will_gate_says_what_would_change_that():
    """Rule 12's other half, given one home.

    "A judgement that cannot fail closed stays a prompt and you write down why" was being
    honoured — the reasons existed — across three specifications, two ceiling comments and a
    test docstring. A reader asking "did anybody decide this, or did it just never get
    built?" had to find all six before they could tell.

    A row here is not a pass and never becomes one: the audit counts these INCOMPLETE,
    because the requirement asks for behaviour and this records how the decision is held.
    What it must carry is `reopen_when` — a row without one is a permanent no, and a
    permanent no about somebody else's requirement is not this framework's to take.
    """

    rows = register().get("ungated", [])
    assert rows, "the ungated list is empty, so this proves nothing"

    for row in rows:
        assert str(row["id"]).startswith("EP-"), row
        assert row["asks"].strip() and row["reason"].strip() and row["reopen_when"].strip()

    # Each of the three fields is required, and the reader is shown refusing each absence.
    for missing in ("asks", "reason", "reopen_when"):
        broken = {"indicator": [], "prohibition": [], "ungated": [{**rows[0]}]}
        del broken["ungated"][0][missing]
        found = pilot_register.problems(broken)
        assert any(rows[0]["id"] in line for line in found), (missing, found)

    # And no requirement is both gated and excused: an id here must not name a check that
    # exists, or the register would be arguing with itself the way the manifest did.
    ids = {str(row["id"]) for row in rows}
    body = (ROOT / "tests" / "test_contracts.py").read_text(encoding="utf-8")
    for name in ids:
        assert f'("{name}", "ai-' not in body, f"{name} is excused here and pinned there"


def test_a_declared_threshold_and_the_code_that_enforces_it_cannot_drift(tmp_path, monkeypatch):
    """`EP-057`: a stated prohibition and a numeric threshold for the same rule.

    Fourteen prohibitions are stated and none of them carries a number — that was the
    finding, and it is still true of those fourteen. Two rules in this framework do carry
    one, and both were bare literals in the middle of a function, which is how a threshold
    changes without anybody arguing for it.

    The pairing is what the requirement asks for, so the pairing is what is checked: the
    register names the constant, the runner reads it off the module, and a register whose
    number has moved away from the code's is refused rather than printed. Neither half can
    move without the other going red, which is the only thing that makes a declared number
    more than a number in a document.
    """

    import tomllib

    from ai_engineering import report

    declared = tomllib.loads((ROOT / "policy" / "pilot-register.toml").read_text(encoding="utf-8"))[
        "threshold"
    ]

    assert [row["id"] for row in declared] == ["owed-a-script", "bypasses-worth-a-look"]
    for row in declared:
        constant = row["enforced_by"].split(",")[0].rsplit(".", 1)[-1]
        assert getattr(report, constant) == row["threshold"], row["id"]
        assert row["never"].strip(), f"{row['id']} states no prohibition"
        assert row["stated_in"].strip(), f"{row['id']} says nowhere it is written down"
        assert row["unit"].strip(), f"{row['id']} counts nothing in particular"

    # And the drift is caught rather than printed. A register that says four while the code
    # says three is the exact failure this pairing exists to prevent, and it cannot be
    # produced from this tree — so it is produced here.
    drifted = tmp_path / "register.toml"
    body = (ROOT / "policy" / "pilot-register.toml").read_text(encoding="utf-8")
    body = body.replace("threshold = 3", "threshold = 4", 1)
    drifted.write_text(body, encoding="utf-8")

    import pilot_register

    monkeypatch.setattr(pilot_register, "REGISTER", drifted)
    assert pilot_register.main() == 1, "a threshold that had drifted from the code was printed"


def test_the_runner_still_works_with_nothing_but_an_interpreter():
    """It is a command before it is a test, and it stopped being one for an hour.

    `just register` invokes this with a bare interpreter and the mutation harness runs it
    from a copied tree. Neither has the package installed. Binding the declared thresholds to
    the code that enforces them added `from ai_engineering import report`, and the runner
    died with `ModuleNotFoundError` in both — while the local gate stayed green, because
    `uv run` happens to put the product on the path there.

    So this runs it the way those two run it: a subprocess with no inherited environment,
    which is the only arrangement that can tell a runner that works from a runner that works
    *here*.
    """
    import os
    import subprocess
    import sys

    done = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "pilot_register.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=300,
        env={"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp")},
        check=False,
    )

    assert done.returncode == 0, done.stdout[-1500:] + done.stderr[-1500:]
    assert "RAN register=" in done.stdout
    assert "threshold      owed-a-script" in done.stdout
    assert "ModuleNotFoundError" not in done.stderr
