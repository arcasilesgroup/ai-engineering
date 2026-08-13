"""Executable contracts for the versioned Solution Intent."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "intent-v1.schema.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "intent-v1.json"


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


def _fixture_case(corpus: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    materialized = deepcopy(corpus["base"])
    for mutation in case["mutations"]:
        node = materialized[mutation["target"]]
        for part in mutation["path"][:-1]:
            node = node[part]
        leaf = mutation["path"][-1]
        if mutation["op"] == "remove":
            del node[leaf]
        elif mutation["op"] == "set":
            node[leaf] = deepcopy(mutation["value"])
        else:
            assert mutation["op"] == "append"
            node[leaf].append(deepcopy(mutation["value"]))
    return materialized


def _fixture_content_relations(content: str) -> list[str]:
    lines = content.splitlines()
    assert lines and lines[0] == "---"
    closing = lines.index("---", 1)
    entries = [
        line.removeprefix("relations: ")
        for line in lines[1:closing]
        if line.startswith("relations: ")
    ]
    assert len(entries) <= 1
    return entries[0].split(",") if entries else []


def _fixture_graph(materialized: dict[str, Any]) -> dict[str, list[str]]:
    return {
        ".ai/intent.md": [relation["path"] for relation in materialized["intent"]["relations"]],
        **{
            file["path"]: _fixture_content_relations(file["content"])
            for file in materialized["repository"]["files"]
        },
    }


def _fixture_has_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(target) for target in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def _fixture_contract_problems(
    corpus: dict[str, Any],
    expected_taxonomy: dict[str, str],
    expected_mutations: dict[str, list[dict[str, Any]]],
) -> list[str]:
    problems = []
    cases = {case["id"]: case for case in corpus["cases"]}
    paths = [file["path"] for file in corpus["base"]["repository"]["files"]]
    if len(paths) != len(set(paths)):
        problems.append("repository paths must be unique")
    if {case_id: case["classification"] for case_id, case in cases.items()} != expected_taxonomy:
        problems.append("case taxonomy differs")
    if {case_id: case["mutations"] for case_id, case in cases.items()} != expected_mutations:
        problems.append("case mutations differ")
    return problems


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


def test_intent_fixture_corpus_covers_valid_and_all_invalid_cases() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert corpus["schema"] == "urn:ai-engineering:intent-fixtures:1"
    assert set(corpus) == {"schema", "base", "cases"}
    assert set(corpus["base"]) == {"intent", "repository"}
    assert set(corpus["base"]["repository"]) == {"files"}

    cases = corpus["cases"]
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(
        set(case)
        == (
            {"id", "classification", "mutations"}
            if case["classification"] == "valid"
            else {"id", "classification", "mutations", "expected_incomplete"}
        )
        for case in cases
    )
    for case in cases:
        for mutation in case["mutations"]:
            assert mutation["target"] in {"intent", "repository"}
            assert mutation["op"] in {"append", "remove", "set"}
            assert mutation["path"]
            assert set(mutation) == (
                {"target", "op", "path"}
                if mutation["op"] == "remove"
                else {"target", "op", "path", "value"}
            )

    transition = {
        "from": "draft",
        "to": "active",
        "changed_at": "2026-08-13T10:00:00Z",
        "authority_role": "repository maintainer",
        "approval_ref": "change-request-17",
    }
    invalid_transition = {**transition, "to": "retired"}
    cycle_content = (
        '---\nid: "010"\nstatus: draft\nrelations: .ai/intent.md\n---\n\n# Governed foundation\n'
    )
    expected_taxonomy = {
        "canonical-draft": "valid",
        "missing-required": "schema_invalid",
        "unknown-root-field": "schema_invalid",
        "unknown-nested-field": "schema_invalid",
        "malformed-version": "schema_invalid",
        "malformed-identity-pattern": "schema_invalid",
        "duplicate-cardinality": "schema_invalid",
        "conditional-active-without-approval": "schema_invalid",
        "invalid-transition-shape": "schema_invalid",
        "stale-digest": "semantic_invalid",
        "broken-relation": "semantic_invalid",
        "relation-cycle": "semantic_invalid",
        "invalid-lifecycle-history": "semantic_invalid",
    }
    expected_mutations = {
        "canonical-draft": [],
        "missing-required": [{"target": "intent", "op": "remove", "path": ["solution_intent"]}],
        "unknown-root-field": [
            {
                "target": "intent",
                "op": "set",
                "path": ["unexpected"],
                "value": "not allowed",
            }
        ],
        "unknown-nested-field": [
            {
                "target": "intent",
                "op": "set",
                "path": ["identity", "unexpected"],
                "value": "not allowed",
            }
        ],
        "malformed-version": [
            {
                "target": "intent",
                "op": "set",
                "path": ["schema_version"],
                "value": "2",
            }
        ],
        "malformed-identity-pattern": [
            {
                "target": "intent",
                "op": "set",
                "path": ["identity", "id"],
                "value": "Not Valid",
            }
        ],
        "duplicate-cardinality": [
            {
                "target": "intent",
                "op": "append",
                "path": ["solution_intent", "fixed_constraints"],
                "value": "Blocking evidence must fail closed.",
            }
        ],
        "conditional-active-without-approval": [
            {
                "target": "intent",
                "op": "set",
                "path": ["lifecycle", "status"],
                "value": "active",
            }
        ],
        "invalid-transition-shape": [
            {
                "target": "intent",
                "op": "append",
                "path": ["lifecycle", "transitions"],
                "value": invalid_transition,
            }
        ],
        "stale-digest": [
            {
                "target": "intent",
                "op": "set",
                "path": ["relations", 0, "target_digest"],
                "value": "sha256:" + "0" * 64,
            }
        ],
        "broken-relation": [{"target": "repository", "op": "set", "path": ["files"], "value": []}],
        "relation-cycle": [
            {
                "target": "repository",
                "op": "set",
                "path": ["files", 0, "content"],
                "value": cycle_content,
            },
            {
                "target": "intent",
                "op": "set",
                "path": ["relations", 0, "target_digest"],
                "value": "sha256:" + sha256(cycle_content.encode()).hexdigest(),
            },
        ],
        "invalid-lifecycle-history": [
            {
                "target": "intent",
                "op": "append",
                "path": ["lifecycle", "transitions"],
                "value": transition,
            }
        ],
    }
    assert not _fixture_contract_problems(corpus, expected_taxonomy, expected_mutations)

    duplicate_path = deepcopy(corpus)
    duplicate_path["base"]["repository"]["files"].append(
        deepcopy(duplicate_path["base"]["repository"]["files"][0])
    )
    assert _fixture_contract_problems(duplicate_path, expected_taxonomy, expected_mutations) == [
        "repository paths must be unique"
    ]

    taxonomy_substitution = deepcopy(corpus)
    next(case for case in taxonomy_substitution["cases"] if case["id"] == "unknown-root-field")[
        "classification"
    ] = "semantic_invalid"
    assert "case taxonomy differs" in _fixture_contract_problems(
        taxonomy_substitution, expected_taxonomy, expected_mutations
    )

    mutation_substitution = deepcopy(corpus)
    missing_mutations = next(
        case for case in mutation_substitution["cases"] if case["id"] == "missing-required"
    )["mutations"]
    next(case for case in mutation_substitution["cases"] if case["id"] == "unknown-root-field")[
        "mutations"
    ] = deepcopy(missing_mutations)
    assert "case mutations differ" in _fixture_contract_problems(
        mutation_substitution, expected_taxonomy, expected_mutations
    )

    by_class = {
        classification: {case["id"] for case in cases if case["classification"] == classification}
        for classification in ("valid", "schema_invalid", "semantic_invalid")
    }
    assert {case["classification"] for case in cases} == set(by_class)
    valid_ids = by_class["valid"]
    schema_invalid_ids = by_class["schema_invalid"]
    semantic_invalid_ids = by_class["semantic_invalid"]
    assert valid_ids == {"canonical-draft"}
    assert schema_invalid_ids == {
        "missing-required",
        "unknown-root-field",
        "unknown-nested-field",
        "malformed-version",
        "malformed-identity-pattern",
        "duplicate-cardinality",
        "conditional-active-without-approval",
        "invalid-transition-shape",
    }
    assert semantic_invalid_ids == {
        "stale-digest",
        "broken-relation",
        "relation-cycle",
        "invalid-lifecycle-history",
    }

    materialized = {case["id"]: _fixture_case(corpus, case) for case in cases}
    assert all(_valid(materialized[case_id]["intent"], schema, schema) for case_id in valid_ids)
    assert all(
        not _valid(materialized[case_id]["intent"], schema, schema)
        for case_id in schema_invalid_ids
    )
    assert all(
        _valid(materialized[case_id]["intent"], schema, schema) for case_id in semantic_invalid_ids
    )

    expected = {
        "missing-required": ("INTENT_SCHEMA_INVALID", "schema validation failed"),
        "unknown-root-field": ("INTENT_SCHEMA_INVALID", "schema validation failed"),
        "unknown-nested-field": ("INTENT_SCHEMA_INVALID", "schema validation failed"),
        "malformed-version": ("INTENT_SCHEMA_INVALID", "schema validation failed"),
        "malformed-identity-pattern": (
            "INTENT_SCHEMA_INVALID",
            "schema validation failed",
        ),
        "duplicate-cardinality": ("INTENT_SCHEMA_INVALID", "schema validation failed"),
        "conditional-active-without-approval": (
            "INTENT_SCHEMA_INVALID",
            "schema validation failed",
        ),
        "invalid-transition-shape": (
            "INTENT_SCHEMA_INVALID",
            "schema validation failed",
        ),
        "stale-digest": ("INTENT_RELATION_STALE", "relation digest does not match target"),
        "broken-relation": ("INTENT_RELATION_BROKEN", "relation target does not exist"),
        "relation-cycle": ("INTENT_RELATION_CYCLE", "relation graph contains a cycle"),
        "invalid-lifecycle-history": (
            "INTENT_LIFECYCLE_INVALID",
            "lifecycle history does not reach declared status",
        ),
    }
    for case in cases:
        if case["classification"] == "valid":
            continue
        assert case["expected_incomplete"] == {
            "outcome": "INCOMPLETE",
            "code": expected[case["id"]][0],
            "reason": expected[case["id"]][1],
        }

    canonical = materialized["canonical-draft"]
    target = canonical["repository"]["files"][0]
    relation = canonical["intent"]["relations"][0]
    assert relation["path"] == target["path"]
    assert relation["target_digest"] == "sha256:" + sha256(target["content"].encode()).hexdigest()

    for resolved in materialized.values():
        assert set(resolved["repository"]) == {"files"}
        paths = [file["path"] for file in resolved["repository"]["files"]]
        assert len(paths) == len(set(paths))
        for file in resolved["repository"]["files"]:
            assert set(file) == {"path", "content"}
            assert not file["path"].startswith("/") and ".." not in Path(file["path"]).parts
            assert all(
                not path.startswith("/") and ".." not in Path(path).parts
                for path in _fixture_content_relations(file["content"])
            )

    serialized = json.dumps(corpus)
    assert not re.search(r"/(?:Users|home)/|[A-Za-z]:\\\\", serialized)
    assert not re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", serialized)

    assert (
        materialized["stale-digest"]["intent"]["relations"][0]["target_digest"]
        != relation["target_digest"]
    )
    assert materialized["broken-relation"]["repository"]["files"] == []
    assert not _fixture_has_cycle(_fixture_graph(canonical))
    cycle = materialized["relation-cycle"]
    assert _fixture_has_cycle(_fixture_graph(cycle))
    cycle_target = cycle["repository"]["files"][0]
    assert _fixture_content_relations(cycle_target["content"]) == [".ai/intent.md"]
    assert (
        cycle["intent"]["relations"][0]["target_digest"]
        == "sha256:" + sha256(cycle_target["content"].encode()).hexdigest()
    )
    assert (
        materialized["invalid-lifecycle-history"]["intent"]["lifecycle"]["transitions"][-1]["to"]
        != materialized["invalid-lifecycle-history"]["intent"]["lifecycle"]["status"]
    )
