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

    guards = {
        name for handlers in chain.TABLE.values() for name, _ in handlers if name.endswith("_guard")
    }
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
