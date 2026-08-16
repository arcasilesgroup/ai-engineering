"""The threat model, held to the tree it describes.

`ai-security` step 1 tells every user to write the boundary and the data down before
anything else, and this project had never written its own. An audit put it plainly: the
framework demands a threat model from everybody and has none. A security product with no
threat model is the shape it exists to refuse.

So it is data rather than prose, and this is what makes it data. Every row names the file
that holds its control and the test that proves the control can still say no, and both are
resolved against the tree. Delete a guard and the build goes red naming the boundary it left
open, which is the only difference between a threat model and a page somebody wrote once.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "policy" / "threat-model.toml"

FIELDS = ("id", "asset", "controlled_by", "harm", "control", "check")


def boundaries() -> list[dict]:
    return tomllib.loads(MODEL.read_text(encoding="utf-8"))["boundary"]


def test_the_framework_has_a_threat_model_about_itself():
    rows = boundaries()
    assert len(rows) >= 12, f"{len(rows)} boundaries is fewer than this framework has"
    assert len({row["id"] for row in rows}) == len(rows), "a boundary appears twice"


@pytest.mark.parametrize("row", boundaries(), ids=lambda row: row["id"])
def test_every_boundary_says_all_five_things_and_names_a_control_that_is_there(row):
    """A row missing any of the five is a boundary somebody half thought about.

    `harm` is the field that matters most and the one easiest to leave out: without it a row
    says a control exists and never says what happens when it does not, which is a threat
    model written from the answers rather than from the risks."""
    for field in FIELDS:
        assert str(row.get(field, "")).strip(), f"{row.get('id')}: no {field}"

    assert (ROOT / row["control"]).is_file(), (
        f"{row['id']}: the control at {row['control']} is not in this tree, so this boundary "
        f"is described and unheld"
    )
    assert (ROOT / row["check"]).is_file(), (
        f"{row['id']}: the check at {row['check']} is not in this tree, so nothing proves the "
        f"control at {row['control']} can still say no"
    )


def test_every_guard_in_the_dispatcher_is_a_boundary_this_model_names():
    """The direction that catches the gap rather than the drift.

    Checking that each row names a real file finds a deleted control. It cannot find a
    control this model never mentioned — a guard shipped without anybody writing down what it
    is for. So the dispatcher's own list of guards is read here, and a guard missing from the
    model reds the build naming itself."""
    import chain

    # Every hook that is not telemetry, and not only the ones spelled `*_guard`. A reviewer
    # defeated the suffix version twice: a blocking hook named `secret_scan` shipped with no
    # row and the file stayed green, and deleting `self_protect`'s own row — a blocking
    # PreToolUse hook that is in the model — went unnoticed for the same reason. A check that
    # only sees the handlers somebody remembered to name correctly is a naming convention
    # wearing a control's clothes.
    guards = {name for handlers in chain.TABLE.values() for name, _ in handlers} - chain.TELEMETRY
    named = {Path(row["control"]).stem for row in boundaries()}
    missing = sorted(guards - named)
    assert not missing, f"guards this threat model never mentions: {missing}"


def test_a_boundary_whose_control_is_not_built_says_so_in_its_own_words():
    """`reason` is how this file stays honest instead of complete.

    The supply-chain row attests provenance and produces no SBOM, and the requirements that
    ask for one need a published release. A threat model that listed only solved problems
    would be a marketing page, so a row may record a half-built control — and when it does,
    it has to say which half."""
    partial = [row for row in boundaries() if row.get("reason")]
    assert partial, "no boundary records a control that is not finished, which is unlikely"
    for row in partial:
        assert len(str(row["reason"]).split()) >= 12, f"{row['id']}: the reason says too little"


def test_the_security_skill_points_at_it_rather_than_asking_for_one_it_has_not_written():
    """Rule 9 and the cobbler's children. `ai-security` demands a threat model from its
    reader; the reader is entitled to see ours."""
    skill = (ROOT / ".agents" / "skills" / "ai-security" / "SKILL.md").read_text(encoding="utf-8")
    assert "policy/threat-model.toml" in skill, (
        "ai-security asks every user for a threat model and does not show them this one"
    )


def test_the_router_a_person_meets_names_the_phase_and_shows_an_example():
    """EP-135, and the half an independent verifier found missing.

    The requirement is that the *surfaces* show the skills by the five phases, with a "use
    it / not for / example" beside each. The phase was declared, required by a schema, and
    printed by the gate — so the only person who ever saw the map was a developer running
    `just check`, never somebody who installed the wheel. The router is the file a person
    actually meets on their own surface, so that is where it goes.

    Neither field is a restatement: the phase is read from the one file that lists all
    fifteen capabilities, and the example is the first labelled case from the corpus the
    routing evaluation runs on every gate. An example nothing checks is the sentence that
    goes stale first."""
    from ai_engineering import wiring

    placed = wiring.phases()
    assert set(placed.values()) >= {"discover", "decide", "plan", "build", "verify"}

    for skill in sorted((ROOT / ".agents" / "skills").glob("ai-*")):
        phase = placed.get(skill.name, "")
        case = wiring.example(skill)
        assert phase, f"{skill.name} is a skill the manifest gives no phase"
        assert case, f"{skill.name} has no labelled case to show a person"

        body = wiring.router_body(skill.name, "a description", phase, case)
        assert f"# {skill.name} · {phase}" in body
        assert case in body
        # And still no second copy of the instructions: the router routes.
        assert "$ARGUMENTS" in body and "## Steps" not in body


def test_a_skill_with_no_declared_phase_says_so_rather_than_reading_as_one():
    """Fail visible rather than fail silent. A router that simply omitted the phase would
    look exactly like a catalogue that had never been mapped."""
    from ai_engineering import wiring

    body = wiring.router_body("ai-something", "a description", "", "")
    assert "phase not declared" in body


# Read by something that is not a test, or argued for. `policy/` is data and data is only
# governance when something consults it — the whole `policy/adapters/` directory sat beside a
# schema its only consumer read backwards, and the reason nobody noticed is that a data file
# has no compiler. This is that question asked of every file at once.
POLICY_EXEMPT = {
    "policy/adapters": "read as a directory by `hooks/chain.py`, which globs it rather than "
    "naming any one file — an adapter is added by dropping it in, which is the point",
    "policy/pilot-register.toml": "read by `tests/pilot_register.py`, which the `register` "
    "recipe runs as a step of `just check` rather than as a test — the reader lives under "
    "tests/ and runs as a gate, and `just register` is the command that prints it",
    "policy/quality-gate.toml": "read by `tests/quality_gate.py`, in the same shape as the "
    "pilot register: a gate step whose reader happens to live beside the suite, and the "
    "workflow that consumes its verdict names the reader rather than the data",
    "policy/envelope-v1.schema.json": "nothing validates against it, and that is a real gap "
    "rather than a shape. The envelope is emitted by `cli.py` and the schema is enforced by "
    "the suite, so a wrong envelope reds the gate and never a user's run. Closing it means "
    "validating on the emitting path, which is a change to what every JSON call costs",
    "policy/surface-adapter-v1.schema.json": "nothing in the product validates an adapter "
    "against it: the dispatcher reads the directory raw because it runs on a 20 ms budget "
    "and may not import the package. Recorded as a half-built control in the "
    "`dispatcher-input` boundary, with what is and is not covered",
}


def test_every_policy_file_is_read_by_something_that_is_not_a_test():
    """The generalisation of a defect this repository has now found twice.

    A schema nothing validates against, a table nothing consults, a register nothing prints:
    each is a document that reads like a control, and `policy/` is where they accumulate
    because a data file cannot fail to compile. So the question is asked of the whole
    directory, and the answer has to be a reader in the product — `src/`, `hooks/`,
    `surfaces/`, the justfile or a workflow — because a file only tests read is a file that
    governs the tests.
    """
    import subprocess

    where = ("src", "hooks", "surfaces", "justfile", ".github")
    orphans = []
    for path in sorted((ROOT / "policy").rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if any(relative == prefix or relative.startswith(prefix + "/") for prefix in POLICY_EXEMPT):
            continue
        # A line that opens the file, not a line that mentions it. Searching for the bare
        # name passed the two purest instances of what this test exists to find: the adapter
        # schema is named only in a docstring and a comment and nothing validates against it,
        # and the pilot register is named only in a docstring. It also passed a planted
        # `policy/settings.json`, because that name appears all over the installer. A
        # mention is not a reader, and this is the difference between the two.
        found = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "grep",
                "-lE",
                # The name inside a quoted string, which is what a read looks like and what
                # prose does not: this repository writes a path in backticks when it is
                # talking about it and in quotes when it is opening it. A keyword-and-name
                # pattern was not enough — it still passed the adapter schema and the pilot
                # register, both named only in a docstring, which are the two purest
                # instances of the thing this test exists to find.
                rf"[\"'][^\"']*{path.name}",
                "--",
                *where,
            ],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.split()
        if not found:
            orphans.append(relative)

    assert not orphans, (
        f"policy files nothing in the product reads: {orphans}. Either give each one a "
        f"reader, or say in POLICY_EXEMPT why it has none — an unexplained absence is how "
        f"a document comes to read like a control."
    )


def test_the_exemptions_name_a_directory_that_is_there_and_say_why():
    """An exemption list is the second place a claim can rot. Each entry has to point at
    something and carry an argument long enough to disagree with."""
    for prefix, why in POLICY_EXEMPT.items():
        assert (ROOT / prefix).exists(), f"{prefix} is exempted and is not there"
        assert len(why.split()) >= 12, f"{prefix}: the reason says too little to argue with"


def test_the_security_lane_counts_the_boundaries_a_person_can_see(tmp_path, capsys, monkeypatch):
    """The threat model's own reader. Every path in it is resolved by the tests above, and
    that made it a file only the suite ever opened — so somebody running the security lane
    is told how many boundaries there are and how many carry a whole control.

    Absent is declined and present-and-unreadable is INCOMPLETE, which is the rule this
    module already applies to an engine: a repository that has not written a threat model is
    not failing a check, and demanding one from every consumer would make this lane an
    opinion."""
    from ai_engineering import scan

    monkeypatch.setattr(scan, "BASELINE", ())
    monkeypatch.setattr(scan, "CROSS_CHECKS", ())

    assert scan.baseline(tmp_path) == 0
    assert "SKIPPED     boundaries" in capsys.readouterr().out

    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "threat-model.toml").write_text("[[boundary\n", encoding="utf-8")
    assert scan.baseline(tmp_path) == 1
    assert "INCOMPLETE  boundaries" in capsys.readouterr().out

    # And this repository's own, counted from the file rather than written down here. The
    # run still exits 1, because the engines are stubbed out and a coverage question nobody
    # can answer is INCOMPLETE — which is the rule working, not a failure of this fixture.
    assert len(scan.model(ROOT)) == len(boundaries())
    assert scan.baseline(ROOT) == 1
    printed = capsys.readouterr().out
    assert f"{len(boundaries())} declared" in printed
    assert "INCOMPLETE  coverage" in printed

    # The second half of that line carries the only judgement in it, and nothing read it:
    # replacing `held` with every row left the suite green. A boundary whose control is half
    # built is counted apart, and the count says so.
    partial = [row for row in boundaries() if row.get("reason")]
    assert partial, "no boundary records a half-built control, so this proves nothing"
    assert f"{len(boundaries()) - len(partial)} with a control this tree holds whole" in printed

    # And a threat model that is readable and declares nothing is not an unreadable one.
    (tmp_path / "policy" / "threat-model.toml").write_text("# nothing yet\n", encoding="utf-8")
    assert scan.baseline(tmp_path) == 0
    assert "OBSERVED    boundaries    0 declared" in capsys.readouterr().out


@pytest.mark.parametrize(
    "body",
    (
        "[boundary]\nid = 'x'\n",  # the likeliest typo this format has
        "boundary = 'later'\n",
        "boundary = 5\n",
        "[[boundary]]\nid = 'x'\n[[other]]\n",
    ),
)
def test_a_threat_model_shaped_wrongly_is_a_verdict_and_never_a_traceback(tmp_path, body):
    """`[boundary]` instead of `[[boundary]]` produced a list of a string's characters and
    then an AttributeError out through the security gate — the same defect this module had
    just fixed in its SARIF reader, committed while fixing it. A gate that terminates with a
    traceback has not decided anything."""
    from ai_engineering import scan

    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "threat-model.toml").write_text(body, encoding="utf-8")
    read = scan.model(tmp_path)
    assert read is None or all(isinstance(row, dict) for row in read)
