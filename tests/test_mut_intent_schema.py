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


@pytest.mark.parametrize(
    ("schema", "says"),
    [
        # Not at check time. A schema carrying `multipleOf` looks stricter than it is for as
        # long as nobody writes the field it governs, and the day somebody does the rule has
        # never been applied and nothing said so.
        pytest.param(
            {"type": "integer", "multipleOf": 3}, "keyword", id="a keyword outside the set"
        ),
        # A closed set that stops at the top level is a closed set with a hole in it, and
        # the hole is exactly where a nested definition would put the keyword nobody enforces.
        *[
            pytest.param(nest, "keyword", id=f"the same keyword under {where}")
            for where, nest in (
                ("properties", {"properties": {"a": {"multipleOf": 3}}}),
                ("$defs", {"$defs": {"a": {"multipleOf": 3}}}),
                ("allOf", {"allOf": [{"multipleOf": 3}]}),
                ("oneOf", {"oneOf": [{"multipleOf": 3}]}),
                ("items", {"items": {"multipleOf": 3}}),
                ("if", {"if": {"multipleOf": 3}}),
                ("then", {"then": {"multipleOf": 3}}),
                ("else", {"else": {"multipleOf": 3}}),
                ("not", {"not": {"multipleOf": 3}}),
            )
        ],
        # `number`, `boolean` and `null` are missing from the type set on purpose: accepting
        # a type name whose check is not written is how a document passes a validation nobody
        # performed.
        pytest.param({"type": "number"}, "type", id="a type this module does not implement"),
        pytest.param({"type": "boolean"}, "type", id="another one"),
        # No network and no file. A `$ref` to a URL turns validating a user's file into
        # fetching somebody else's document; a broken local one is a rule with nothing behind it.
        pytest.param({"$ref": "https://example.invalid/s.json"}, "local", id="a remote reference"),
        pytest.param({"$ref": "other.json#/$defs/x"}, "local", id="a reference into another file"),
        pytest.param(
            {"$ref": "#/$defs/missing"}, "unknown", id="a local reference that resolves to nothing"
        ),
        pytest.param({"$ref": "#/$defs/"}, "unsupported", id="a reference naming nothing"),
        pytest.param({"$ref": "#/$defs/a/b"}, "unsupported", id="a reference into a definition"),
        pytest.param(
            {"type": "string", "pattern": 7}, "pattern", id="a pattern that is not a string"
        ),
        # Distinct, because a repeated name is a schema somebody edited twice and the second
        # edit may have meant something the first did not.
        pytest.param({"required": "a"}, "required", id="required as a string"),
        pytest.param({"required": [1]}, "required", id="required holding a number"),
        pytest.param({"required": ["a", "a"]}, "required", id="required repeating a name"),
        pytest.param({"enum": "one"}, "enum", id="an enum that is not a list"),
        pytest.param({"uniqueItems": "true"}, "uniqueItems", id="uniqueItems as a string"),
        pytest.param(
            {"additionalProperties": "false"},
            "additionalProperties",
            id="a string where a bool goes",
        ),
        # `properties` as a list and `allOf` as an object both read as empty to a loop that
        # does not check, so every rule inside them would be skipped in silence.
        pytest.param({"properties": []}, "properties", id="properties as a list"),
        pytest.param({"allOf": {"a": {"type": "string"}}}, "allOf", id="allOf as an object"),
    ],
)
def test_a_schema_this_module_cannot_enforce_is_refused_at_load_time(schema, says):
    """Twenty-three rows, one function. The constructor refuses when the schema is read,
    not when a document is checked against it — because a rule nobody applies looks enforced
    right up to the day it matters."""

    assert says in _refused(schema)


def test_a_schema_that_is_not_an_object_is_refused():
    """A list, a number and a string are all valid JSON and none of them is a schema.
    Separate from the table because there is no `_refused` message to compare."""

    for shape in (None, [], "object", 7):
        with pytest.raises(intent._UnsupportedSchema):
            intent._Schema(shape)  # type: ignore[arg-type]


def test_the_four_types_and_a_resolving_reference_are_accepted():
    """The clean control. Without it every row above is satisfied by a constructor that
    refuses everything, which is the passing test this repository exists to refuse."""

    for name in ("array", "integer", "object", "string"):
        assert intent._Schema({"type": name})
    assert intent._Schema({"$defs": {"name": {"type": "string"}}, "$ref": "#/$defs/name"})


def test_an_invalid_pattern_is_compiled_here_rather_than_on_first_use():
    """An invalid expression discovered while checking a document is an exception in the
    middle of a validation, and the person who typed the document did not write the schema."""

    with pytest.raises(re.error):
        intent._Schema({"type": "string", "pattern": "([unclosed"})


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
