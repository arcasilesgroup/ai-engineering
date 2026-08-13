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


def test_intent_validator_rejects_unknown_missing_stale_and_broken_relations(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from ai_engineering import intent

    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        repository = tmp_path / case["id"]
        materialized = _fixture_case(corpus, case)
        source = repository / ".ai" / "intent.md"
        source.parent.mkdir(parents=True)
        source.write_text(json.dumps(materialized["intent"]), encoding="utf-8")
        for file in materialized["repository"]["files"]:
            target = repository / file["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file["content"], encoding="utf-8")

        before = {
            path.relative_to(repository): path.read_bytes()
            for path in repository.rglob("*")
            if path.is_file()
        }
        result = intent.validate(source, repository)
        expected = (
            {"outcome": "PASS"}
            if case["classification"] == "valid"
            else case["expected_incomplete"]
        )
        assert result.as_dict() == expected, case["id"]
        assert before == {
            path.relative_to(repository): path.read_bytes()
            for path in repository.rglob("*")
            if path.is_file()
        }

    canonical = _fixture_case(corpus, corpus["cases"][0])
    files = [(file["path"], file["content"]) for file in canonical["repository"]["files"]]
    assert intent.validate(canonical["intent"], files).as_dict() == {"outcome": "PASS"}

    active = deepcopy(canonical["intent"])
    transition = {
        "from": "draft",
        "to": "active",
        "changed_at": "2026-08-13T10:00:00Z",
        "authority_role": "repository maintainer",
        "approval_ref": "change-request-17",
    }
    active["lifecycle"] = {
        "status": "active",
        "transitions": [transition],
        "approval": {
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-17",
            "approved_at": "2026-08-13T10:00:00Z",
        },
    }
    assert intent.validate(active, files).as_dict() == {"outcome": "PASS"}

    duplicate = intent.validate(canonical["intent"], [*files, files[0]])
    assert duplicate.as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target is ambiguous",
    }

    duplicate_identity = deepcopy(canonical["intent"])
    other_path = "specs/010-other/spec.md"
    other_content = '---\nid: "010"\nstatus: draft\n---\n'
    duplicate_identity["relations"].append(
        {
            "kind": "spec",
            "id": "010",
            "path": other_path,
            "target_digest": "sha256:" + sha256(other_content.encode()).hexdigest(),
        }
    )
    assert intent.validate(duplicate_identity, [*files, (other_path, other_content)]).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target is ambiguous",
    }

    broken_graph = deepcopy(canonical)
    broken_content = '---\nid: "010"\nstatus: draft\nrelations: specs/999-missing/spec.md\n---\n\n'
    broken_graph["repository"]["files"][0]["content"] = broken_content
    broken_graph["intent"]["relations"][0]["target_digest"] = (
        "sha256:" + sha256(broken_content.encode()).hexdigest()
    )
    broken = intent.validate(
        broken_graph["intent"],
        [(file["path"], file["content"]) for file in broken_graph["repository"]["files"]],
    )
    assert broken.as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target does not exist",
    }

    traversal = deepcopy(canonical)
    traversal_content = '---\nid: "010"\nstatus: draft\nrelations: ../../outside\n---\n\n'
    traversal["repository"]["files"][0]["content"] = traversal_content
    traversal["intent"]["relations"][0]["target_digest"] = (
        "sha256:" + sha256(traversal_content.encode()).hexdigest()
    )
    escaped = intent.validate(
        traversal["intent"],
        [(file["path"], file["content"]) for file in traversal["repository"]["files"]],
    )
    assert escaped.as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target is outside repository",
    }

    discontinuous = deepcopy(canonical)
    discontinuous["intent"]["lifecycle"] = {
        "status": "active",
        "transitions": [transition, transition],
        "approval": {
            "authority_role": "repository maintainer",
            "approval_ref": "change-request-17",
            "approved_at": "2026-08-13T10:00:00Z",
        },
    }
    invalid_history = intent.validate(discontinuous["intent"], files)
    assert invalid_history.as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_LIFECYCLE_INVALID",
        "reason": "lifecycle history does not reach declared status",
    }

    repository = tmp_path / "symlink-repository"
    outside = tmp_path / "outside.md"
    outside.write_text(files[0][1], encoding="utf-8")
    linked = repository / files[0][0]
    linked.parent.mkdir(parents=True)
    linked.symlink_to(outside)
    symlink_escape = intent.validate(canonical["intent"], repository)
    assert symlink_escape.as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target is outside repository",
    }

    unreadable_repository = tmp_path / "unreadable-repository"
    unreadable_target = unreadable_repository / files[0][0]
    unreadable_target.mkdir(parents=True)
    assert intent.validate(canonical["intent"], unreadable_repository).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target cannot be read",
    }

    malformed_target = deepcopy(canonical)
    malformed_content = '---\nid: "010"\nrelations: .ai/intent.md\n'
    malformed_target["repository"]["files"][0]["content"] = malformed_content
    malformed_target["intent"]["relations"][0]["target_digest"] = (
        "sha256:" + sha256(malformed_content.encode()).hexdigest()
    )
    assert intent.validate(
        malformed_target["intent"],
        [(file["path"], file["content"]) for file in malformed_target["repository"]["files"]],
    ).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target cannot be read",
    }

    malformed = repository / ".ai" / "intent.md"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("{not-json", encoding="utf-8")
    assert intent.validate(malformed, repository).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_SCHEMA_INVALID",
        "reason": "schema validation failed",
    }

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema["unevaluatedProperties"] = False
    undecidable_schema = tmp_path / "unsupported-schema.json"
    undecidable_schema.write_text(json.dumps(schema), encoding="utf-8")
    monkeypatch.setattr(intent.paths, "policy", lambda _: undecidable_schema)
    assert intent.validate(canonical["intent"], files).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_SCHEMA_INVALID",
        "reason": "schema validation failed",
    }


