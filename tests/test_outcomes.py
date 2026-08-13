from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ai_engineering import outcome

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "outcome-v1.schema.json"
ROOT_KEYS = {
    "$id",
    "$schema",
    "additionalProperties",
    "description",
    "oneOf",
    "properties",
    "required",
    "title",
    "type",
    "x-outcome-policy",
}
OUTCOMES = {
    "READY": (
        0,
        "Preconditions are freshly proven; no requested mutation ran",
        "begin only the stated permitted operation",
    ),
    "PASS": (
        0,
        "The requested operation and all applicable checks completed",
        "continue to the next governed stage",
    ),
    "WARN": (
        0,
        "Work completed with a non-blocking bounded condition",
        "inspect the warning, then continue or remediate",
    ),
    "FAIL": (
        1,
        "An executed check conclusively found a violation",
        "remediate the violation and rerun",
    ),
    "INCOMPLETE": (
        1,
        "The framework cannot decide or prove the claim",
        "obtain/repair authority, capability or evidence and rerun",
    ),
    "CANCELLED": (
        130,
        "Explicit cancellation stopped work before a decision",
        "confirm intent, then restart as a new operation",
    ),
    "WOULD_CHANGE": (
        0,
        "A complete dry run derived exact changes and made none",
        "review the proposed changes, then run without dry-run",
    ),
}


def _valid(instance: Any, schema: dict[str, Any]) -> bool:
    if not isinstance(instance, dict):
        return False
    if set(schema["required"]) - set(instance):
        return False
    if schema["additionalProperties"] is False and set(instance) - set(schema["properties"]):
        return False
    for key, rule in schema["properties"].items():
        value = instance[key]
        if rule["type"] == "string" and not isinstance(value, str):
            return False
        if rule["type"] == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            return False
        if "const" in rule and value != rule["const"]:
            return False
        if "enum" in rule and value not in rule["enum"]:
            return False
        if isinstance(value, str) and len(value) < rule.get("minLength", 0):
            return False
    matching = 0
    for branch in schema["oneOf"]:
        if all(instance[key] == rule["const"] for key, rule in branch["properties"].items()):
            matching += 1
    return matching == 1


def _outcome(name: str) -> dict[str, Any]:
    exit_code, reason, next_action = OUTCOMES[name]
    return {
        "schema": "urn:ai-engineering:outcome:1",
        "schema_version": "1",
        "outcome": name,
        "exit_code": exit_code,
        "reason": reason,
        "next_action": next_action,
    }


def test_outcome_v1_schema_is_closed_and_exact() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(schema) == ROOT_KEYS
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:ai-engineering:outcome:1"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "schema",
        "schema_version",
        "outcome",
        "exit_code",
        "reason",
        "next_action",
    ]
    assert set(schema["properties"]) == set(schema["required"])
    assert schema["properties"]["outcome"]["enum"] == list(OUTCOMES)
    assert schema["x-outcome-policy"] == {
        "phase_only": ["RUNNING"],
        "invalid_cli_exit": 2,
        "unknown_normalizes_to": "INCOMPLETE",
        "dry_run_undecidable": "INCOMPLETE",
        "ordered_outcomes": list(OUTCOMES),
    }

    branch_contract = {
        branch["properties"]["outcome"]["const"]: (
            branch["properties"]["exit_code"]["const"],
            branch["properties"]["reason"]["const"],
            branch["properties"]["next_action"]["const"],
        )
        for branch in schema["oneOf"]
    }
    assert branch_contract == OUTCOMES
    assert all(_valid(_outcome(name), schema) for name in OUTCOMES)

    invalid = []
    for name in OUTCOMES:
        wrong_exit = _outcome(name)
        wrong_exit["exit_code"] = 130 if wrong_exit["exit_code"] != 130 else 0
        invalid.append(wrong_exit)
    missing = _outcome("PASS")
    del missing["next_action"]
    invalid.append(missing)
    unknown = {**_outcome("PASS"), "authority": "agent"}
    invalid.append(unknown)
    running = {**_outcome("PASS"), "outcome": "RUNNING"}
    invalid.append(running)
    boolean_exit = {**_outcome("PASS"), "exit_code": False}
    invalid.append(boolean_exit)
    invented_reason = deepcopy(_outcome("FAIL"))
    invented_reason["reason"] = "looks bad"
    invalid.append(invented_reason)
    assert all(not _valid(candidate, schema) for candidate in invalid)


def test_outcome_core_maps_status_to_exact_exit_and_next_action(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name, (exit_code, reason, next_action) in OUTCOMES.items():
        result = outcome.result(name)
        assert result.as_dict() == _outcome(name)
        assert result.exit_code == exit_code
        assert result.reason == reason
        assert result.next_action == next_action

    assert outcome.result("RUNNING").outcome == "INCOMPLETE"
    assert outcome.result("UNKNOWN").outcome == "INCOMPLETE"
    assert outcome.result("").outcome == "INCOMPLETE"
    assert outcome.result(None).outcome == "INCOMPLETE"
    assert outcome.dry_run(exact_changes=True).outcome == "WOULD_CHANGE"
    assert outcome.dry_run(exact_changes=False).outcome == "INCOMPLETE"
    assert outcome.dry_run(exact_changes=1).outcome == "INCOMPLETE"
    assert outcome.invalid_cli_exit() == 2

    with pytest.raises(ValueError, match="do not match"):
        outcome.Result(
            "urn:ai-engineering:outcome:1",
            "1",
            "PASS",
            1,
            OUTCOMES["PASS"][1],
            OUTCOMES["PASS"][2],
        )
    with pytest.raises(ValueError, match="version"):
        outcome.Result("invented", "1", "PASS", *OUTCOMES["PASS"])

    changed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    changed["x-outcome-policy"]["invalid_cli_exit"] = 0
    changed_path = tmp_path / "outcome.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")
    with monkeypatch.context() as scoped:
        scoped.setattr(outcome, "SCHEMA_PATH", changed_path)
        with pytest.raises(outcome.OutcomePolicyError):
            outcome.result("PASS")

    linked = tmp_path / "linked.json"
    linked.symlink_to(SCHEMA_PATH)
    with monkeypatch.context() as scoped:
        scoped.setattr(outcome, "SCHEMA_PATH", linked)
        with pytest.raises(outcome.OutcomePolicyError):
            outcome.result("PASS")
