"""Whether P0 is finished, asked once, against the spec's own words.

Every other test in this suite proves one mechanism. This one asks the question a person
actually has: is the wave done. It answers it by reading the P0 section of the spec,
requiring every sentence in it to be claimed by exactly the evidence that claim rests on,
and requiring that evidence to be present in the tree right now.

Two failure directions, and the second is the one this file exists for. A requirement can
be added to the spec and never implemented — that reddens here because nothing claims the
sentence. Or a later wave's work can be counted as this one's, which is how a wave gets
declared complete while the thing it promised is still missing; so every phrase claimed
here has to come out of the P0 section and appear nowhere in P1 to P5, and the markers of
those waves may not be claimed at all.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "010-governed-agentic-engineering-foundation" / "spec.md"

# Requirement, the words in the spec that state it, and where in this repository it is.
# Every phrase is a verbatim substring of the P0 section once its line wrapping is undone,
# and every needle is a string that is really in the file named beside it — a requirement
# whose evidence is a path that exists but says nothing is a requirement nobody checked.
P0: dict[str, tuple[str, str, str]] = {
    "identity": (
        "P0 lands the identity",
        "docs/adr/0006-governed-mission.md",
        "mission",
    ),
    "intent": (
        "Intent",
        "policy/intent-v1.schema.json",
        "urn:ai-engineering:intent",
    ),
    "madr": ("MADR contracts", "policy/madr-v1.schema.json", "urn:ai-engineering:madr"),
    "spec-flow": ("the single `ai-spec` flow", ".agents/skills/ai-spec/SKILL.md", "ai-spec"),
    "capability-manifest": (
        "capability manifest",
        "policy/capability-manifest.schema.json",
        "capabilit",
    ),
    "outcome-schema": (
        "outcome/check/evidence/JSON schemas",
        "policy/outcome-v1.schema.json",
        "x-outcome-policy",
    ),
    "evidence-schema": (
        "outcome/check/evidence/JSON schemas",
        "policy/check-evidence-v1.schema.json",
        "x-evidence-policy",
    ),
    "acceptance-schema": (
        "outcome/check/evidence/JSON schemas",
        "policy/risk-acceptance-v1.schema.json",
        "x-acceptance-policy",
    ),
    "hard-renames": ("hard renames", "CHANGELOG.md", "hooks/no_verify_guard.py"),
    "report-digest": ("`report digest`", "src/ai_engineering/report.py", 'add_parser("digest")'),
    "invalid-fixtures-first": (
        "with invalid fixtures red before valid implementations",
        "tests/fixtures/risk-acceptance-v1.json",
        "invalid",
    ),
    "frozen-waves": (
        "It freezes the P1-P5 contracts below.",
        "specs/010-governed-agentic-engineering-foundation/spec.md",
        "### P5 —",
    ),
    # The rename happened and is recorded; the guard it renamed has since been deleted for
    # blocking three times against 670 bypasses. So the proof moves from the file to the
    # record — which is where a hard rename's proof belonged anyway, because a file proves
    # only the name it currently has and never the name somebody used to type.
    "guard-rename": (
        "P0 hard-renames `design_gate` to `change_scope_guard`, with no alias, because the "
        "guard enforces approved scope and plan presence rather than judging design.",
        "CHANGELOG.md",
        "design_gate",
    ),
    "release-lanes": (
        "P0 retains the current trusted-publishing, provenance, dependency-audit, "
        "installed-wheel test and security-analysis lanes.",
        ".github/workflows/release.yml",
        "id-token: write",
    ),
    "pinned-dependencies": (
        "Every new dependency is exactly pinned in its governing lock or action reference.",
        ".github/workflows/check.yml",
        'GITLEAKS_VERSION: "8.30.1"',
    ),
    "missing-lane-incomplete": (
        "A removed, skipped or missing required lane is `INCOMPLETE` and blocks release",
        ".github/workflows/check.yml",
        "INCOMPLETE",
    ),
    "lanes-supplement": (
        "a new lane supplements rather than silently replaces existing proof.",
        "tests/test_quality_gate.py",
        "b81028e7c88d58dd70c2148f572d913e3cfba4cde5754fb311e97f4704bafb98",
    ),
}

# Every schema P0 shipped, named rather than globbed. See the closure rule below.
P0_SCHEMAS = frozenset(
    {
        "policy/capability-manifest.schema.json",
        "policy/check-evidence-v1.schema.json",
        "policy/intent-v1.schema.json",
        "policy/madr-v1.schema.json",
        "policy/outcome-v1.schema.json",
        "policy/risk-acceptance-v1.schema.json",
    }
)

# The words that belong to a later wave. None of them is P0's to claim, and the alias P0
# removed is here too: a rename with an alias left behind is not a rename.
LATER_WAVES = (
    "surface adapter",
    "merge_group",
    "SBOM",
    "external pilot",
    "provider-neutral semantic review",
    "design_gate.py",
)


def _sections() -> dict[str, str]:
    """Each wave's contract as one reflowed paragraph, keyed by its wave."""

    text = SPEC.read_text(encoding="utf-8")
    found = list(re.finditer(r"^### (P[0-5]) — .*$", text, flags=re.MULTILINE))
    ends = [*(match.start() for match in found[1:]), text.index("\n## ", found[-1].start())]
    return {
        match.group(1): " ".join(text[match.end() : end].split())
        for match, end in zip(found, ends, strict=True)
    }


