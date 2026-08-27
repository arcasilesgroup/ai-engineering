"""Tests for spec 036 / B-036-1: the decision-boundary classifier.

A decision classifies its boundary: Always, Ask-first or Never inside the declared scope,
None out of it — indexed U0 (undeclared or malformed declarations) or U1..
(out-of-declaration) — reporting CANNOT DECIDE and blocking rather than guessing
(wayfinder W-02: Unknown -> CANNOT JUDGE). The classifier reads declarations from the
capability-manifest surface and never defines a second permission model.
"""

from __future__ import annotations

from ai_engineering import decision_boundary as db


def test_in_declaration_classifies_deterministically():
    declarations = {"promote": "always", "merge": "ask_first", "delete": "never"}
    assert db.classify("promote", declarations).verdict == "Always"
    assert db.classify("merge", declarations).verdict == "Ask-first"
    assert db.classify("delete", declarations).verdict == "Never"
    for name in declarations:
        result = db.classify(name, declarations)
        assert result.reason is None
        assert not result.blocks


def test_out_of_declaration_is_undecidable_and_blocks():
    declarations = {"promote": "always"}
    result = db.classify("delete", declarations)
    assert result.verdict is None
    assert result.reason == "U1"
    assert result.blocks


def test_undeclared_or_malformed_declarations_read_as_u0():
    assert db.classify("anything", None).reason == "U0"
    assert db.classify("anything", {}).reason == "U0"
    assert db.classify("x", {"x": "sometimes"}).reason == "U0"
    assert db.classify("anything", None).verdict is None


def test_never_coerces_an_undecided_class():
    # The clean control: a None verdict is never turned into a class downstream.
    result = db.classify("delete", {"promote": "always"})
    assert result.blocks
    assert result.verdict is None


def test_capability_manifest_surface_maps_gate_to_class():
    manifest = {
        "schema": "urn:ai-engineering:capability-manifest:1",
        "schema_version": "1",
        "capabilities": [
            {"id": "ai-explore", "modes": [{"id": "default", "human_gate": "never"}]},
            {"id": "ai-research", "modes": [{"id": "cited-web", "human_gate": "before_network"}]},
        ],
    }
    mapping = db.from_capability_manifest(manifest)
    assert mapping["ai-explore:default"] == "Always"
    assert mapping["ai-research:cited-web"] == "Ask-first"


def test_unknown_or_missing_gate_maps_to_none_and_blocks():
    # A gate outside the declared vocabulary must not be decided as a class: it is the
    # caller's U0, matching capability.py's fail-closed posture on the same input.
    manifest = {
        "schema": "urn:ai-engineering:capability-manifest:1",
        "schema_version": "1",
        "capabilities": [
            {"id": "ai-x", "modes": [{"id": "m", "human_gate": "soemtimes"}]},
            {"id": "ai-y", "modes": [{"id": "m"}]},
        ],
    }
    mapping = db.from_capability_manifest(manifest)
    assert mapping["ai-x:m"] is None
    assert mapping["ai-y:m"] is None
    assert db.classify("ai-x:m", {"ai-x:m": mapping["ai-x:m"]}).reason == "U0"
