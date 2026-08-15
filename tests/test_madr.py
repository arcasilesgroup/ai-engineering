"""Executable contracts for the versioned MADR frontmatter."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ai_engineering import decide, madr, outcome, paths

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "madr-v1.schema.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "madr-v1.json"
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


# The repository's own MADRs are validated as a set in one place. Every accepted record
# must show a committed transition, so this question needs a git repository to answer —
# and the mutation harness runs the suite in a copied tree that has none. Asking it there
# would be asking a different question, so it is asked once, where it can be answered.
def _repository_madrs_validate() -> None:
    if os.environ.get("AI_ENG_REAL_SRC"):
        pytest.skip("the mutation harness's copied tree has no git history to validate against")
    assert madr.validate(ROOT).outcome == "PASS"


def test_intent_supersession_madr_is_complete() -> None:
    predecessor = (
        ROOT
        / "docs"
        / "adr"
        / ("0004-no-document-mould-from-another-repository-enters-this-framew.md")
    )
    decision = ROOT / "docs" / "adr" / "0005-intent-supersedes-0004.md"
    expected = {
        "schema": "urn:ai-engineering:madr:1",
        "schema_version": "1",
        "type": "adr",
        "id": "0005",
        "title": "Intent supersedes the boundary of ADR 0004",
        "date": "2026-08-13",
        "spec": "010",
        "status": "accepted",
        "authority_role": "repository owner",
        "approval_ref": "ae523990",
        "approved_at": "2026-08-15T03:54:12Z",
        "supersedes": "0004",
    }
    expected_frontmatter = "\n".join(
        ["---", *(f"{key}: {json.dumps(value)}" for key, value in expected.items()), "---", ""]
    ).encode()

    raw = decision.read_bytes()
    parsed = madr._parse(raw)
    assert raw.startswith(expected_frontmatter)
    assert madr._v1_fields(parsed) == expected
    # The three travel together or not at all, and a role naming an agent or a reviewer is
    # refused by the schema — which is why none of them could be filled in by a model.
    # raw_fields keeps the quotes the file carries, which is the point of reading it raw.
    assert parsed.raw_fields["authority_role"] == '"repository owner"'
    assert parsed.raw_fields["approval_ref"] == '"ae523990"'
    assert parsed.raw_fields["approved_at"] == '"2026-08-15T03:54:12Z"'

    body = parsed.body
    assert "ADR 0004 remains correct about document moulds owned by another repository" in body
    assert "The canonical `.ai/intent.md` introduced by Spec 010 is not such a mould" in body
    assert all(
        option in body
        for option in (
            "1. **Keep ADR 0004 as the only decision",
            "2. **Rewrite or delete ADR 0004",
            "3. **Preserve ADR 0004 and supersede only its decision boundary",
        )
    )
    assert "Recommend option 3." in body
    # The bound moved with the transition: accepting the record approves the decision and
    # still authorizes nothing and accepts nothing, which is the sentence worth pinning.
    assert "it still authorizes no work and\naccepts no risk" in body
    assert "ADR 0004 remains unchanged as historical evidence" in body
    assert "Open risk:" in body
    assert "authority comes from its transition and from nothing else" in body

    assert sha256(predecessor.read_bytes()).hexdigest() == (
        "6c5e77f6f648ecae994435f27c7121866e04e3c9674ac5d0b9b16106d0b2447d"
    )
    _repository_madrs_validate()


def test_mission_madr_has_options_risks_and_owner() -> None:
    decision = ROOT / "docs" / "adr" / "0006-governed-mission.md"
    expected = {
        "schema": "urn:ai-engineering:madr:1",
        "schema_version": "1",
        "type": "adr",
        "id": "0006",
        "title": "Govern engineering work from intent to evidence",
        "date": "2026-08-13",
        "spec": "010",
        "status": "accepted",
        "authority_role": "repository owner",
        "approval_ref": "ae523990",
        "approved_at": "2026-08-15T03:54:12Z",
        "supersedes": "",
    }

    parsed = madr._parse(decision.read_bytes())
    assert madr._v1_fields(parsed) == expected
    # The three travel together or not at all, and a role naming an agent or a reviewer is
    # refused by the schema — which is why none of them could be filled in by a model.
    # raw_fields keeps the quotes the file carries, which is the point of reading it raw.
    assert parsed.raw_fields["authority_role"] == '"repository owner"'
    assert parsed.raw_fields["approval_ref"] == '"ae523990"'
    assert parsed.raw_fields["approved_at"] == '"2026-08-15T03:54:12Z"'

    body = " ".join(parsed.body.split())
    assert all(
        option in body
        for option in (
            "1. **Keep the narrow one-person safety mission",
            "2. **Restore the previous broad control plane",
            "3. **Govern the whole engineering journey with bounded autonomy",
        )
    )
    assert "Recommend option 3." in body
    assert "Proposed decision owner: the project maintainer role." in body
    assert "Open risk:" in body
    assert "does not by itself grant authority" in body
    assert "does not claim regulatory compliance" in body
    assert "is not acceptance of those risks and is not authority to implement" in body
    _repository_madrs_validate()


def test_cli_madr_has_hard_rename_and_transition_evidence() -> None:
    decision = ROOT / "docs" / "adr" / "0007-cli-contract.md"
    expected = {
        "schema": "urn:ai-engineering:madr:1",
        "schema_version": "1",
        "type": "adr",
        "id": "0007",
        "title": "Make the CLI outcome-first and exact",
        "date": "2026-08-13",
        "spec": "010",
        "status": "accepted",
        "authority_role": "repository owner",
        "approval_ref": "ae523990",
        "approved_at": "2026-08-15T03:54:12Z",
        "supersedes": "",
    }

    parsed = madr._parse(decision.read_bytes())
    assert madr._v1_fields(parsed) == expected
    # The three travel together or not at all, and a role naming an agent or a reviewer is
    # refused by the schema — which is why none of them could be filled in by a model.
    # raw_fields keeps the quotes the file carries, which is the point of reading it raw.
    assert parsed.raw_fields["authority_role"] == '"repository owner"'
    assert parsed.raw_fields["approval_ref"] == '"ae523990"'
    assert parsed.raw_fields["approved_at"] == '"2026-08-15T03:54:12Z"'

    body = " ".join(parsed.body.split())
    assert (
        "`init`, `doctor`, `update`, `spec`, `decide`, `accept`, `audit`, `report`, "
        "`exception` and `uninstall`"
    ) in body
    assert all(
        rename in body
        for rename in (
            "`--adr` to `--madr`",
            "`plan` to `exception`",
            "`digest` to `report digest`",
        )
    )
    assert "No old spelling remains as an alias" in body
    assert "Invalid CLI use exits 2 without writing state" in body
    assert "source checkout and installed wheel" in body
    assert "exactly one JSON object" in body
    assert "Open risk:" in body
    assert "No risk is accepted by this record" in body
    _repository_madrs_validate()


def _render_madr(record: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in record.items():
        rendered = json.dumps(value, separators=(",", ":"))
        lines.append(f"{key}: {rendered}")
    return "\n".join([*lines, "---", "", body.rstrip(), ""])


def _write_repository(root: Path, record: dict[str, Any], body: str) -> Path:
    specification = root / "specs" / "010-governed-foundation" / "spec.md"
    specification.parent.mkdir(parents=True, exist_ok=True)
    specification.write_text(
        '---\nid: "010"\nstatus: draft\n---\n\n# Governed foundation\n',
        encoding="utf-8",
    )
    decision = root / "docs" / "adr" / f"{record.get('id', '0001')}-decision.md"
    decision.parent.mkdir(parents=True, exist_ok=True)
    decision.write_text(_render_madr(record, body), encoding="utf-8")
    return decision


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=root, check=True)
    _commit_existing(root, message)


def _commit_existing(root: Path, message: str) -> None:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "role",
        "GIT_AUTHOR_EMAIL": "role",
        "GIT_COMMITTER_NAME": "role",
        "GIT_COMMITTER_EMAIL": "role",
    }
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", message], cwd=root, check=True, env=environment
    )


def _git_status(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.splitlines()


def _repository_with_spec(root: Path) -> None:
    specification = root / "specs" / "010-governed-foundation" / "spec.md"
    specification.parent.mkdir(parents=True)
    specification.write_text(
        '---\nid: "010"\nstatus: draft\n---\n\n# Governed foundation\n',
        encoding="utf-8",
    )
    _commit(root, "record specification")


def _run_semantic_fixture_case(
    tmp_path: Path, case: dict[str, Any], corpus: dict[str, Any]
) -> dict[str, str]:
    root = tmp_path / f"fixture-{case['id']}"
    base = corpus["base"]
    body = corpus["body"]
    first = _write_repository(root, base, body)
    scenario = case["mutation"]["scenario"]
    if scenario == "cycle":
        second = root / "docs" / "adr" / "0002-second.md"
        second.write_text(
            _render_madr({**base, "id": "0002", "title": "Second decision"}, body),
            encoding="utf-8",
        )
    _commit(root, "valid semantic baseline")

    if scenario == "invalid-transition":
        first.write_text(
            _render_madr({**base, "status": "superseded", **corpus["approval"]}, body),
            encoding="utf-8",
        )
        _commit_existing(root, "invalid transition")
    elif scenario == "duplicate-id":
        duplicate = root / "docs" / "adr" / "0009-duplicate.md"
        duplicate.write_text(_render_madr(base, body), encoding="utf-8")
    elif scenario == "self-link":
        first.write_text(_render_madr({**base, "supersedes": "0001"}, body), encoding="utf-8")
    elif scenario == "cycle":
        first.write_text(_render_madr({**base, "supersedes": "0002"}, body), encoding="utf-8")
        second.write_text(
            _render_madr(
                {**base, "id": "0002", "title": "Second decision", "supersedes": "0001"},
                body,
            ),
            encoding="utf-8",
        )
    elif scenario == "orphan-spec":
        first.write_text(_render_madr({**base, "spec": "999"}, body), encoding="utf-8")
    elif scenario == "orphan-supersession":
        first.write_text(_render_madr({**base, "supersedes": "9999"}, body), encoding="utf-8")
    else:
        raise AssertionError(f"unknown semantic fixture scenario: {scenario}")
    return madr.validate(root).as_dict()


def test_madr_validator_fails_closed_on_invalid_graph_and_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    base = corpus["base"]
    body = corpus["body"]
    cases = corpus["cases"]
    expected = corpus["taxonomy"]

    valid = tmp_path / "valid"
    decision = _write_repository(valid, base, body)
    _commit(valid, "record proposed decision")
    assert madr.validate(valid).as_dict() == expected["pass"]

    invalid_bodies = {
        "missing-section": body.rsplit("## Consequences", 1)[0],
        "duplicate-section": body + "\n\n## Consequences\n\nAgain.\n",
        "one-alternative": body.replace("2. Keep approval", "Keep approval"),
        "empty-consequences": body.rsplit("Authority remains", 1)[0],
        "empty-rejection-reason": body.replace(
            "Keep approval with an accountable role.\n\n## Consequences",
            "\n## Consequences",
        ),
        "fenced-sections": "# Decision\n\n````markdown\n" + body + "\n````\n",
        "fenced-alternatives": body.replace(
            "1. Let an automated actor approve its own work.\n"
            "2. Keep approval with an accountable role.",
            "````\n1. Hidden.\n2. Hidden.\n````",
        ),
    }
    executed: set[str] = set()
    for case in cases:
        assert set(case) == {"id", "classification", "mutation", "expected"}
        mutation = case["mutation"]
        if mutation["op"] == "scenario":
            continue
        candidate = deepcopy(base)
        rendered_body = body
        if mutation["op"] == "remove":
            candidate.pop(mutation["field"])
        elif mutation["op"] == "set":
            candidate[mutation["field"]] = mutation["value"]
        elif mutation["op"] == "set_approval":
            candidate = {**base, "status": "accepted", **corpus["approval"]}
            candidate[mutation["field"]] = mutation["value"]
        elif mutation["op"] == "add_approval":
            candidate[mutation["field"]] = corpus["approval"][mutation["field"]]
        elif mutation["op"] == "remove_approval":
            candidate = {**base, "status": mutation["status"], **corpus["approval"]}
            candidate.pop(mutation["field"])
        elif mutation["op"] == "body":
            scenario = mutation["scenario"]
            rendered_body = invalid_bodies[scenario]
            if scenario == "empty-rejection-reason":
                candidate = {**base, "status": "rejected", **corpus["approval"]}
        elif mutation["op"] != "raw":
            raise AssertionError(f"unknown fixture mutation: {mutation}")
        rendered = _render_madr(candidate, rendered_body)
        if mutation["op"] == "raw":
            field = mutation["field"]
            rendered = rendered.replace(
                f"{field}: {json.dumps(candidate[field])}", f"{field}: {mutation['value']}"
            )
        decision.write_text(rendered, encoding="utf-8")
        assert madr.validate(valid).as_dict() == expected[case["expected"]], case["id"]
        executed.add(case["id"])
    for case in cases:
        if case["mutation"]["op"] != "scenario":
            continue
        assert _run_semantic_fixture_case(tmp_path, case, corpus) == expected[case["expected"]]
        executed.add(case["id"])
    assert executed == {case["id"] for case in cases}

    decision.write_bytes(b"---\nschema: urn:ai-engineering:madr:1\n\xff\n")
    assert madr.validate(valid).as_dict() == expected["unreadable"]
    duplicate = _render_madr(base, body).replace(
        'title: "Keep authority outside the agent"\n',
        'title: "Keep authority outside the agent"\ntitle: "A second title"\n',
    )
    decision.write_text(duplicate, encoding="utf-8")
    assert madr.validate(valid).as_dict() == expected["ambiguous"]

    graph = tmp_path / "graph"
    _write_repository(graph, base, body)
    second_record = {**base, "id": "0002", "title": "Second decision"}
    (graph / "docs" / "adr" / "0002-second.md").write_text(
        _render_madr(second_record, body), encoding="utf-8"
    )
    _commit(graph, "record graph")
    assert madr.validate(graph).as_dict() == expected["pass"]

    duplicate_spec = graph / "specs" / "010-duplicate" / "spec.md"
    duplicate_spec.parent.mkdir(parents=True)
    duplicate_spec.write_text(
        '---\nid: "010"\nstatus: draft\n---\n\n# Duplicate\n', encoding="utf-8"
    )
    assert madr.validate(graph).as_dict() == expected["ambiguous"]

    outside = graph / "other" / "0003-outside.md"
    outside.parent.mkdir()
    outside.write_text(
        _render_madr({**base, "id": "0003", "title": "Outside"}, body), encoding="utf-8"
    )
    assert madr.validate(graph).as_dict() == expected["home_invalid"]

    transition = tmp_path / "transition"
    transition_record = deepcopy(base)
    transition_path = _write_repository(transition, transition_record, body)
    _commit(transition, "record proposed decision")
    transition_record.update(status="accepted", **corpus["approval"])
    transition_path.write_text(_render_madr(transition_record, body), encoding="utf-8")
    assert madr.validate(transition).as_dict() == expected["transition_invalid"]
    _commit_existing(transition, "accept decision")
    assert madr.validate(transition).outcome == "PASS"
    transition_record["status"] = "rejected"
    transition_path.write_text(_render_madr(transition_record, body), encoding="utf-8")
    assert madr.validate(transition).as_dict() == expected["transition_invalid"]
    transition_record["status"] = "superseded"
    transition_path.write_text(_render_madr(transition_record, body), encoding="utf-8")
    assert madr.validate(transition).as_dict() == expected["transition_invalid"]
    _commit_existing(transition, "supersede decision")
    assert madr.validate(transition).outcome == "PASS"
    transition_record["status"] = "accepted"
    transition_path.write_text(_render_madr(transition_record, body), encoding="utf-8")
    assert madr.validate(transition).as_dict() == expected["transition_invalid"]

    for status in ("accepted", "rejected", "superseded"):
        created = tmp_path / f"created-{status}"
        proposed = _write_repository(created, base, body)
        _commit(created, "baseline")
        proposed.unlink()
        _commit_existing(created, "remove proposal")
        _write_repository(created, {**base, "status": status, **corpus["approval"]}, body)
        assert madr.validate(created).as_dict() == expected["transition_invalid"]

    rejected = tmp_path / "rejected"
    rejected_path = _write_repository(rejected, base, body)
    _commit(rejected, "record proposed decision")
    rejected_path.write_text(
        _render_madr({**base, "status": "rejected", **corpus["approval"]}, body),
        encoding="utf-8",
    )
    _commit_existing(rejected, "reject decision")
    assert madr.validate(rejected).outcome == "PASS"
    rejected_path.write_text(
        _render_madr({**base, "status": "accepted", **corpus["approval"]}, body),
        encoding="utf-8",
    )
    assert madr.validate(rejected).as_dict() == expected["transition_invalid"]

    unsupported = deepcopy(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    unsupported["$schema"] = "https://json-schema.org/draft/2099-01/schema"
    unsupported_path = tmp_path / "unsupported-schema.json"
    unsupported_path.write_text(json.dumps(unsupported), encoding="utf-8")
    monkeypatch.setattr(madr, "SCHEMA_PATH", unsupported_path)
    assert madr.validate(valid).as_dict() == expected["schema_unsupported"]


def test_madr_reviewer_repro_home_detection_is_complete(tmp_path: Path) -> None:
    root = tmp_path / "home"
    _write_repository(root, _madr(), json.loads(FIXTURE_PATH.read_text())["body"])
    _commit(root, "baseline")
    outside = root / "docs" / "nested" / "0008-OUTSIDE.MD"
    outside.parent.mkdir(parents=True)
    outside.write_text(
        '\ufeff---\r\nschema: "urn:ai-engineering:madr:1"\r\n'
        'schema_version: "1"\r\ntype: adr\r\nid: "0008"\r\n---\r\n',
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_HOME_INVALID"


def test_madr_reviewer_repro_semantic_indexes_are_closed(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "indexes"
    decision = _write_repository(root, corpus["base"], corpus["body"])
    duplicate = root / "specs" / "999-duplicate" / "spec.md"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text('---\nid: "010"\nstatus: draft\n---\n', encoding="utf-8")
    _commit(root, "baseline")
    assert madr.validate(root).code == "MADR_AMBIGUOUS"
    duplicate.unlink()
    duplicate_content = root / "docs" / "adr" / "0009-duplicate-content.md"
    duplicate_content.parent.mkdir(parents=True, exist_ok=True)
    duplicate_content.write_text(_render_madr(corpus["base"], corpus["body"]), encoding="utf-8")
    assert madr.validate(root).code == "MADR_AMBIGUOUS"
    duplicate_content.unlink()
    decision.write_text(
        _render_madr({**corpus["base"], "supersedes": "0009"}, corpus["body"]),
        encoding="utf-8",
    )
    target = root / "docs" / "adr" / "0009-empty.md"
    target.write_text("", encoding="utf-8")
    assert madr.validate(root).code == "MADR_SCHEMA_INVALID"


def test_madr_reviewer_repro_fenced_markdown_is_not_evidence(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "fences"
    fenced = "# Decision\n\n````markdown\n" + corpus["body"] + "\n````\n"
    _write_repository(root, corpus["base"], fenced)
    _commit(root, "baseline")
    assert madr.validate(root).code == "MADR_BODY_INVALID"


def test_madr_reviewer_repro_schema_policy_is_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "policy"
    _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "baseline")
    schema = json.loads(SCHEMA_PATH.read_text())
    schema["x-owner-field"] = "approval_ref"
    schema["properties"]["title"]["x-status-transitions"] = {"allowed": "all"}
    changed = tmp_path / "changed-schema.json"
    changed.write_text(json.dumps(schema), encoding="utf-8")
    monkeypatch.setattr(madr, "SCHEMA_PATH", changed)
    assert madr.validate(root).code == "MADR_SCHEMA_UNSUPPORTED"


def test_madr_reviewer_repro_requires_usable_git(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    bare = tmp_path / "bare"
    _write_repository(bare, corpus["base"], corpus["body"])
    assert madr.validate(bare).code == "MADR_HISTORY_UNAVAILABLE"
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=bare, check=True)
    assert madr.validate(bare).code == "MADR_HISTORY_UNAVAILABLE"


def test_madr_reviewer_repro_fixture_contract_is_closed() -> None:
    corpus = json.loads(FIXTURE_PATH.read_bytes())
    assert set(corpus) == {
        "schema",
        "case_contract",
        "taxonomy",
        "base",
        "approval",
        "body",
        "cases",
    }
    assert corpus["schema"] == "urn:ai-engineering:madr-fixtures:2"
    assert corpus["case_contract"] == {
        "required": ["id", "classification", "mutation", "expected"],
        "additional_properties": False,
    }
    assert set(corpus["taxonomy"]) == {
        "pass",
        "schema_invalid",
        "schema_unsupported",
        "body_invalid",
        "unreadable",
        "ambiguous",
        "graph_invalid",
        "home_invalid",
        "transition_invalid",
        "history_unavailable",
    }
    expected_ids = {"cycle"} | set(
        re.findall(
            r"[a-z]+(?:-[a-z]+)+",
            "missing-schema missing-schema-version missing-type missing-id missing-title "
            "missing-date "
            "missing-spec missing-status missing-supersedes wrong-schema-type wrong-version-type "
            "wrong-type-type wrong-id-type wrong-title-type wrong-date-type wrong-spec-type "
            "wrong-status-enum wrong-supersedes-type wrong-authority-role-type "
            "wrong-approval-ref-type wrong-approved-at-type unknown-field malformed-schema "
            "malformed-version malformed-type malformed-id blank-title malformed-date "
            "malformed-spec "
            "malformed-supersedes forbidden-authority-role blank-approval-ref non-utc-approved-at "
            "approval-role-on-proposed approval-ref-on-proposed approved-at-on-proposed "
            "accepted-missing-role accepted-missing-ref accepted-missing-at rejected-missing-role "
            "rejected-missing-ref rejected-missing-at superseded-missing-role "
            "superseded-missing-ref "
            "superseded-missing-at unquoted-yes unquoted-no unquoted-on unquoted-off unquoted-null "
            "unquoted-nan unquoted-inf unquoted-hex unquoted-octal unquoted-scientific "
            "unquoted-time "
            "unquoted-bool unquoted-number body-missing-section body-duplicate-section "
            "body-one-alternative body-empty-consequences body-empty-rejection "
            "body-fenced-sections body-fenced-alternatives transition-invalid duplicate-id "
            "self-link "
            "cycle orphan-spec orphan-supersession",
        )
    )
    assert {case["id"] for case in corpus["cases"]} == expected_ids
    assert len(corpus["cases"]) == len(expected_ids)
    semantic_ids = {
        "transition-invalid",
        "duplicate-id",
        "self-link",
        "cycle",
        "orphan-spec",
        "orphan-supersession",
    }
    by_id = {case["id"]: case for case in corpus["cases"]}
    assert all(by_id[identifier]["mutation"]["op"] == "scenario" for identifier in semantic_ids)
    assert {by_id[identifier]["expected"] for identifier in semantic_ids} == {
        "transition_invalid",
        "ambiguous",
        "graph_invalid",
    }
    assert all(
        set(case) == set(corpus["case_contract"]["required"])
        and case["expected"] in corpus["taxonomy"]
        for case in corpus["cases"]
    )


def test_madr_reviewer_repro_checks_each_git_dag_edge(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "dag"
    _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "proposed")
    subprocess.run(["git", "branch", "left"], cwd=root, check=True)
    subprocess.run(["git", "checkout", "--quiet", "-b", "right"], cwd=root, check=True)
    right = root / "docs" / "adr" / "0003-right.md"
    right.write_text(
        _render_madr({**corpus["base"], "id": "0003", "title": "Right"}, corpus["body"]),
        encoding="utf-8",
    )
    _commit_existing(root, "right proposal")
    subprocess.run(["git", "checkout", "--quiet", "left"], cwd=root, check=True)
    left = root / "docs" / "adr" / "0002-left.md"
    left.write_text(
        _render_madr({**corpus["base"], "id": "0002", "title": "Left"}, corpus["body"]),
        encoding="utf-8",
    )
    _commit_existing(root, "left proposal")
    subprocess.run(
        ["git", "merge", "--quiet", "--no-ff", "right", "-m", "merge"], cwd=root, check=True
    )
    assert madr.validate(root).outcome == "PASS"


def test_madr_reviewer_repro_preserves_scalar_types(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "scalars"
    path = _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "baseline")
    path.write_text(
        _render_madr(corpus["base"], corpus["body"]).replace('id: "0001"', "id: 0001"),
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_SCHEMA_INVALID"
    path.write_text(
        _render_madr(corpus["base"], corpus["body"]).replace(
            'schema_version: "1"', "schema_version: 1"
        ),
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_SCHEMA_INVALID"
    path.write_text(
        _render_madr(corpus["base"], corpus["body"]).replace(
            'title: "Keep authority outside the agent"', "title: null"
        ),
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_SCHEMA_INVALID"


def test_madr_reviewer_repro_cycle_and_history_walks_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CountingDict(dict[str, str]):
        calls = 0

        def __contains__(self, key: object) -> bool:
            self.calls += 1
            return super().__contains__(key)

        def __getitem__(self, key: str) -> str:
            self.calls += 1
            return super().__getitem__(key)

    edges = CountingDict({f"{index:05d}": f"{index + 1:05d}" for index in range(5000)})
    assert madr._acyclic(edges)
    assert edges.calls < 50_000

    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "long-history"
    _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "baseline")
    progress = root / "progress.txt"
    for index in range(32):
        progress.write_text(f"{index}\n", encoding="utf-8")
        _commit_existing(root, f"progress {index}")

    original = madr.subprocess.run
    calls: list[tuple[str, ...]] = []

    def counted(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(tuple(command[3:]))
        return original(command, **kwargs)

    monkeypatch.setattr(madr.subprocess, "run", counted)
    assert madr.validate(root).outcome == "PASS"
    verbs = Counter(call[0] for call in calls)
    assert verbs["cat-file"] <= 5
    assert "show" not in verbs
    assert "ls-tree" not in verbs
    assert len(calls) <= 13


def test_madr_final_repro_discovery_is_conservative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "discovery"
    _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "baseline")
    note = root / "notes" / "note.md"
    note.parent.mkdir()
    note.write_text("---\ntitle: note\ntitle: duplicate\nbroken\n---\n", encoding="utf-8")
    (root / "notes" / "link.md").symlink_to(note)
    assert madr.validate(root).outcome == "PASS"
    (root / "notes" / "blank.md").write_text("---\ntitle:\n---\n", encoding="utf-8")
    assert madr.validate(root).outcome == "PASS"
    canonical = root / "docs" / "adr" / "0009-note.md"
    canonical.write_text("---\ntitle:\n---\n", encoding="utf-8")
    assert madr.validate(root).code == "MADR_SCHEMA_INVALID"
    canonical.write_bytes(b"---\ntitle: \xff\n---\n")
    assert madr.validate(root).code == "MADR_UNREADABLE"
    canonical.unlink()
    _repository_madrs_validate()

    (root / ".gitignore").write_text("ignored/\ndocs/adr/0009-hidden.md\n", encoding="utf-8")
    ignored = root / "ignored" / "0009-outside.md"
    ignored.parent.mkdir()
    ignored.write_text(_render_madr(corpus["base"], corpus["body"]), encoding="utf-8")
    assert madr.validate(root).code == "MADR_HOME_INVALID"
    ignored.unlink()
    hidden = root / "docs" / "adr" / "0009-hidden.md"
    hidden.write_text(_render_madr(corpus["base"], corpus["body"]), encoding="utf-8")
    assert madr.validate(root).code == "MADR_AMBIGUOUS"
    hidden.unlink()
    for index in range(64):
        (ignored.parent / f"payload-{index}.bin").write_bytes(b"x" * 131_072)
    original = Path.read_bytes
    fully_read: list[Path] = []

    def counted(path: Path) -> bytes:
        fully_read.extend([path] if path.is_relative_to(ignored.parent) else [])
        return original(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", counted)
        assert madr.validate(root).outcome == "PASS"
    assert fully_read == []
    oversized = ignored.parent / "frontmatter.bin"
    oversized.write_bytes(b"---\n" + b"x" * (madr._DISCOVERY_LIMIT + 1))
    assert madr.validate(root).code == "MADR_UNREADABLE"
    oversized.unlink()

    candidate = root / "notes" / "broken.md"
    rendered = _render_madr(corpus["base"], corpus["body"])
    escaped = (
        rendered.replace("madr:1", r"madr:\u0031").replace(
            'schema_version: "1"', 'schema_version: "2"'
        ),
        rendered.replace('schema: "urn:ai-engineering:madr:1"', 'schema: "different"').replace(
            'schema_version: "1"', r'schema_version: "\u0031"'
        ),
    )
    for record in escaped:
        candidate.write_text(record, encoding="utf-8")
        assert madr.validate(root).code == "MADR_HOME_INVALID"
    candidate.write_text(
        '\ufeff---\r\nschema: "urn:ai-engineering:madr:1"\r\nbroken\r\n---\r\n',
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_HOME_INVALID"
    candidate.unlink()
    madr_link = root / "docs" / "adr" / "0009-link.md"
    madr_link.symlink_to(note)
    assert madr.validate(root).outcome == "INCOMPLETE"
    madr_link.unlink()
    spec_link = root / "specs" / "011-link" / "spec.md"
    spec_link.parent.mkdir(parents=True)
    spec_link.symlink_to(note)
    assert madr.validate(root).outcome == "INCOMPLETE"


def test_madr_final_repro_dirty_status_never_transitions(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "dirty"
    path = _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "proposed")
    path.write_text(
        _render_madr(
            {**corpus["base"], "status": "accepted", **corpus["approval"]}, corpus["body"]
        ),
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_TRANSITION_INVALID"
    _commit_existing(root, "accepted")
    assert madr.validate(root).outcome == "PASS"
    accepted = {**corpus["base"], "status": "accepted", **corpus["approval"]}
    for field, value in (
        ("authority_role", "release maintainer"),
        ("approval_ref", "change-request-18"),
        ("approved_at", "2026-08-13T11:00:00Z"),
    ):
        path.write_text(_render_madr({**accepted, field: value}, corpus["body"]), encoding="utf-8")
        assert madr.validate(root).code == "MADR_TRANSITION_INVALID", field
    path.write_text(
        _render_madr(accepted, corpus["body"] + "\n\nBody clarification."), encoding="utf-8"
    )
    assert madr.validate(root).outcome == "PASS"
    second = {**corpus["base"], "id": "0002", "title": "Second proposal"}
    (root / "docs" / "adr" / "0002-second.md").write_text(
        _render_madr(second, corpus["body"]), encoding="utf-8"
    )
    assert madr.validate(root).outcome == "PASS"


def test_madr_final_repro_rejects_shallow_and_replace_history(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    source = tmp_path / "source"
    _write_repository(source, corpus["base"], corpus["body"])
    _commit(source, "one")
    (source / "progress").write_text("two\n", encoding="utf-8")
    _commit_existing(source, "two")

    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--quiet", "--depth=1", source.as_uri(), str(shallow)], check=True
    )
    assert madr.validate(shallow).code == "MADR_HISTORY_UNAVAILABLE"

    replaced = tmp_path / "replaced"
    subprocess.run(["git", "clone", "--quiet", str(source), str(replaced)], check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=replaced, check=True, capture_output=True, text=True
    ).stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD^"], cwd=replaced, check=True, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(["git", "replace", head, parent], cwd=replaced, check=True)
    assert madr.validate(replaced).code == "MADR_HISTORY_UNAVAILABLE"


def test_madr_final_repro_requires_json_quoted_scalars(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "quoted"
    path = _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "baseline")
    rendered = _render_madr(corpus["base"], corpus["body"])
    for quoted, invalid in (
        ('schema: "urn:ai-engineering:madr:1"', "schema: urn:ai-engineering:madr:1"),
        ('title: "Keep authority outside the agent"', "title: yes"),
        ('title: "Keep authority outside the agent"', "title: 0x10"),
        ('title: "Keep authority outside the agent"', "title: .nan"),
        ('title: "Keep authority outside the agent"', "title: 12:30"),
    ):
        path.write_text(rendered.replace(quoted, invalid), encoding="utf-8")
        assert madr.validate(root).code == "MADR_SCHEMA_INVALID", invalid
    escaped = {**corpus["base"], "title": 'Quoted "decision"'}
    path.write_text(_render_madr(escaped, corpus["body"]), encoding="utf-8")
    assert madr.validate(root).outcome == "PASS"


def test_madr_final_repro_commonmark_fences_are_exact(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "fences-final"
    path = _write_repository(root, corpus["base"], corpus["body"])
    _commit(root, "baseline")
    path.write_text(
        _render_madr(corpus["base"], "~~~language`tag\n" + corpus["body"] + "\n~~~\n"),
        encoding="utf-8",
    )
    assert madr.validate(root).code == "MADR_BODY_INVALID"
    unclosed = "````markdown\ninside\n```` trailing\n" + corpus["body"]
    path.write_text(_render_madr(corpus["base"], unclosed), encoding="utf-8")
    assert madr.validate(root).code == "MADR_BODY_INVALID"


def test_madr_final_repro_legacy_identity_comes_from_h1(tmp_path: Path) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text())
    root = tmp_path / "legacy"
    decision = _write_repository(
        root, {**corpus["base"], "supersedes": "0001", "id": "0002"}, corpus["body"]
    )
    decision.rename(root / "docs" / "adr" / "0002-decision.md")
    legacy = root / "docs" / "adr" / "0001-legacy.md"
    legacy.write_text(
        "---\nstatus: proposed\ndate: 2026-08-13\nspec: 010-governed-foundation\n"
        'supersedes: ""\n---\n\n# 0001. Legacy\n\nPreserved record.\n',
        encoding="utf-8",
    )
    _commit(root, "baseline")
    duplicate = root / "docs" / "adr" / "0009-copy.md"
    duplicate.write_bytes(legacy.read_bytes())
    assert madr.validate(root).code == "MADR_AMBIGUOUS"


def test_decide_madr_accepts_madr_and_rejects_adr_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "repository"
    _repository_with_spec(root)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    result = decide.main(["Keep authority outside the agent", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.splitlines() == [
        "  ✓ docs/adr/0001-keep-authority-outside-the-agent.md",
        "    outcome: PASS. status: proposed; this record grants no authority.",
    ]
    decision = root / "docs" / "adr" / "0001-keep-authority-outside-the-agent.md"
    assert madr.validate(root).outcome == "PASS"
    assert "authority_role:" not in decision.read_text(encoding="utf-8")
    assert not any("specs/" in line for line in _git_status(root))

    result = decide.main(["Reject an orphan", "--madr", "--supersede", "9999"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().out == (
        "  INCOMPLETE [MADR_GRAPH_INVALID]: MADR graph has a broken local edge. "
        "No change remains.\n"
    )
    assert not (root / "docs" / "adr" / "0002-reject-an-orphan.md").exists()
    assert madr.validate(root).outcome == "PASS"

    before_aliases = _git_status(root)
    for alias in ("--adr", "--mad", "--ma", "--m"):
        with pytest.raises(SystemExit) as stopped:
            decide.main(["Compatibility must stay deleted", alias])
        assert stopped.value.code == 2
        assert f"unrecognized arguments: {alias}" in capsys.readouterr().err
        assert _git_status(root) == before_aliases

    duplicate = root / "docs" / "adr" / "0009-duplicate.md"
    duplicate.write_bytes(decision.read_bytes())
    before = _git_status(root)
    result = decide.main(["Do not write through ambiguity", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().out == (
        "  INCOMPLETE [MADR_AMBIGUOUS]: MADR identity or target is ambiguous. "
        "Nothing was written.\n"
    )
    assert _git_status(root) == before


def test_decide_madr_creation_is_exclusive_and_cleans_partial_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    collision = tmp_path / "collision"
    _repository_with_spec(collision)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: collision)
    original_open = os.open
    colliding_bytes = b"created by a concurrent writer\n"

    def collide(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None):
        if isinstance(path, str) and path.endswith(".md") and flags & os.O_CREAT:
            competitor = original_open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o666,
                dir_fd=dir_fd,
            )
            try:
                os.write(competitor, colliding_bytes)
            finally:
                os.close(competitor)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", collide)
    result = decide.main(["Concurrent decision", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    output = capsys.readouterr().out
    collided = collision / "docs" / "adr" / "0001-concurrent-decision.md"
    assert "INCOMPLETE" in output and "MADR_WRITE_FAILED" in output
    assert "Nothing was written" not in output and "remains" in output
    assert collided.read_bytes() == colliding_bytes

    monkeypatch.setattr(os, "open", original_open)
    partial = tmp_path / "partial"
    _repository_with_spec(partial)
    preexisting_home = partial / "docs" / "adr"
    preexisting_home.mkdir(parents=True)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: partial)

    class PartialWriter:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> PartialWriter:
            return self

        def __exit__(self, *exc: Any) -> None:
            self.stream.close()

        def write(self, value: str) -> int:
            self.stream.write(value[:12])
            self.stream.flush()
            raise OSError("simulated partial write")

    original_fdopen = os.fdopen

    def fail_partly(fd: int, *args: Any, **kwargs: Any):
        return PartialWriter(original_fdopen(fd, *args, **kwargs))

    monkeypatch.setattr(os, "fdopen", fail_partly)
    result = decide.main(["Partial decision", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    output = capsys.readouterr().out
    assert "INCOMPLETE" in output and "MADR_WRITE_FAILED" in output
    assert "No change remains" in output
    assert preexisting_home.is_dir() and list(preexisting_home.iterdir()) == []


def test_decide_madr_never_follows_a_canonical_home_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "linked-home"
    _repository_with_spec(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "docs").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    result = decide.main(["Stay inside the repository", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "MADR_WRITE_FAILED" in capsys.readouterr().out
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("swapped", ["docs", "adr"])
def test_decide_madr_creation_stays_anchored_when_home_is_swapped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    swapped: str,
) -> None:
    root = tmp_path / f"swap-{swapped}"
    _repository_with_spec(root)
    home = root / "docs" / "adr"
    home.mkdir(parents=True)
    outside = tmp_path / f"outside-{swapped}"
    outside.mkdir()
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    original_open = os.open
    exchanged = False

    def exchange(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None):
        nonlocal exchanged
        if not exchanged and isinstance(path, str) and path.endswith(".md"):
            exchanged = True
            victim = root / "docs" if swapped == "docs" else home
            held = victim.with_name(f"{victim.name}-held")
            victim.rename(held)
            victim.symlink_to(outside, target_is_directory=True)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", exchange)
    result = decide.main(["Stay descriptor relative", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    output = capsys.readouterr().out
    assert exchanged and "INCOMPLETE" in output
    assert "MADR_HOME_INVALID" in output and "remains" in output
    assert list(outside.iterdir()) == []
    held = root / ("docs-held/adr" if swapped == "docs" else "docs/adr-held")
    assert list(held.iterdir()) == []


def test_decide_madr_fails_closed_without_descriptor_relative_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "unsupported"
    _repository_with_spec(root)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd - {os.open})

    result = decide.main(["Require anchored writes", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "MADR_WRITE_FAILED" in capsys.readouterr().out
    assert not (root / "docs").exists()


def test_decide_madr_closes_every_descriptor_after_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: set[int] = set()
    closed: set[int] = set()
    original_open = os.open
    original_close = os.close

    def tracked_open(*args: Any, **kwargs: Any) -> int:
        descriptor = original_open(*args, **kwargs)
        opened.add(descriptor)
        return descriptor

    def tracked_close(descriptor: int) -> None:
        closed.add(descriptor)
        original_close(descriptor)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(os, "close", tracked_close)

    success = tmp_path / "success-descriptors"
    _repository_with_spec(success)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: success)
    result = decide.main(["Close on success", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert opened <= closed

    opened.clear()
    closed.clear()
    failure = tmp_path / "failure-descriptors"
    _repository_with_spec(failure)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: failure)
    result = decide.main(["Close on failure", "--madr", "--supersede", "9999"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert opened <= closed


def test_decide_madr_validates_title_and_cleans_new_home_after_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "titles"
    _repository_with_spec(root)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    with pytest.raises(SystemExit) as stopped:
        decide.main(["   ", "--madr"])
    assert stopped.value.code == outcome.invalid_cli_exit()
    assert "needs a title" in capsys.readouterr().err
    assert not (root / "docs").exists()

    result = decide.main(["Ñ決定", "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    capsys.readouterr()
    fallback = root / "docs" / "adr" / "0001-decision-0001.md"
    assert fallback.exists() and madr.validate(root).outcome == "PASS"

    trailing_separator = "a" * 59 + " separator"
    result = decide.main([trailing_separator, "--madr"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    capsys.readouterr()
    names = sorted(path.name for path in (root / "docs" / "adr").iterdir())
    assert names[1] == f"0002-{'a' * 59}.md"
    assert all(re.fullmatch(r"[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md", name) for name in names)

    rejected = tmp_path / "rejected"
    _repository_with_spec(rejected)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: rejected)
    result = decide.main(["Orphan", "--madr", "--supersede", "9999"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "MADR_GRAPH_INVALID" in capsys.readouterr().out
    assert not (rejected / "docs").exists()


def test_decide_madr_listing_decodes_status_and_marks_malformed_values_unknown(
    tmp_path: Path,
) -> None:
    home = tmp_path / "docs" / "adr"
    home.mkdir(parents=True)
    (home / "0001-structured.md").write_text('---\nstatus: "proposed"\n---\n')
    (home / "0002-legacy.md").write_text("---\nstatus: accepted\n---\n")
    (home / "0003-broken.md").write_text('---\nstatus: "proposed\n---\n')
    (home / "0004-unknown.md").write_text('---\nstatus: "unknown"\n---\n')

    assert decide.listing(tmp_path) == [
        f"  {'0001-structured':<44} proposed",
        f"  {'0002-legacy':<44} accepted",
        f"  {'0003-broken':<44} ?",
        f"  {'0004-unknown':<44} ?",
    ]


def test_decide_accept_takes_its_authority_from_the_approved_intent(tmp_path, monkeypatch):
    """A record could only be accepted by hand-editing YAML, which is why this repository
    sat blocked waiting for values a person had to type into three files.

    The authority is not invented and it is not asked for again: it is read from the
    Solution Intent, which is committed, validated and already carries the human who
    approved it. An Intent that does not validate grants nothing. An Intent still in draft
    grants nothing, because a draft has no approval block to read.
    """

    from ai_engineering import decide, intent, paths

    root = tmp_path / "repository"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / ".ai").mkdir()
    record = json.loads((ROOT / ".ai" / "intent.md").read_text(encoding="utf-8"))
    spec_path = "specs/010-governed-agentic-engineering-foundation/spec.md"
    (root / "specs" / "010-governed-agentic-engineering-foundation").mkdir(parents=True)
    body = (ROOT / spec_path).read_bytes()
    (root / spec_path).write_bytes(body)

    def write_intent(lifecycle: dict) -> None:
        record["lifecycle"] = lifecycle
        (root / ".ai" / "intent.md").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    proposed = (
        '---\nschema: "urn:ai-engineering:madr:1"\nschema_version: "1"\ntype: "adr"\n'
        'id: "0009"\ntitle: "A decision that needs accepting"\ndate: "2026-08-15"\n'
        'spec: "010"\nstatus: "proposed"\nsupersedes: ""\n---\n\n# 0009. A decision\n'
    )
    decision = root / "docs" / "adr" / "0009-a-decision.md"
    decision.write_text(proposed, encoding="utf-8")
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    # A draft Intent has no approval block, so it grants nothing and nothing is written.
    write_intent({"status": "draft", "transitions": []})
    assert decide.main(["--accept", "0009"]).outcome == "INCOMPLETE"
    assert decision.read_text(encoding="utf-8") == proposed

    write_intent(json.loads(json.dumps(_ACTIVE_LIFECYCLE)))
    assert intent.validate(root / ".ai" / "intent.md", root).outcome == "PASS"
    assert decide.main(["--accept", "0009"]).outcome == "PASS"

    accepted = decision.read_text(encoding="utf-8")
    assert 'status: "accepted"' in accepted
    assert 'authority_role: "repository owner"' in accepted
    assert 'approval_ref: "ae523990"' in accepted
    assert re.search(r'approved_at: "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"', accepted)
    assert madr._parse(accepted.encode()).raw_fields["status"] == '"accepted"'

    # Accepting twice is not a second approval; the record has already left `proposed`.
    assert decide.main(["--accept", "0009"]).outcome == "INCOMPLETE"
    assert decision.read_text(encoding="utf-8") == accepted


_ACTIVE_LIFECYCLE = {
    "status": "active",
    "approval": {
        "authority_role": "repository owner",
        "approval_ref": "ae523990",
        "approved_at": "2026-08-15T03:54:12Z",
    },
    "transitions": [
        {
            "from": "draft",
            "to": "active",
            "changed_at": "2026-08-15T03:54:12Z",
            "authority_role": "repository owner",
            "approval_ref": "ae523990",
        }
    ],
}


def test_an_approved_specification_still_hashes_to_what_was_approved():
    """MADR 0008 approves five specifications at exact digests, and a digest is only as
    good as the discipline around it. Editing any of the five invalidates its approval,
    and nothing would have said so.

    That is not hypothetical: the audit found exactly this in specification 010's own
    plan, where an invalidated plan digest sat beside an approved one and no check in
    `src/`, `tests/` or `hooks/` read either. The gate was prose, so it could not fail.

    This reads the table out of the record and recomputes it. A specification that changed
    after approval turns red naming itself, which leaves two honest moves — revert the
    edit, or take the approval again — and removes the third, which is not noticing."""

    import hashlib
    import re

    record = (
        ROOT / "docs" / "adr" / "0008-the-five-wave-specifications-are-approved-at-exact-digests.md"
    )
    rows = re.findall(
        r"\| `(specs/[^`]+)` \| P\d \| `([0-9a-f]{16})` \|", record.read_text("utf-8")
    )
    assert len(rows) == 5, f"the approval table lost a row: {rows}"
    for folder, approved in rows:
        spec = ROOT / folder / "spec.md"
        assert spec.exists(), f"{folder} was approved and is not here"
        now = hashlib.sha256(spec.read_bytes()).hexdigest()[:16]
        assert now == approved, (
            f"{folder}/spec.md was approved at {approved} and now hashes to {now}: "
            f"either revert the edit or take the approval again"
        )