def test_intent_validator_resolves_typed_targets_and_deep_graphs_without_recursion() -> None:
    from ai_engineering import intent

    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    canonical = _fixture_case(corpus, corpus["cases"][0])
    target_path = canonical["repository"]["files"][0]["path"]

    def validates(content: str, relation: dict[str, str] | None = None) -> dict[str, str]:
        candidate = deepcopy(canonical["intent"])
        if relation is not None:
            candidate["relations"][0].update(relation)
        candidate["relations"][0]["target_digest"] = (
            "sha256:" + sha256(content.encode()).hexdigest()
        )
        return intent.validate(candidate, [(target_path, content)]).as_dict()

    broken = {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target identity does not match relation",
    }
    assert validates("# no frontmatter\n") == broken
    assert validates("---\nstatus: draft\n---\n\n# Missing id\n") == broken
    assert validates('---\nid: "011"\nstatus: draft\n---\n') == broken
    assert validates('---\nid: "010"\nstatus: draft\ntype: adr\n---\n') == broken
    assert validates('---\nid: "010"\nstatus: unknown\n---\n') == broken
    assert (
        validates(
            '---\nid: "010"\nstatus: draft\n---\n',
            {"id": "011"},
        )
        == broken
    )
    assert validates(
        '---\nid: "010"\nstatus: draft\n---\n',
        {"kind": "decision", "id": "0010"},
    ) == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_SCHEMA_INVALID",
        "reason": "schema validation failed",
    }

    decision_path = "docs/adr/0010-governed-choice.md"
    decision = '---\ntype: adr\nid: "0010"\nstatus: proposed\n---\n\n# Governed choice\n'
    candidate = deepcopy(canonical["intent"])
    candidate["relations"][0] = {
        "kind": "decision",
        "id": "0010",
        "path": decision_path,
        "target_digest": "sha256:" + sha256(decision.encode()).hexdigest(),
    }
    assert intent.validate(candidate, [(decision_path, decision)]).as_dict() == {"outcome": "PASS"}
    for malformed in (
        '---\nid: "0010"\nstatus: proposed\n---\n',
        '---\ntype: spec\nid: "0010"\nstatus: proposed\n---\n',
        '---\ntype: adr\nid: "0011"\nstatus: proposed\n---\n',
    ):
        candidate["relations"][0]["target_digest"] = (
            "sha256:" + sha256(malformed.encode()).hexdigest()
        )
        assert intent.validate(candidate, [(decision_path, malformed)]).as_dict() == broken

    crlf = '---\r\nid: "010"\r\nstatus: draft\r\n---\r\n\r\n# Governed\r\n'
    assert validates(crlf) == {"outcome": "PASS"}
    malformed_utf8 = b'---\nid: "010"\nstatus: draft\n---\n\xff'
    candidate = deepcopy(canonical["intent"])
    candidate["relations"][0]["target_digest"] = "sha256:" + sha256(malformed_utf8).hexdigest()
    assert intent.validate(candidate, [(target_path, malformed_utf8)]).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_BROKEN",
        "reason": "relation target cannot be read",
    }

    count = 1_205
    files: list[tuple[str, str]] = []
    for number in range(count):
        path = f"docs/adr/{number:04d}-node.md"
        next_path = f"docs/adr/{number + 1:04d}-node.md" if number + 1 < count else ""
        relation_line = f"relations: {next_path}\n" if next_path else ""
        files.append(
            (
                path,
                f'---\ntype: adr\nid: "{number:04d}"\nstatus: proposed\n'
                f"{relation_line}---\n\n# Node\n",
            )
        )
    deep = deepcopy(canonical["intent"])
    deep["relations"][0] = {
        "kind": "decision",
        "id": "0000",
        "path": files[0][0],
        "target_digest": "sha256:" + sha256(files[0][1].encode()).hexdigest(),
    }
    assert intent.validate(deep, files).as_dict() == {"outcome": "PASS"}

    last_path, _ = files[-1]
    files[-1] = (
        last_path,
        f'---\ntype: adr\nid: "{count - 1:04d}"\nstatus: proposed\nrelations: {files[0][0]}\n---\n',
    )
    assert intent.validate(deep, files).as_dict() == {
        "outcome": "INCOMPLETE",
        "code": "INTENT_RELATION_CYCLE",
        "reason": "relation graph contains a cycle",
    }


