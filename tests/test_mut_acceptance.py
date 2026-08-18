"""Every refusal `_validate_field` and `validate_record` can make, one at a time.

Between them these two carried 103 of the 533 mutants that survived over `acceptance.py`,
the largest single pool in the tree. `tests/test_acceptance.py` exercises them through a
corpus of whole records, which proves the shapes a real record takes; it leaves the shapes a
malformed one takes to whatever the corpus happens to contain.

Every branch here refuses, and they refuse with different words on purpose. A record that is
not JSON, one that is JSON but not canonical, one whose fields are right and whose digest is
wrong, and one whose value is three bytes over a limit are four different conversations with
whoever wrote it — and a reader who gets "malformed" for all four learns nothing about which.

These call both functions directly against the real schema. Using a fixture schema would
prove this code agrees with a fixture, and the whole design of `validate_record` is that the
schema document is the contract rather than a restatement of it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ai_engineering import acceptance

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "policy" / "risk-acceptance-v1.schema.json").read_text("utf-8"))

DIGEST = "sha256:" + "a" * 64
OTHER = "sha256:" + "b" * 64


def _record(**overrides: Any) -> dict[str, Any]:
    record = {
        "schema": "urn:ai-engineering:risk-acceptance:1",
        "schema_version": "1",
        "id": "R-010-01",
        "spec": "010",
        "spec_digest": DIGEST,
        "finding": "the native backend cannot prove power-loss durability",
        "severity": "medium",
        "authority_role": "repository maintainer",
        "accepted": "2026-08-14",
        "expires": "2026-11-14",
        "renewals": 0,
        "renews": "",
        "renews_digest": "",
        "justification": "The supported rename APIs promise no survival across power loss.",
        "evidence": {"path": "specs/010-x/spec.md", "content_digest": OTHER},
        "follow_up": "",
        "record_digest": DIGEST,
    }
    record.update(overrides)
    return record


def _sealed(**overrides: Any) -> bytes:
    """A record whose digest is its own, so a test about one field is about that field.

    Without this every case below would refuse on the digest first and prove nothing about
    the thing it set out to check — which is the shape of green test that measures the
    order of the checks rather than any of them.
    """

    record = _record(**overrides)
    record["record_digest"] = acceptance.record_digest(record)
    return acceptance.canonical_bytes(record)


def _refused(body: bytes) -> acceptance.Refusal:
    with pytest.raises(acceptance.Refusal) as raised:
        acceptance.validate_record(body, "the record", SCHEMA)
    return raised.value


def test_a_record_that_holds_together_is_accepted():
    """The clean control. Without it every refusal below is satisfied by a function that
    refuses everything, which is the passing test this repository exists to refuse."""

    assert acceptance.validate_record(_sealed(), "the record", SCHEMA) == json.loads(_sealed())


# --- the four ways a document fails before any field is looked at -------------------


def test_bytes_that_are_not_json_are_refused_as_not_json():
    refusal = _refused(b"not json at all")

    assert refusal.code == "ACCEPTANCE_MALFORMED"
    assert "not JSON" in str(refusal)


def test_json_that_is_not_an_object_is_refused_for_being_the_wrong_shape():
    """A list of records is a plausible mistake and would otherwise reach `set(record)`,
    which answers about the indices of a list without complaining."""

    refusal = _refused(b"[]")

    assert "not one JSON object" in str(refusal)


def test_a_record_that_is_not_canonical_is_refused_even_though_it_parses():
    """Whitespace, key order and escaping all change the bytes without changing the
    meaning, and the digest is over the bytes. A record accepted in a second spelling is a
    record whose digest proves nothing, because there would be a spelling for every value.
    """

    record = _record()
    record["record_digest"] = acceptance.record_digest(record)
    loose = json.dumps(record, indent=2).encode("utf-8")

    assert "not canonical JSON" in str(_refused(loose))


def test_a_missing_field_and_an_extra_field_are_the_same_refusal():
    """The field set is closed in both directions. An extra key is how a field nobody
    reviewed arrives, and a missing one is how a field somebody relies on disappears."""

    missing = _record()
    del missing["follow_up"]
    missing["record_digest"] = acceptance.record_digest(missing)

    extra = _record(surprise="x")
    extra["record_digest"] = acceptance.record_digest(extra)

    for body in (acceptance.canonical_bytes(missing), acceptance.canonical_bytes(extra)):
        assert "exactly the closed fields" in str(_refused(body))


# --- _validate_field, one branch each ------------------------------------------------


def test_an_integer_field_holding_a_string_is_refused():
    assert "non-integer renewals" in str(_refused(_sealed(renewals="0")))


def test_a_boolean_is_not_an_integer_here_even_though_python_says_it_is():
    """`isinstance(True, int)` is true in Python and false in JSON Schema. Without the
    explicit exclusion, `renewals: true` would validate and then be counted."""

    assert "non-integer renewals" in str(_refused(_sealed(renewals=True)))


def test_an_integer_below_its_minimum_is_refused_for_its_range():
    assert "outside its range" in str(_refused(_sealed(renewals=-1)))


def test_an_object_field_missing_a_child_is_refused_before_its_children_are_read():
    """The set comparison comes first on purpose. Walking the children of an object with a
    key missing raises `KeyError` from inside the schema lookup, which reaches a person as
    a traceback rather than as a refusal naming the field."""

    assert "malformed evidence" in str(_refused(_sealed(evidence={"path": "x"})))


def test_an_object_field_that_is_not_an_object_is_refused():
    assert "malformed evidence" in str(_refused(_sealed(evidence="specs/010-x/spec.md")))


def test_a_child_of_an_object_is_validated_by_its_own_name():
    """The recursion has to carry the path or the message names `evidence` for a fault in
    `evidence.content_digest`, and the person re-reads the wrong line."""

    body = _sealed(evidence={"path": "specs/010-x/spec.md", "content_digest": "nope"})

    assert "evidence.content_digest" in str(_refused(body))


def test_a_string_field_holding_a_number_is_refused():
    assert "non-string finding" in str(_refused(_sealed(finding=7)))


def test_a_control_character_inside_a_string_is_refused_on_its_own():
    """Separate from the pattern check, and before it. A record carrying an escape sequence
    is a record that renders as something other than what it says in any terminal that
    prints it, and several fields here have no pattern to catch it."""

    assert "control character" in str(_refused(_sealed(finding="a finding\u0007bell")))


def test_a_const_field_holding_something_else_is_refused():
    assert "unexpected schema" in str(_refused(_sealed(schema="urn:something:else:1")))


def test_a_value_outside_an_enumeration_is_refused_as_undefined():
    assert "undefined severity" in str(_refused(_sealed(severity="apocalyptic")))


def test_a_value_that_fails_its_pattern_is_refused_as_malformed():
    assert "malformed id" in str(_refused(_sealed(id="R-10-1")))


def test_an_empty_value_where_a_length_is_required_is_refused_as_empty():
    """Distinct words from "malformed", because an empty field is nearly always somebody
    who meant to come back to it and a malformed one is nearly always a misunderstanding."""

    assert "empty justification" in str(_refused(_sealed(justification="")))


def test_a_date_that_is_not_one_exact_date_is_refused():
    """Not merely a date-shaped string. `2026-02-30` matches every pattern anybody writes
    for a date and is not a day that exists."""

    assert "not one exact date" in str(_refused(_sealed(accepted="2026-02-30")))


# --- validate_record, after the fields are individually sound ------------------------


def test_a_value_over_its_byte_limit_is_refused_even_when_its_pattern_holds():
    """The limits are in bytes and the pattern is in characters, so a field can pass every
    other check and still be too large to store. Measured in UTF-8, because that is what
    goes on disk, and a character count would let a field of accented text through at up to
    twice the size."""

    limits = SCHEMA["x-utf8-byte-limits"]
    name, limit = next(iter(limits.items()))
    if "." in name:
        pytest.skip(f"{name} is nested and this case wants a top-level field")

    assert "byte bound" in str(_refused(_sealed(**{name: "a" * (limit + 1)})))


def test_a_record_whose_digest_is_not_its_own_is_a_checksum_refusal_not_a_malformed_one():
    """A different code, because this is the only refusal that says somebody edited a
    record after it was sealed rather than wrote one badly."""

    refusal = _refused(acceptance.canonical_bytes(_record(record_digest=OTHER)))

    assert refusal.code == "ACCEPTANCE_CHECKSUM"
    assert "its own record digest" in str(refusal)


def test_an_expiry_before_its_acceptance_is_refused():
    """A window that closes before it opens. Every reader downstream asks whether today is
    inside it and gets a consistent, meaningless no."""

    assert str(_refused(_sealed(accepted="2026-08-14", expires="2026-08-13")))
