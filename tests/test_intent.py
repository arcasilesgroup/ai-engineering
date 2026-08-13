"""Executable contracts for the versioned Solution Intent."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "intent-v1.schema.json"


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    assert reference.startswith("#/$defs/")
    return root["$defs"][reference.removeprefix("#/$defs/")]


def _valid(instance: Any, schema: dict[str, Any], root: dict[str, Any]) -> bool:
    schema = _resolve(schema, root)

    if "const" in schema and instance != schema["const"]:
        return False
    if "enum" in schema and instance not in schema["enum"]:
        return False
    if "type" in schema:
        expected = schema["type"]
        matches_type = {
            "array": isinstance(instance, list),
            "integer": isinstance(instance, int) and not isinstance(instance, bool),
            "object": isinstance(instance, dict),
            "string": isinstance(instance, str),
        }[expected]
        if not matches_type:
            return False

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            return False
        if len(instance) > schema.get("maxLength", len(instance)):
            return False
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            return False
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            return False
        if len(instance) > schema.get("maxItems", len(instance)):
            return False
        if schema.get("uniqueItems") and len(
            {json.dumps(v, sort_keys=True) for v in instance}
        ) != len(instance):
            return False
        if "items" in schema and not all(
            _valid(value, schema["items"], root) for value in instance
        ):
            return False
    if isinstance(instance, dict):
        required = schema.get("required", [])
        if any(key not in instance for key in required):
            return False
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(instance) - set(properties):
            return False
        if any(
            key in instance and not _valid(instance[key], subschema, root)
            for key, subschema in properties.items()
        ):
            return False

    if "allOf" in schema and not all(_valid(instance, part, root) for part in schema["allOf"]):
        return False
    if "oneOf" in schema and sum(_valid(instance, part, root) for part in schema["oneOf"]) != 1:
        return False
    if "not" in schema and _valid(instance, schema["not"], root):
        return False
    if "if" in schema and _valid(instance, schema["if"], root):
        if "then" in schema and not _valid(instance, schema["then"], root):
            return False
    elif "else" in schema and not _valid(instance, schema["else"], root):
        return False
    return True


def _intent() -> dict[str, Any]:
    return {
        "schema": "urn:ai-engineering:intent:1",
        "schema_version": "1",
        "type": "intent",
        "identity": {"id": "governed-delivery", "title": "Governed delivery"},
        "solution_intent": {
            "fixed_constraints": ["Blocking evidence must fail closed."],
            "variables": ["The delivery surface may change."],
            "current_facts": ["One writer owns repository changes."],
            "intended_outcomes": ["Every green result has executed evidence."],
        },
        "ownership": {"accountable_role": "repository maintainer"},
        "relations": [
            {
                "kind": "spec",
                "id": "010",
                "path": "specs/010-governed-agentic-engineering-foundation/spec.md",
                "target_digest": "sha256:" + "a" * 64,
            }
        ],
        "lifecycle": {"status": "draft", "transitions": []},
    }


def test_intent_v1_schema_is_closed_and_versioned() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:ai-engineering:intent:1"
    assert schema["x-canonical-home"] == ".ai/intent.md"

    draft = _intent()
    assert _valid(draft, schema, schema)

    active = deepcopy(draft)
    active["lifecycle"] = {
        "status": "active",
        "transitions": [
            {
                "from": "draft",
                "to": "active",
                "changed_at": "2026-08-13T10:00:00Z",
                "authority_role": "repository maintainer",
                "approval_ref": "change-request-17",
            }
        ],
        "approval": {
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-17",
            "approved_at": "2026-08-13T10:00:00Z",
        },
    }
    decision = deepcopy(draft)
    decision["relations"][0] = {
        "kind": "decision",
        "id": "0005",
        "path": "docs/adr/0005-intent-foundation.md",
        "target_digest": "sha256:" + "b" * 64,
    }

    retired = deepcopy(active)
    retired["lifecycle"]["status"] = "retired"
    retired["lifecycle"]["transitions"].append(
        {
            "from": "active",
            "to": "retired",
            "changed_at": "2026-08-14T10:00:00Z",
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-18",
        }
    )
    retired["lifecycle"]["retired_reason"] = "Replaced by a newly governed intent."
    assert all(_valid(candidate, schema, schema) for candidate in (active, decision, retired))

    invalid = []
    for key in schema["required"]:
        missing = deepcopy(draft)
        missing.pop(key)
        invalid.append(missing)

    unknown_root = deepcopy(draft)
    unknown_root["unexpected"] = "not allowed"
    invalid.append(unknown_root)

    for path in (
        ("identity",),
        ("solution_intent",),
        ("ownership",),
        ("relations", 0),
        ("lifecycle",),
        ("lifecycle", "transitions", 0),
        ("lifecycle", "approval"),
    ):
        unknown_nested = deepcopy(active)
        node = unknown_nested
        for part in path:
            node = node[part]
        node["unexpected"] = "not allowed"
        invalid.append(unknown_nested)

    bad_relation = deepcopy(draft)
    bad_relation["relations"][0]["path"] = "outside/spec.md"
    invalid.append(bad_relation)

    bad_digest = deepcopy(draft)
    bad_digest["relations"][0]["target_digest"] = "not-a-digest"
    invalid.append(bad_digest)

    bad_role = deepcopy(draft)
    bad_role["ownership"]["accountable_role"] = "not/a/role"
    invalid.append(bad_role)

    duplicate_relation = deepcopy(draft)
    duplicate_relation["relations"].append(deepcopy(duplicate_relation["relations"][0]))
    invalid.append(duplicate_relation)

    active_without_approval = deepcopy(active)
    active_without_approval["lifecycle"].pop("approval")
    invalid.append(active_without_approval)

    draft_with_approval = deepcopy(active)
    draft_with_approval["lifecycle"]["status"] = "draft"
    invalid.append(draft_with_approval)

    retired_without_reason = deepcopy(active)
    retired_without_reason["lifecycle"]["status"] = "retired"
    invalid.append(retired_without_reason)

    invalid_transition = deepcopy(active)
    invalid_transition["lifecycle"]["transitions"][0]["to"] = "retired"
    invalid.append(invalid_transition)

    assert invalid
    assert all(not _valid(candidate, schema, schema) for candidate in invalid)