def test_intent_path_is_lexically_canonical_and_never_a_symlink(tmp_path: Path) -> None:
    from ai_engineering import intent

    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    canonical = _fixture_case(corpus, corpus["cases"][0])

    def repository(name: str) -> tuple[Path, bytes]:
        root = tmp_path / name
        root.mkdir()
        for file in canonical["repository"]["files"]:
            target = root / file["path"]
            target.parent.mkdir(parents=True)
            target.write_text(file["content"], encoding="utf-8")
        return root, json.dumps(canonical["intent"]).encode()

    direct, payload = repository("direct")
    canonical_path = direct / ".ai" / "intent.md"
    canonical_path.parent.mkdir()
    canonical_path.write_bytes(payload)
    assert intent.validate(canonical_path, direct).as_dict() == {"outcome": "PASS"}
    elsewhere = direct / "intent.md"
    elsewhere.write_bytes(payload)
    assert intent.validate(elsewhere, direct).outcome == "INCOMPLETE"
    alias_parent = direct / "alias"
    alias_parent.mkdir()
    traversal_alias = alias_parent / ".." / ".ai" / "intent.md"
    assert intent.validate(traversal_alias, direct).outcome == "INCOMPLETE"

    parent_link, payload = repository("parent-link")
    real_ai = parent_link / "real-ai"
    real_ai.mkdir()
    (real_ai / "intent.md").write_bytes(payload)
    (parent_link / ".ai").symlink_to(real_ai, target_is_directory=True)
    assert intent.validate(parent_link / ".ai" / "intent.md", parent_link).outcome == "INCOMPLETE"

    file_link, payload = repository("file-link")
    real_intent = file_link / "real-intent.md"
    real_intent.write_bytes(payload)
    (file_link / ".ai").mkdir()
    (file_link / ".ai" / "intent.md").symlink_to(real_intent)
    assert intent.validate(file_link / ".ai" / "intent.md", file_link).outcome == "INCOMPLETE"


