"""The governed cycle's order, checked as data.

A prose skill file cannot be both the declaration and the readable data: rename
`ai-research` and the corpus refusals that name it fail the gate while the cycle's own
sequence rots in silence unchecked. The order lives in `policy/skill-sequence.toml`,
and this file refuses a map that stops matching the tree:
a stage that exists nowhere, phases that run backwards, a fork flag the frontmatter does
not carry, an empty gate, or a duplicate stage. That is AGENTS.md rule 12: a decision
that always comes out the same is code with a check, not a prompt.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from ai_engineering import paths, wiring

ROOT = Path(__file__).resolve().parents[1]


def _map() -> dict:
    return tomllib.loads(paths.policy("skill-sequence.toml").read_text(encoding="utf-8"))


def _frontmatter(folder: Path) -> dict[str, str]:
    """The flat fields of a skill's frontmatter, as strings.

    Only the fields this file compares are read, and they are single-line scalars in the
    tree today; parsing the whole YAML block here would be a second YAML parser for two
    fields.
    """

    body = (folder / "SKILL.md").read_text(encoding="utf-8")
    head = body.split("---", 2)[1]
    fields: dict[str, str] = {}
    for line in head.splitlines():
        if ":" in line and not line.startswith((" ", "#", ">")) and ">-" not in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def _cycle() -> tuple[list[str], list[str], dict, dict]:
    declared = _map()
    return (
        declared.get("first_half", []),
        declared.get("second_half", []),
        declared.get("stages", {}),
        declared.get("gate", {}),
    )


def test_every_stage_in_the_map_exists_somewhere():
    """A stage that exists nowhere is a stage a session would try to load and fail on.

    The halves name skills in the tree, except the one declared verb; anything else is a
    map pointing at a directory or a command that does not exist.
    """

    first, second, stages, _ = _cycle()
    names = first + second
    assert names, "the map declares no cycle at all, so this proves nothing"
    assert len(names) == len(set(names)), "a stage appears twice in the cycle"

    skills = {p.name for p in paths.skills().glob("ai-*")}
    for name in names:
        assert name in stages, f"{name} appears in a half but has no [stages] row"
        if "verb" in stages[name]:
            assert stages[name]["verb"], f"{name} declares an empty verb"
        else:
            assert name in skills, f"{name} is neither a skill in the tree nor a verb"


def test_phases_run_in_order_along_the_cycle():
    """The cycle's phases must never go backwards.

    `discover` before `decide` before `build` before `verify` is the whole claim the
    order makes; a map that puts `ai-ship` before `ai-build` is a map that lies about
    the work. Verb stages (audit) carry no phase and are skipped — the stages beside
    them still bound the sequence.
    """

    first, second, stages, _ = _cycle()
    placed = wiring.phases()
    order = {phase: index for index, phase in enumerate(wiring.PHASE_ORDER)}
    previous = -1
    for name in first + second:
        if "verb" in stages[name]:
            continue
        phase = placed.get(name, "")
        assert phase, f"{name} is a stage with no declared phase"
        index = order[phase]
        assert index >= previous, (
            f"the cycle goes backwards: {name} is {phase} after an earlier stage "
            f"already at {previous}"
        )
        previous = index


def test_a_fork_flag_claims_exactly_what_the_frontmatter_carries():
    """A stage marked fork runs in its own context; the flag must be real.

    `context: fork` without `background: false` runs in the background by default and its
    verdict lands out of order — the contract refuses that pair already, so a map that
    claims fork where the frontmatter does not carry it is a map and a tree disagreeing
    about which stage runs alone.
    """

    first, second, stages, _ = _cycle()
    skills = {p.name: p for p in paths.skills().glob("ai-*")}
    for name in first + second:
        if "verb" in stages[name]:
            continue
        fm = _frontmatter(skills[name])
        claiming = bool(stages[name].get("fork", False))
        carrying = fm.get("context") == "fork" and fm.get("background") == "false"
        assert claiming == carrying, (
            f"{name}: the map says fork={claiming} but the frontmatter carries "
            f"context={fm.get('context')!r} background={fm.get('background')!r}"
        )


def test_the_gate_is_a_real_line_between_the_halves():
    """An empty gate is a cycle with no approval and the halves run together.

    The second half exists only against an approval record carrying the specification's
    exact digest; a gate section that says nothing would let the halves blur back into
    one uninterrupted run, which is the decision this file exists to keep visible.
    """

    first, second, _, gate = _cycle()
    assert first and second, "both halves must exist for a gate to separate them"
    assert gate, "the [gate] section is missing: the line between the halves is not declared"
    text = " ".join(str(value) for value in gate.values())
    assert len(text.split()) >= 5, "the gate says too little to be a real line"


def test_the_router_shows_what_follows_from_the_map():
    """The router is the file a person actually meets, so the order goes there.

    `EP-135` put the phase and the example on the router; the sequence belongs beside
    them. A skill inside the cycle names its next stage, the last stage of the first half
    names the human approval, and a skill outside the cycle carries no "Sigue" line — the
    absence itself says it is standalone.
    """

    body = wiring.router_body("ai-spec", "a description", "decide", "case")
    assert "Sigue en el ciclo: ai-challenge" in body

    body = wiring.router_body("ai-council", "a description", "decide", "case")
    assert "Sigue: la aprobación humana del brief" in body

    body = wiring.router_body("ai-ship", "a description", "verify", "case")
    assert "Sigue: fin del ciclo" in body

    body = wiring.router_body("ai-note", "a description", "verify", "case")
    assert "Sigue" not in body
