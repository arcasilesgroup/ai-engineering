"""The reader, held to what specification 015 says it must refuse.

Every case here mutates a copy of the register and asserts the reader catches it. A reader
tested only on the register that already passes is a reader nobody has seen say no.
"""

from __future__ import annotations

import copy
import json
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
    assert "RAN register=33" in done.stdout

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
    assert any("18 indicators" in line for line in pilot_register.problems(broken))


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
    """The proposal's own list, and a register missing one would be a register that decided
    which indicators count.

    Thirteen of these came from what this repository could already compute. The last five
    came from auditing `EP-056`, which names six the pilot was commissioned to measure —
    defects, cost, wait, conflicts, escalations and false greens — and finding that not one
    of the thirteen was any of them. Five rows, not six: conflicts was already tracked as
    `coordination_overlap`, and a second row for it would be two homes for one number.

    Four of the five have no instrument and say so. That is the point of them: their absence
    read as though the pilot measured everything it set out to.
    """
    named = {row["id"] for row in register()["indicator"]}
    assert named == {
        "false_greens",
        "escalations",
        "defect_escape",
        "cycle_cost",
        "review_wait",
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
        "skill_evals_recall",
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
        assert row["asks"].strip()
        assert row["reason"].strip()
        assert row["reopen_when"].strip()

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


def test_a_claim_quoting_a_number_the_register_does_not_have_is_refused(tmp_path):
    """The sentence a reader takes the state from was one short, and nothing noticed.

    `claim.why` said "six indicators have no instrument". Five rows were added for `EP-056`,
    four of them uninstrumented, and the sentence stayed at six — because prose is data here
    and nothing read it as a number. Two homes for one count, in the file written to stop
    exactly that.

    A `why` that argues without quoting a figure stays fine. One that quotes the wrong figure
    is the failure, and it is the only thing this checks: the count of uninstrumented rows.
    """

    import pilot_register

    register = {
        "indicator": [
            {"id": "one", "no_instrument": "nothing computes it", "wave": "P5"},
            {"id": "two", "no_instrument": "nor this", "wave": "P5"},
        ],
        "claim": {"p5_complete": False, "why": "1 indicator has no instrument"},
    }

    refused = pilot_register.stale_claim(register, 2)

    assert "says 1 where 2" in refused
    assert not pilot_register.stale_claim({"claim": {"why": "the pilot has not been run"}}, 2), (
        "a reason that quotes no number is an argument, not a stale count"
    )
    assert not pilot_register.stale_claim(register, 1), "the number it does have must pass"


def test_a_receipt_may_not_give_itself_longer_than_the_register_publishes(tmp_path, monkeypatch):
    """Two numbers for one promise, with nothing comparing them.

    `EP-283` asks that a surface's proof go red once its denial is older than a week. The
    register declares that week and `surface._standing` enforces `min(the receipt's own
    window, 31 days)` — it never reads the register. So a receipt could write itself
    thirty-one days and stay green at thirty while this file published seven.

    The refusal names the gap in days rather than in seconds, because the number a reader
    acts on is "this stayed proven for 24 days longer than we said it would".
    """

    import pilot_register

    receipts = tmp_path / "surface"
    receipts.mkdir()
    (receipts / "opencode.enforcement.json").write_text(
        json.dumps({"max_age_seconds": 2_678_400}), encoding="utf-8"
    )
    (receipts / "tight.enforcement.json").write_text(
        json.dumps({"max_age_seconds": 3_600}), encoding="utf-8"
    )
    (receipts / "unreadable.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(pilot_register, "SURFACE_RECEIPTS", receipts)

    register = {"indicator": [{"id": "surface_proof_age", "bound_seconds": 604_800}]}
    loose = pilot_register.looser_than_declared(register)

    assert len(loose) == 1, loose
    assert "opencode.enforcement declares 2678400s" in loose[0]
    assert "24 days past" in loose[0]


def test_a_bound_the_register_does_not_state_is_reported_once_and_not_twice(tmp_path, monkeypatch):
    """`problems()` already refuses a `bound_seconds` that is not a positive number. Saying
    so again here in a second vocabulary is how a reader learns to ignore one of them."""

    import pilot_register

    monkeypatch.setattr(pilot_register, "SURFACE_RECEIPTS", tmp_path)

    assert pilot_register.looser_than_declared({"indicator": []}) == []
    assert (
        pilot_register.looser_than_declared(
            {"indicator": [{"id": "surface_proof_age", "bound_seconds": "a week"}]}
        )
        == []
    )


def test_no_ungated_row_is_held_by_a_condition_that_has_already_fired():
    """A refusal that has outlived its own argument.

    Every ungated row carries `reopen_when`: the thing that would make it gatable. The row is
    only honest while that thing has not happened, and nothing was checking. `EP-302` said it
    would reopen when "the record carries a red run somebody else can read"; the runner that
    writes exactly that has been in the tree and in the nightly lane for two days, and the row
    sat there refusing anyway.

    This cannot decide in general whether a condition has fired — that is a reading, and the
    register is right to keep it one. What it can do is refuse the specific shape that caught
    us twice: a row naming a file or a command that now exists. A reopening condition that
    points at something in the tree has, by its own words, already happened.
    """

    import re

    named = re.compile(r"`([a-z0-9_./-]+\.(?:py|toml|json|md|yml))`")
    fired = []
    for row in register().get("ungated", []):
        for candidate in named.findall(str(row.get("reopen_when", ""))):
            if (ROOT / candidate).exists():
                fired.append(f"{row['id']} reopens when {candidate} exists, and it does")

    # The shape this cannot see, said once so nobody reads its silence as coverage. `EP-163`
    # reopened when "a readability measure exists that a person disagreeing with it can argue
    # against" — Gunning fog, which had been in `contract.py` for days and is named in no
    # backtick. A condition can point at a thing rather than a file, and no pattern finds a
    # thing. The record for that is `docs/adr/0014`, and the reader for it is a person.

    assert not fired, (
        "; ".join(fired) + ". A refusal whose reopening condition has fired is a refusal "
        "nobody re-read. Remove the row and grade the requirement, or say why the condition "
        "means something narrower than the file existing."
    )


def test_nothing_the_ledger_proves_is_listed_here_as_ungatable():
    """Two documents about the same requirements, and nothing compared them.

    `ungated` says a requirement is held by a written reason because no gate can hold it.
    `docs/requirements.toml` says PROVEN when a command decides it. Both cannot be true of one
    id, and both were: `EP-179` and `EP-324` sat in this list while the ledger proved them —
    `EP-324` still carried a reason explaining that only the weaker of its two questions was
    checkable, written before the reader for the stronger one existed.

    That is the same shape as a reopening condition nobody re-read, one document over. A
    refusal is only honest while nothing has answered it, and the answer arrives in the other
    file.
    """

    import tomllib

    ledger = tomllib.loads((ROOT / "docs" / "requirements.toml").read_text(encoding="utf-8"))
    graded = {row["id"]: row["verdict"] for row in ledger["requirement"]}

    contradicted = [
        row["id"] for row in register().get("ungated", []) if graded.get(row["id"]) == "PROVEN"
    ]

    assert not contradicted, (
        f"{contradicted} are listed here as held by a reason because no gate can hold them, "
        "and the ledger proves each with a command. Remove the row, or regrade the "
        "requirement — an ungated list that carries proven requirements is a refusal nobody "
        "re-read after somebody answered it."
    )


# Quantities the gate already computes, and the words a row would quote them with. Adding one
# is a line: the name it is written by, and the command that prints the real number.
COUNTED = {
    "labelled": ("python tests/skill_eval.py", r"(\d+)\s+labelled"),
}


def test_no_reason_quotes_a_count_the_gate_computes():
    """`AGENTS.md` already states this rule about itself — "this file names the home and never
    the value, because a doctrine that quotes a number is a doctrine that goes stale without a
    test" — and the register did not follow it.

    `EP-117`'s reason said the golden cases were 160 labelled routing cases. The corpus is 174
    and `just skilleval` has printed the real number on every gate run since the day it was
    written. Nobody recomputed the sentence, because a sentence does not fail.

    So a reason names where the number lives rather than the number. This checks the one
    quantity that has already gone stale, and the table above is how the next is added.
    """

    import re
    import subprocess

    prose = " ".join(
        f"{row.get('reason', '')} {row.get('no_instrument', '')} {row.get('asks', '')}"
        for kind in ("ungated", "indicator", "prohibition")
        for row in register().get(kind, [])
    )

    for word, (command, pattern) in COUNTED.items():
        quoted = re.findall(pattern, prose)
        if not quoted:
            continue
        done = subprocess.run(
            command.split(), capture_output=True, text=True, cwd=str(ROOT), check=False
        )
        real = re.search(pattern, done.stdout)
        assert real, f"{command} no longer prints a {word} count, so this cannot check one"
        assert all(one == real.group(1) for one in quoted), (
            f"the register quotes {quoted} {word} cases and {command} prints {real.group(1)}. "
            "Name where the number lives rather than the number — AGENTS.md says exactly this "
            "about itself and this file was not following it."
        )
