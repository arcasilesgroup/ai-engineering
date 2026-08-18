"""Which JSON Schema documents this repository is willing to enforce, and which it refuses.

`intent._Schema` carried 67 surviving mutants across `_check_scalars` and `valid`. It is a
deliberately small validator — a closed keyword set, four types, local `$ref` only — and the
smallness is the design rather than an omission.

The reason is worth stating once. This module enforces the Solution Intent, a file the user
owns and edits, against a schema this repository ships. A general validator would mean
importing one, and an unsupported keyword silently ignored by a validator is a rule the
document appears to state and nobody applies — which is the false green the whole product
exists to remove, arriving through a dependency.

So the constructor refuses at load time rather than at check time. A schema with a keyword
this module cannot enforce is refused before a single document is validated against it,
because the alternative is a schema that looks stricter than it is for as long as nobody
happens to write the field it governs.
"""

from __future__ import annotations

import re

import pytest

from ai_engineering import intent


def _refused(schema: dict) -> str:
    with pytest.raises(intent._UnsupportedSchema) as raised:
        intent._Schema(schema)
    return str(raised.value)


def test_a_schema_this_module_can_enforce_is_accepted():
    """The clean control. Without it every refusal below is satisfied by a constructor that
    refuses everything, which is the passing test this repository exists to refuse."""

    assert intent._Schema({"type": "object", "properties": {"name": {"type": "string"}}})


def test_a_keyword_outside_the_closed_set_is_refused_at_load_time():
    """Not at check time. A schema carrying `multipleOf` looks stricter than it is for as
    long as nobody writes the field it governs, and the day somebody does the rule has never
    been applied and nothing ever said so."""

    assert "keyword" in _refused({"type": "integer", "multipleOf": 3})


def test_a_schema_that_is_not_an_object_is_refused():
    for shape in (None, [], "object", 7):
        with pytest.raises(intent._UnsupportedSchema):
            intent._Schema(shape)  # type: ignore[arg-type]


def test_only_the_four_types_this_module_implements_are_allowed():
    """`number`, `boolean` and `null` are missing on purpose. Accepting a type name whose
    check is not written is how a document passes a validation nobody performed."""

    for name in ("array", "integer", "object", "string"):
        assert intent._Schema({"type": name})
    assert "type" in _refused({"type": "number"})
    assert "type" in _refused({"type": "boolean"})


def test_a_reference_has_to_be_local_and_has_to_resolve():
    """No network and no file. A `$ref` to a URL turns validating a user's file into
    fetching somebody else's document, and a broken local one is a rule with nothing behind
    it."""

    assert "local" in _refused({"$ref": "https://example.invalid/schema.json"})
    assert "local" in _refused({"$ref": "other.json#/$defs/x"})
    assert "unknown" in _refused({"$ref": "#/$defs/missing"})
    assert "unsupported" in _refused({"$ref": "#/$defs/"})
    assert "unsupported" in _refused({"$ref": "#/$defs/a/b"})


def test_a_reference_that_resolves_is_accepted():
    assert intent._Schema({"$defs": {"name": {"type": "string"}}, "$ref": "#/$defs/name"})


def test_a_pattern_is_compiled_at_load_time_rather_than_on_first_use():
    """An invalid expression discovered while checking a document is an exception in the
    middle of a validation, and the person who typed the document did not write the
    schema."""

    with pytest.raises(re.error):
        intent._Schema({"type": "string", "pattern": "([unclosed"})
    assert "pattern" in _refused({"type": "string", "pattern": 7})


@pytest.mark.parametrize("key", ["minItems", "maxItems", "minLength", "maxLength"])
def test_a_bound_has_to_be_a_non_negative_integer(key: str):
    """And a boolean is not one, whatever Python thinks. `minLength: true` is `minLength: 1`
    if it is allowed through, which is a rule nobody wrote applied to every string."""

    assert intent._Schema({key: 0})
    assert key in _refused({key: -1})
    assert key in _refused({key: "3"})
    assert key in _refused({key: True})


def test_required_is_a_list_of_distinct_strings():
    """Distinct, because a repeated name is a schema somebody edited twice and the second
    edit may have meant something the first did not."""

    assert intent._Schema({"required": ["a", "b"]})
    assert "required" in _refused({"required": "a"})
    assert "required" in _refused({"required": [1]})
    assert "required" in _refused({"required": ["a", "a"]})


def test_the_remaining_three_keywords_are_checked_for_their_own_type():
    assert "enum" in _refused({"enum": "one"})
    assert "uniqueItems" in _refused({"uniqueItems": "true"})
    assert "additionalProperties" in _refused({"additionalProperties": "false"})


def test_every_nested_schema_is_checked_by_the_same_rules_as_the_outer_one():
    """A closed keyword set that stops at the top level is a closed set with a hole in it,
    and the hole is exactly where a nested definition would put the keyword nobody
    enforces."""

    assert "keyword" in _refused({"properties": {"a": {"multipleOf": 3}}})
    assert "keyword" in _refused({"$defs": {"a": {"multipleOf": 3}}})
    assert "keyword" in _refused({"allOf": [{"multipleOf": 3}]})
    assert "keyword" in _refused({"oneOf": [{"multipleOf": 3}]})
    assert "keyword" in _refused({"items": {"multipleOf": 3}})
    assert "keyword" in _refused({"if": {"multipleOf": 3}})
    assert "keyword" in _refused({"then": {"multipleOf": 3}})
    assert "keyword" in _refused({"else": {"multipleOf": 3}})
    assert "keyword" in _refused({"not": {"multipleOf": 3}})


def test_a_container_that_is_the_wrong_container_is_refused():
    """`properties` as a list and `allOf` as an object both read as empty to a loop that
    does not check, so every rule inside them would be skipped in silence."""

    assert "properties" in _refused({"properties": []})
    assert "allOf" in _refused({"allOf": {"a": {"type": "string"}}})