def test_intent_target_frontmatter_rejects_repaired_scalars_and_unicode_lines() -> None:
    from ai_engineering import intent

    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    canonical = _fixture_case(corpus, corpus["cases"][0])
    target_path = canonical["repository"]["files"][0]["path"]

    def validates(content: str) -> dict[str, str]:
        encoded = content.encode()
        candidate = deepcopy(canonical["intent"])
        candidate["relations"][0]["target_digest"] = "sha256:" + sha256(encoded).hexdigest()
        return intent.validate(candidate, [(target_path, encoded)]).as_dict()

    assert validates("---\nid: '010'\nstatus: \"draft\"\n---\n") == {"outcome": "PASS"}
    assert validates("---\r\nid: '010'\r\nstatus: \"draft\"\r\n---\r\n") == {"outcome": "PASS"}

    decision_path = "docs/adr/0010-dont-repeat-work.md"

    def validates_decision(content: str) -> dict[str, str]:
        encoded = content.encode()
        candidate = deepcopy(canonical["intent"])
        candidate["relations"][0] = {
            "kind": "decision",
            "id": "0010",
            "path": decision_path,
            "target_digest": "sha256:" + sha256(encoded).hexdigest(),
        }
        return intent.validate(candidate, [(decision_path, encoded)]).as_dict()

    madr = (
        "---\n"
        "schema: urn:ai-engineering:madr:1\n"
        'schema_version: "1"\n'
        "type: adr\n"
        'id: "0010"\n'
        'title: "Don\'t repeat work"\n'
        "date: 2026-08-13\n"
        'spec: "010"\n'
        "status: proposed\n"
        'supersedes: ""\n'
        "---\n"
    )
    assert validates_decision(madr) == {"outcome": "PASS"}
    mixed_quotes = madr.replace(
        'title: "Don\'t repeat work"',
        'title: "Why "don\'t" repeat work"',
    )
    assert validates_decision(mixed_quotes) == {"outcome": "PASS"}
    for control in ("\x00", "\t", "\x7f", "\u009f", "\u202e", "\u00a0"):
        poisoned = madr.replace("Don't", f"Don{control}t")
        assert validates_decision(poisoned)["outcome"] == "INCOMPLETE"

    malformed = (
        '---\nid: "010\nstatus: draft\n---\n',
        '---\nid: ""010""\nstatus: draft\n---\n',
        "---\nid: \"'010'\"\nstatus: draft\n---\n",
        '---\nid: "010"\nstatus: ""draft""\n---\n',
        '---\nid: "010"\nstatus: "\'draft\'"\n---\n',
        '---\nid: "010"\nstatus: "draft\'\n---\n',
        '---\nid: "010"\nstatus: dra"ft\n---\n',
        '---\nid: "010"\u0085status: draft\n---\n',
        '---\nid: "010"\u2028status: draft\n---\n',
        '---\nid: "010"\u2029status: draft\n---\n',
        '---\rid: "010"\rstatus: draft\r---\r',
        '---\n# comment\nid: "010"\nstatus: draft\n---\n',
        '---\n id: "010"\nstatus: draft\n---\n',
        '---\nid: "010"\nstatus: draft\nunexpected: value\n---\n',
        '---\nid: "010"\nid: "010"\nstatus: draft\n---\n',
        '---\nid: "010"\nstatus: dra\x00ft\n---\n',
        '---\nid: "010"\nstatus: dra\x7fft\n---\n',
    )
    for content in malformed:
        result = validates(content)
        assert result["outcome"] == "INCOMPLETE", content.encode("unicode_escape")
