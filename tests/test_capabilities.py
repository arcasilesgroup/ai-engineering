from __future__ import annotations

import json
import re
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "capability-manifest.schema.json"
ROOT_KEYWORDS = {
    "$defs",
    "$id",
    "$schema",
    "additionalProperties",
    "description",
    "properties",
    "required",
    "title",
    "type",
    "x-capability-policy",
    "x-mode-policy",
}


def _resolve(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = node.get("$ref")
    if reference is None:
        return node
    assert reference.startswith("#/$defs/")
    return root["$defs"][reference.removeprefix("#/$defs/")]


def _schema_accepts(value: Any, node: dict[str, Any], root: dict[str, Any]) -> bool:
    node = _resolve(node, root)
    if "const" in node and value != node["const"]:
        return False
    if "enum" in node and value not in node["enum"]:
        return False
    expected = node.get("type")
    if expected is not None:
        matches = {
            "array": isinstance(value, list),
            "boolean": isinstance(value, bool),
            "object": isinstance(value, dict),
            "string": isinstance(value, str),
        }[expected]
        if not matches:
            return False
    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            return False
        if "pattern" in node and re.search(node["pattern"], value) is None:
            return False
    if isinstance(value, list):
        if len(value) < node.get("minItems", 0):
            return False
        if len(value) > node.get("maxItems", len(value)):
            return False
        canonical = [json.dumps(item, sort_keys=True) for item in value]
        if node.get("uniqueItems") and len(canonical) != len(set(canonical)):
            return False
        if "items" in node and not all(
            _schema_accepts(item, node["items"], root) for item in value
        ):
            return False
    if isinstance(value, dict):
        if set(node.get("required", ())) - set(value):
            return False
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False and set(value) - set(properties):
            return False
        if any(
            key in value and not _schema_accepts(value[key], child, root)
            for key, child in properties.items()
        ):
            return False
    if "allOf" in node and not all(_schema_accepts(value, part, root) for part in node["allOf"]):
        return False
    if "anyOf" in node and not any(_schema_accepts(value, part, root) for part in node["anyOf"]):
        return False
    return not ("not" in node and _schema_accepts(value, node["not"], root))


def _manifest_accepts(value: dict[str, Any], schema: dict[str, Any]) -> bool:
    if not _schema_accepts(value, schema, schema):
        return False
    capability_policy = schema["x-capability-policy"]
    identifiers = [entry[capability_policy["id_field"]] for entry in value["capabilities"]]
    if capability_policy["ids_unique"] and len(identifiers) != len(set(identifiers)):
        return False
    mode_policy = schema["x-mode-policy"]
    for capability in value["capabilities"]:
        modes = capability["modes"]
        mode_ids = [mode[mode_policy["id_field"]] for mode in modes]
        if mode_policy["ids_unique_within_capability"] and len(mode_ids) != len(set(mode_ids)):
            return False
        permission_sets = [
            json.dumps(
                {field: mode[field] for field in mode_policy["permission_fields"]},
                sort_keys=True,
            )
            for mode in modes
        ]
        if mode_policy["permission_sets_distinct_within_capability"] and len(
            permission_sets
        ) != len(set(permission_sets)):
            return False
    return True


def _mode(identifier: str, *, write: bool = False) -> dict[str, Any]:
    return {
        "id": identifier,
        "read_roots": ["."],
        "write_roots": ["docs/adr"] if write else [],
        "exec_allowlist": [],
        "network": [],
        "secrets": [],
        "human_gate": "before_write" if write else "never",
        "enforcement": ["preflight.skill"],
        "proof_requirements": {
            "allow": ["capability.allow"],
            "deny": ["capability.deny"],
            "installed_artifact": True,
        },
    }


def test_capability_schema_is_closed_and_permission_distinct() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(schema) == ROOT_KEYWORDS
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:ai-engineering:capability-manifest:1"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["schema", "schema_version", "capabilities"]

    capability_policy = schema["x-capability-policy"]
    allowed_ids = capability_policy["allowed_ids"]
    assert len(allowed_ids) == len(set(allowed_ids)) == 15
    assert capability_policy == {
        "id_field": "id",
        "ids_unique": True,
        "allowed_ids": allowed_ids,
    }
    assert schema["$defs"]["capability"]["properties"]["id"]["enum"] == allowed_ids
    assert set(schema["$defs"]) == {
        "capability",
        "execution",
        "identifier",
        "identifier_list",
        "mode",
        "network_destination",
        "proof_requirements",
        "repository_root",
        "root_list",
    }
    assert schema["x-mode-policy"] == {
        "id_field": "id",
        "ids_unique_within_capability": True,
        "permission_fields": [
            "read_roots",
            "write_roots",
            "exec_allowlist",
            "network",
            "secrets",
            "human_gate",
        ],
        "permission_sets_distinct_within_capability": True,
    }

    mode = schema["$defs"]["mode"]
    assert mode["additionalProperties"] is False
    assert set(mode["required"]) == set(mode["properties"])
    assert mode["properties"]["human_gate"]["enum"] == [
        "never",
        "before_write",
        "before_exec",
        "before_network",
        "before_publish",
    ]
    proof = schema["$defs"]["proof_requirements"]
    assert proof["additionalProperties"] is False
    assert proof["properties"]["installed_artifact"] == {"type": "boolean", "const": True}

    manifest = {
        "schema": "urn:ai-engineering:capability-manifest:1",
        "schema_version": "1",
        "capabilities": [{"id": "ai-spec", "modes": [_mode("read"), _mode("write", write=True)]}],
    }
    assert _manifest_accepts(manifest, schema)

    unknown = deepcopy(manifest)
    unknown["capabilities"][0]["modes"][0]["shell"] = "*"
    assert not _manifest_accepts(unknown, schema)
    escaped = deepcopy(manifest)
    escaped["capabilities"][0]["modes"][0]["read_roots"] = ["../private"]
    assert not _manifest_accepts(escaped, schema)
    unnormalized = deepcopy(manifest)
    unnormalized["capabilities"][0]["modes"][0]["read_roots"] = ["src/./private"]
    assert not _manifest_accepts(unnormalized, schema)
    wildcard = deepcopy(manifest)
    wildcard["capabilities"][0]["modes"][0]["write_roots"] = ["**"]
    assert not _manifest_accepts(wildcard, schema)
    missing_proof = deepcopy(manifest)
    del missing_proof["capabilities"][0]["modes"][0]["proof_requirements"]
    assert not _manifest_accepts(missing_proof, schema)
    duplicate_permissions = deepcopy(manifest)
    duplicate_permissions["capabilities"][0]["modes"][1].update(
        {
            field: deepcopy(duplicate_permissions["capabilities"][0]["modes"][0][field])
            for field in schema["x-mode-policy"]["permission_fields"]
        }
    )
    assert not _manifest_accepts(duplicate_permissions, schema)


def test_capabilities_toml_declares_exactly_fifteen_capabilities() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = tomllib.loads((ROOT / "policy" / "capabilities.toml").read_text(encoding="utf-8"))
    assert _manifest_accepts(manifest, schema)

    capabilities = manifest["capabilities"]
    expected = schema["x-capability-policy"]["allowed_ids"]
    assert [capability["id"] for capability in capabilities] == expected
    assert len(capabilities) == 15
    declared_modes = {
        capability["id"]: [mode["id"] for mode in capability["modes"]]
        for capability in capabilities
    }
    assert declared_modes == {
        "ai-explore": ["default"],
        "ai-research": ["local", "cited-web"],
        "ai-spec": ["default"],
        "ai-plan": ["default"],
        "ai-build": ["default"],
        "ai-debug": ["default"],
        "ai-test": ["default"],
        "ai-design": ["default"],
        "ai-animation": ["default"],
        "ai-security": ["default"],
        "ai-review": ["default"],
        "ai-verify": ["default"],
        "ai-note": ["default"],
        "ai-report": ["digest", "issue"],
        "ai-ship": ["commit", "pull-request"],
    }

    dimensions = {
        "read_roots": "preflight.read",
        "write_roots": "preflight.write",
        "exec_allowlist": "preflight.exec",
        "network": "preflight.network",
        "secrets": "preflight.secrets",
    }
    for capability in capabilities:
        for mode in capability["modes"]:
            required = {control for field, control in dimensions.items() if mode[field]}
            if mode["human_gate"] != "never":
                required.add("preflight.human-gate")
            assert set(mode["enforcement"]) == required
            proof = mode["proof_requirements"]
            assert proof["installed_artifact"] is True
            assert proof["allow"] and proof["deny"]

    by_id = {capability["id"]: capability["modes"] for capability in capabilities}
    assert by_id["ai-explore"][0]["write_roots"] == []
    assert by_id["ai-review"][0]["write_roots"] == []
    assert by_id["ai-research"][0]["network"] == []
    assert by_id["ai-research"][1]["human_gate"] == "before_network"
    assert by_id["ai-report"][0]["network"] == []
    assert by_id["ai-report"][1]["human_gate"] == "before_publish"
    assert by_id["ai-ship"][1]["human_gate"] == "before_publish"
