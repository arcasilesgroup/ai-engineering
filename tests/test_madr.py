"""Executable contracts for the versioned MADR frontmatter."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "madr-v1.schema.json"
ROOT_SCHEMA_KEYWORDS = {
    "$defs",
    "$id",
    "$schema",
    "additionalProperties",
    "allOf",
    "description",
    "properties",
    "required",
    "title",
    "type",
    "x-body-sections",
    "x-canonical-home",
    "x-decision-graph",
    "x-owner-field",
    "x-status-transitions",
}


def _root_keywords_are_closed(schema: dict[str, Any]) -> bool:
    return set(schema) == ROOT_SCHEMA_KEYWORDS


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    assert reference.startswith("#/$defs/")
    return root["$defs"][reference.removeprefix("#/$defs/")]


def _has_format(value: str, format_name: str) -> bool:
    try:
        if format_name == "date":
            return date.fromisoformat(value).isoformat() == value
        if format_name == "date-time":
            datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
            return value.endswith("Z")
    except ValueError:
        return False
    raise AssertionError(f"unsupported format in test contract: {format_name}")


def _valid(instance: Any, schema: dict[str, Any], root: dict[str, Any]) -> bool:
    schema = _resolve(schema, root)
    if "const" in schema and instance != schema["const"]:
        return False
    if "enum" in schema and instance not in schema["enum"]:
        return False
    if "type" in schema:
        expected = schema["type"]
        matches = {
            "object": isinstance(instance, dict),
            "string": isinstance(instance, str),
        }[expected]
        if not matches:
            return False

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            return False
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            return False
        if "format" in schema and not _has_format(instance, schema["format"]):
            return False
    if isinstance(instance, dict):
        if any(key not in instance for key in schema.get("required", [])):
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
    if "anyOf" in schema and not any(_valid(instance, part, root) for part in schema["anyOf"]):
        return False
    if "not" in schema and _valid(instance, schema["not"], root):
        return False
    return not (
        "if" in schema
        and _valid(instance, schema["if"], root)
        and "then" in schema
        and not _valid(instance, schema["then"], root)
    )


def _madr(status: str = "proposed") -> dict[str, str]:
    record = {
        "schema": "urn:ai-engineering:madr:1",
        "schema_version": "1",
        "type": "adr",
        "id": "0007",
        "title": "Keep authority outside the agent",
        "date": "2026-08-13",
        "spec": "010",
        "status": status,
        "supersedes": "",
    }
    if status != "proposed":
        record.update(
            {
                "authority_role": "repository maintainer",
                "approval_ref": "change-request-17",
                "approved_at": "2026-08-13T10:00:00Z",
            }
        )
    return record


def test_madr_v1_schema_graph_and_transitions_are_closed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert _root_keywords_are_closed(schema)
    authority_override = deepcopy(schema)
    authority_override["x-authority-override"] = {"role": "AI agent"}
    assert not _root_keywords_are_closed(authority_override)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:ai-engineering:madr:1"
    assert schema["x-canonical-home"] == "docs/adr/"
    assert schema["x-owner-field"] == "authority_role"
    assert schema["x-body-sections"] == {
        "required": [
            "Context and problem statement",
            "Considered options",
            "Decision outcome",
            "Consequences",
        ],
        "alternatives": "Considered options",
        "rejection_reason": "Decision outcome",
        "consequences": "Consequences",
    }
    assert schema["x-status-transitions"] == {
        "initial": "proposed",
        "allowed": [
            {"from": "proposed", "to": "accepted"},
            {"from": "proposed", "to": "rejected"},
            {"from": "accepted", "to": "superseded"},
        ],
        "terminal": ["rejected", "superseded"],
    }
    assert schema["x-decision-graph"] == {
        "node_id_field": "id",
        "node_ids_unique": True,
        "spec_edge": {
            "field": "spec",
            "target_home": "specs/",
            "cardinality": "exactly_one",
            "existing": True,
            "local": True,
        },
        "supersession_edge": {
            "field": "supersedes",
            "target_home": "docs/adr/",
            "empty_allowed": True,
            "existing_if_present": True,
            "local": True,
            "self_links_allowed": False,
            "acyclic": True,
        },
    }

    required = [
        "schema",
        "schema_version",
        "type",
        "id",
        "title",
        "date",
        "spec",
        "status",
        "supersedes",
    ]
    approval = ["authority_role", "approval_ref", "approved_at"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == required
    assert set(schema["properties"]) == set(required + approval)
    assert all(
        _resolve(property_schema, schema)["type"] == "string"
        for property_schema in schema["properties"].values()
    )
    assert schema["properties"]["id"]["pattern"] == "^[0-9]{4}$"
    assert schema["properties"]["spec"]["pattern"] == "^[0-9]{3}$"
    assert schema["properties"]["date"]["format"] == "date"
    assert _resolve(schema["properties"]["approved_at"], schema)["format"] == "date-time"
    assert "never an agent or reviewer" in schema["properties"]["authority_role"]["description"]
    assert schema["properties"]["status"]["enum"] == [
        "proposed",
        "accepted",
        "rejected",
        "superseded",
    ]

    proposed = _madr()
    accepted = _madr("accepted")
    accepted["supersedes"] = "0004"
    assert all(
        _valid(candidate, schema, schema)
        for candidate in (proposed, accepted, _madr("rejected"), _madr("superseded"))
    )

    invalid = []
    for field in required:
        candidate = deepcopy(proposed)
        candidate.pop(field)
        invalid.append(candidate)
    for field in required:
        candidate = deepcopy(proposed)
        candidate[field] = {"wrong": "type"}
        invalid.append(candidate)
    for status in ("accepted", "rejected", "superseded"):
        for field in approval:
            candidate = _madr(status)
            candidate.pop(field)
            invalid.append(candidate)
    valid_approval_values = {
        "authority_role": "repository maintainer",
        "approval_ref": "change-request-17",
        "approved_at": "2026-08-13T10:00:00Z",
    }
    for field, value in valid_approval_values.items():
        candidate = deepcopy(proposed)
        candidate[field] = value
        invalid.append(candidate)

    mutations = {
        "unknown": "not allowed",
        "schema": "urn:ai-engineering:madr:2",
        "schema_version": "2",
        "type": "madr",
        "id": "7",
        "title": "   ",
        "date": "2026-02-30",
        "spec": "10",
        "status": "approved",
        "supersedes": "0007-extra",
    }
    for field, value in mutations.items():
        candidate = deepcopy(proposed)
        candidate[field] = value
        invalid.append(candidate)

    invalid_approval_values = {
        "authority_role": "   ",
        "approval_ref": "",
        "approved_at": "2026-08-13T10:00:00+02:00",
    }
    for field, value in invalid_approval_values.items():
        candidate = _madr("accepted")
        candidate[field] = value
        invalid.append(candidate)

    for forbidden_role in (
        "AI agent",
        "security reviewer",
        "AGENT",
        "lead ReViEwEr",
        "security-reviewer",
        "AI_agent",
        "agent_owner",
        "security_reviewer",
        "reviewer_role",
    ):
        candidate = _madr("accepted")
        candidate["authority_role"] = forbidden_role
        invalid.append(candidate)

    for nearby_role in (
        "agentic engineering owner",
        "peer reviewers coordinator",
        "reagent operations owner",
    ):
        candidate = _madr("accepted")
        candidate["authority_role"] = nearby_role
        assert _valid(candidate, schema, schema)

    assert invalid
    assert all(not _valid(candidate, schema, schema) for candidate in invalid)