def uncovered(section: str, claims: list[str]) -> list[str]:
    """Everything the contract states that no claim accounts for.

    It splits as finely as the prose allows — full stops, semicolons, commas and `and` —
    because this contract lands eleven separate things in one sentence, and at sentence
    granularity any one of them could be dropped from the map while its neighbours kept
    the sentence looking covered.

    The test is one-directional on purpose. Accepting a unit because some claim is a
    substring *of it* was measured letting three invented requirements through, including
    two naming later waves: `Intent`, `hard renames` and `capability manifest` are short
    enough that almost any new sentence contains one. A claim has to cover the statement,
    not merely appear somewhere inside it."""

    return [
        unit
        for raw in re.split(r"(?<=[.;]) |, | and ", section)
        if (unit := raw.strip().rstrip(".,;")) and not any(unit in claim for claim in claims)
    ]


def test_the_coverage_rule_rejects_a_requirement_nothing_claims():
    """The rule that decides whether the map is complete, held against text it has never
    seen — otherwise it is only ever exercised on prose already known to pass."""

    claims = ["Intent", "hard renames", "capability manifest"]
    invented = (
        "P0 ships a signed SBOM alongside the Intent.",
        "P0 must publish a reproducible build attestation for every hard renames artifact.",
        "P0 delivers an external pilot with a capability manifest.",
        "P0 encrypts the chain at rest.",
    )
    for sentence in invented:
        assert uncovered(sentence, claims), f"absorbed silently: {sentence}"
    assert not uncovered("Intent", claims)


def test_every_p0_requirement_is_claimed_by_evidence_that_exists():
    waves = _sections()
    p0 = waves["P0"]
    later = " ".join(body for wave, body in waves.items() if wave != "P0")

    for name, (phrase, where, needle) in P0.items():
        assert phrase in p0, f"{name} claims words the P0 contract does not contain"
        # A term may well recur — `report digest` lands in P0 and is constrained again in
        # P2 — so the disjointness that matters is the whole statement. The sentence a
        # claim rests on has to be P0's own, because a later wave's sentence counted here
        # is exactly how a wave gets declared finished on work nobody in it did.
        statement = next(part for part in p0.split(". ") if phrase in part + ".")
        assert statement not in later, f"{name} rests on a sentence a later wave states"
        proof = ROOT / where
        assert proof.exists(), f"{name} rests on {where}, which is not in the tree"
        assert needle in proof.read_text(encoding="utf-8"), f"{where} does not hold {name}"

    # Coverage, the other way round: a requirement the contract states and nothing claims.
    # The contract names its schemas as one phrase, so they cannot be told apart by the
    # words alone; the set P0 shipped is named instead. Both directions bite. A schema
    # added to that set and mapped by nothing is the hole this catches, and a schema a
    # later wave ships is not P0's to claim — the second half is why this list is frozen
    # rather than globbed, because a glob would have quietly enrolled P1's first schema
    # into P0's evidence the moment it landed.
    claimed_paths = {where for _, where, _ in P0.values()}
    assert claimed_paths >= P0_SCHEMAS, f"unclaimed: {sorted(P0_SCHEMAS - claimed_paths)}"
    shipped_later = {
        f"policy/{schema.name}" for schema in (ROOT / "policy").glob("*.schema.json")
    } - P0_SCHEMAS
    assert not (shipped_later & claimed_paths), sorted(shipped_later & claimed_paths)

    assert not uncovered(p0, [phrase for phrase, _, _ in P0.values()])

    # A wave contract that names a later wave's work is claiming it, whatever the map says.
    for marker in LATER_WAVES:
        assert marker.lower() not in p0.lower(), f"the P0 contract names {marker}"


def test_p0_claims_nothing_that_belongs_to_a_later_wave():
    """The failure this repository is built against, applied to itself: a wave declared
    finished on work that was never in it. P1 to P5 are frozen contracts and none of them
    is evidence for anything here."""

    claimed = " ".join(
        f"{phrase} {where} {needle}" for phrase, where, needle in P0.values()
    ).lower()
    for marker in LATER_WAVES:
        assert marker.lower() not in claimed, f"P0 claims {marker}, which is not P0's"
    assert not (ROOT / "hooks" / "design_gate.py").exists()

    # And it is answered by the same command CI runs, rather than by a file somebody has to
    # remember to run: `just check` calls `test`, and `test` runs the whole tests directory.
    recipe = (ROOT / "justfile").read_text(encoding="utf-8")
    # The list is read rather than pinned as one string: `check` grew a `register` recipe in
    # P5 and this assertion is about `test` being in it, not about the order of the others.
    called = recipe.split("\ncheck:", 1)[1].splitlines()[0].split()
    assert "test" in called and "lint" in called and "security" in called, called
    assert "\ntest:\n    uv run --with {{pytest}} --with {{xdist}} pytest -q -n auto\n" in recipe


def test_the_gate_checks_the_page_is_about_this_tree():
    """A generated document nothing verifies is a document that goes stale in a week.

    The page under `docs/` is the one thing here written for a person rather than for a
    machine, and the whole reason it can be trusted after nobody has looked at it for a
    month is that the gate recomputes its digest. Which means the gate has to run it.

    Before the receipt recipe, because that one writes last and a check after it would
    record a run that had not finished."""

    recipe = (ROOT / "justfile").read_text(encoding="utf-8")
    called = recipe.split("\ncheck:", 1)[1].splitlines()[0].split()

    assert "intent-page" in called, called
    assert called.index("intent-page") < called.index("ran"), called
    assert "\nintent-page:\n" in recipe
    # And it is the module's own answer, not a second implementation of freshness.
    body = recipe.split("\nintent-page:\n", 1)[1].split("\n\n", 1)[0]
    assert "solution_intent" in body and "--check" in body
