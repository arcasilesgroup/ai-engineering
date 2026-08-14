"""The immutable acceptance register, as tests that fail.

An acceptance record is the one artifact in this repository that says a known problem may
stay. If its contract can be widened by an unknown field, a second spelling of an identity,
a renewal that rewrites its predecessor, or a value the schema never bounded, then the
record stops being evidence and becomes a place to hide. Every test here names one way that
could happen and goes red the moment it can.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "risk-acceptance-v1.schema.json"
REQUIRED = [
    "schema",
    "schema_version",
    "id",
    "spec",
    "spec_digest",
    "finding",
    "severity",
    "authority_role",
    "accepted",
    "expires",
    "renewals",
    "renews",
    "renews_digest",
    "justification",
    "evidence",
    "follow_up",
    "record_digest",
]
DIGEST = "sha256:" + "0" * 64
OTHER_DIGEST = "sha256:" + "1" * 64


def _has_format(value: str, format_name: str) -> bool:
    if format_name == "date":
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    raise AssertionError(f"unsupported format in test contract: {format_name}")


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    return root["$defs"][reference.removeprefix("#/$defs/")] if reference else schema


def _valid(instance: Any, schema: dict[str, Any], root: dict[str, Any]) -> bool:
    schema = _resolve(schema, root)
    if "const" in schema and instance != schema["const"]:
        return False
    if "enum" in schema and instance not in schema["enum"]:
        return False
    if "type" in schema:
        matches = {
            "object": isinstance(instance, dict),
            "string": isinstance(instance, str),
            "integer": isinstance(instance, int) and not isinstance(instance, bool),
        }[schema["type"]]
        if not matches:
            return False

    if isinstance(instance, str):
        if (
            not schema.get("minLength", 0)
            <= len(instance)
            <= schema.get("maxLength", len(instance))
        ):
            return False
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            return False
        if "format" in schema and not _has_format(instance, schema["format"]):
            return False
    if isinstance(instance, int) and not isinstance(instance, bool):
        low, high = schema.get("minimum", instance), schema.get("maximum", instance)
        if not low <= instance <= high:
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
    if "if" in schema:
        taken = "then" if _valid(instance, schema["if"], root) else "else"
        if taken in schema and not _valid(instance, schema[taken], root):
            return False
    return True


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
        "evidence": {"path": "specs/010-x/spec.md", "content_digest": OTHER_DIGEST},
        "follow_up": "",
        "record_digest": DIGEST,
    }
    record.update(overrides)
    return record


def _renewal(**overrides: Any) -> dict[str, Any]:
    base = {"id": "R-010-02", "renewals": 1, "renews": "R-010-01", "renews_digest": OTHER_DIGEST}
    return _record(**(base | overrides))


def test_risk_acceptance_v1_schema_is_closed_and_exact() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(schema) == {
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
        "x-acceptance-policy",
        "x-utf8-byte-limits",
    }
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:ai-engineering:risk-acceptance:1"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False

    # Every field is required. An optional field on this record would be a place to omit
    # the authority, the binding or the expiry and still look complete.
    assert schema["required"] == REQUIRED
    assert sorted(schema["properties"]) == sorted(REQUIRED)

    # The byte bounds the specification states are declared where the schema lives, because
    # maxLength counts characters and a 128-character value can be 512 bytes.
    assert schema["x-utf8-byte-limits"] == {
        "finding": 128,
        "authority_role": 128,
        "justification": 2000,
        "follow_up": 2000,
        "evidence.path": 1024,
    }
    for name, limit in schema["x-utf8-byte-limits"].items():
        node = schema["properties"]
        for part in name.split("."):
            node = node[part] if part in node else node["properties"][part]
        assert node["maxLength"] == limit

    policy = schema["x-acceptance-policy"]
    assert policy["home"] == "specs/NNN-slug/acceptance-r-NNN-NN/record.json"
    assert policy["spec_md_is_never_opened_for_write"] is True
    assert policy["publication"] == "native exclusive no-replace rename"
    assert policy["canonical_json"] == {
        "encoding": "utf-8",
        "bom": False,
        "sort_keys": True,
        "indent": 2,
        "allow_nan": False,
        "trailing_newline": True,
    }
    assert policy["record_digest_omits"] == ["record_digest"]
    assert policy["expires_not_before"] == "accepted"
    assert policy["evidence_max_bytes"] == 100_000
    assert policy["max_renewals"] == 2
    assert policy["third_renewal"] == "FAIL"
    assert policy["integrity_before_freshness"] is True
    assert policy["stale_head_is_renewable"] is True
    for outcome_field in ("unknown_field", "malformed", "digest_mismatch", "stale_binding"):
        assert policy[outcome_field] == "INCOMPLETE"
    # Five claims this record may never make, declared as data so a later reader cannot
    # quietly start making one of them.
    for never in (
        "record_digest_is_an_external_signature",
        "suppresses_failed_or_incomplete_checks",
        "claims_respondent_identity",
        "claims_power_loss_durability",
        "claims_tamper_proof_storage",
    ):
        assert policy[never] is False

    assert _valid(_record(), schema, schema)
    assert _valid(_renewal(), schema, schema)
    assert _valid(_renewal(renewals=2), schema, schema)
    assert _valid(_record(follow_up="open a durability fixture task"), schema, schema)

    rejected: list[dict[str, Any]] = [_record(unexpected="x")]
    rejected += [{k: v for k, v in _record().items() if k != field} for field in REQUIRED]
    rejected += [
        _record(schema="urn:ai-engineering:risk-acceptance:2"),
        _record(schema_version="2"),
        _record(id="R-10-01"),
        _record(id="r-010-01"),
        _record(id="R-010-1"),
        _record(spec="10"),
        _record(spec="0100"),
        _record(spec_digest="sha256:" + "0" * 63),
        _record(spec_digest="sha256:" + "A" * 64),
        _record(spec_digest=""),
        _record(finding=""),
        _record(finding="x" * 129),
        _record(severity="informational"),
        _record(severity=""),
        _record(authority_role=""),
        _record(authority_role="x" * 129),
        _record(accepted="14-08-2026"),
        _record(accepted="2026-02-30"),
        _record(expires=""),
        _record(renewals=-1),
        _record(renewals=3),
        _record(renewals=True),
        _record(renewals="0"),
        _record(renews="R-010-1"),
        _record(justification=""),
        _record(justification="x" * 2001),
        _record(follow_up="x" * 2001),
        _record(record_digest="sha1:" + "0" * 64),
        _record(evidence={}),
        _record(evidence={"path": "specs/010-x/spec.md"}),
        _record(evidence={"path": "specs/010-x/spec.md", "content_digest": DIGEST, "size": 1}),
        _record(evidence={"path": "", "content_digest": DIGEST}),
        _record(evidence={"path": "x" * 1025, "content_digest": DIGEST}),
        _record(evidence="specs/010-x/spec.md@" + DIGEST),
        # An original that names no predecessor cannot carry a renewal count or a
        # predecessor digest, and a renewal cannot drop either one.
        _record(renewals=1),
        _record(renews_digest=OTHER_DIGEST),
        _renewal(renewals=0),
        _renewal(renews_digest=""),
        _renewal(renews_digest="sha256:" + "z" * 64),
    ]
    for candidate in rejected:
        assert not _valid(candidate, schema, schema), candidate
