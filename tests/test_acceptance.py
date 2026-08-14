"""The immutable acceptance register, as tests that fail.

An acceptance record is the one artifact in this repository that says a known problem may
stay. If its contract can be widened by an unknown field, a second spelling of an identity,
a renewal that rewrites its predecessor, or a value the schema never bounded, then the
record stops being evidence and becomes a place to hide. Every test here names one way that
could happen and goes red the moment it can.
"""

from __future__ import annotations

import base64
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "risk-acceptance-v1.schema.json"
CORPUS_PATH = ROOT / "tests" / "fixtures" / "risk-acceptance-v1.json"
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


# The exact cases the specification names. Adding or removing one is a deliberate edit to
# this list, not something a corpus rewrite can do quietly.
RECORD_CASES = [
    "canonical-original",
    "canonical-renewal",
    "historical-gap-is-filled",
    "unknown-field",
    "missing-field",
    "wrong-container-type",
    "oversized-finding",
    "oversized-justification",
    "oversized-evidence-path",
    "severity-outside-enum",
    "renewals-out-of-range",
    "original-carries-a-renewal-count",
    "renewal-drops-its-predecessor-digest",
    "malformed-date",
    "invalid-utf8",
    "control-character",
    "non-canonical-json",
    "path-disagrees-with-id",
    "id-owner-disagrees-with-spec-directory",
    "spec-field-disagrees-with-directory",
    "duplicate-id",
    "exhausted-ordinal",
    "undecidable-noncanonical-leaf",
    "wrong-record-digest",
    "wrong-renews-digest",
    "renewal-cycle",
    "renewal-fork",
    "missing-predecessor",
    "stale-spec-binding",
    "stale-evidence-binding",
    "expiry-before-accepted",
    "evidence-over-one-hundred-thousand-bytes",
    "third-renewal",
]
LEGACY_CASES = [
    "legacy-valid",
    "legacy-id-less",
    "legacy-renewals-once",
    "legacy-not-an-acceptance",
    "legacy-unknown-key",
    "legacy-wrong-container-type",
    "legacy-renewals-out-of-range",
    "legacy-malformed-date",
    "legacy-missing-finding",
    "legacy-noncanonical-home",
]
PRIVACY_CASES = [
    "pii-secret",
    "pii-email",
    "pii-ip-address",
    "pii-phone-like",
    "pii-personal-name-ambiguity",
    "machine-path-posix-home",
    "machine-path-windows-drive",
    "machine-path-unc",
    "clean-role-and-reason",
]
GITLEAKS_CASES = [
    "gitleaks-missing",
    "gitleaks-wrong-version",
    "gitleaks-unexpected-exit",
    "gitleaks-clean",
    "gitleaks-hit",
]
CLASSIFICATIONS = {
    "valid",
    "schema_invalid",
    "malformed_bytes",
    "register_invalid",
    "integrity_invalid",
    "freshness_invalid",
    "policy_invalid",
    "policy_refused",
    "ignored",
    "malformed",
}
ENFORCERS = {"schema", "reader", "register", "writer"}


def _apply(record: dict[str, Any], mutations: list[dict[str, Any]]) -> dict[str, Any]:
    mutated = json.loads(json.dumps(record))
    for mutation in mutations:
        target, *rest = mutation["path"]
        node, key = mutated, target
        for step in rest:
            node, key = node[key], step
        if mutation["op"] == "remove":
            del node[key]
        elif mutation["op"] == "set":
            node[key] = mutation["value"]
        elif mutation["op"] == "set_repeated":
            node[key] = mutation["unit"] * mutation["count"]
        elif mutation["op"] == "set_base64":
            node[key] = base64.b64decode(mutation["value"]).decode("utf-8")
        else:
            raise AssertionError(f"unsupported mutation op in corpus: {mutation['op']}")
    return mutated


def test_acceptance_corpus_covers_valid_adversarial_and_privacy_cases() -> None:
    raw = CORPUS_PATH.read_bytes()
    corpus = json.loads(raw.decode("utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert corpus["schema"] == "urn:ai-engineering:risk-acceptance-fixtures:1"
    assert corpus["schema_version"] == "1"

    base = corpus["base"]["record"]
    assert _valid(base, schema, schema)
    evidence_path = base["evidence"]["path"]
    assert evidence_path in {file["path"] for file in corpus["base"]["repository"]["files"]}

    cases = corpus["cases"]
    assert [case["id"] for case in cases] == RECORD_CASES
    for case in cases:
        assert case["classification"] in CLASSIFICATIONS, case["id"]
        assert case["enforced_by"] in ENFORCERS, case["id"]
        assert case["expected"] in {"PASS", "FAIL", "INCOMPLETE"}, case["id"]

    # Only the schema-enforced cases may be decided by the schema. The rest must pass it and
    # be caught later, which is exactly why the reader, register and writer tasks exist; a
    # corpus that let the schema catch them would hide a missing gate behind a green test.
    for case in cases:
        if "mutations" not in case:
            continue
        candidate = _apply(base, case["mutations"])
        decided = _valid(candidate, schema, schema)
        if case["enforced_by"] == "schema":
            assert decided is (case["expected"] == "PASS"), case["id"]
        else:
            assert decided, case["id"]

    # A third renewal is refused before a record exists, because the schema caps the counter
    # at two: there is no valid record shape to publish and then reject.
    third = next(case for case in cases if case["id"] == "third-renewal")
    assert "mutations" not in third
    assert (
        third["request"]["would_be_renewals"] == schema["x-acceptance-policy"]["max_renewals"] + 1
    )
    assert not _valid(
        _apply(base, [{"op": "set", "path": ["renewals"], "value": 3}]), schema, schema
    )

    invalid_utf8 = next(case for case in cases if case["id"] == "invalid-utf8")
    payload = base64.b64decode(invalid_utf8["record_bytes_base64"])
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        raise AssertionError("the invalid-utf8 case decodes as utf-8, so it proves nothing")

    non_canonical = next(case for case in cases if case["id"] == "non-canonical-json")
    canonical = schema["x-acceptance-policy"]["canonical_json"]
    encoding = non_canonical["encoding"]
    assert encoding["indent"] != canonical["indent"]
    assert encoding["sort_keys"] != canonical["sort_keys"]
    assert encoding["trailing_newline"] != canonical["trailing_newline"]

    legacy = corpus["legacy_blocks"]
    assert [block["id"] for block in legacy] == LEGACY_CASES
    for block in legacy:
        assert block["block"].startswith("```yaml\n") and block["block"].endswith("\n```")
        assert block["expected"] in {"PASS", "INCOMPLETE", "IGNORED"}, block["id"]
        assert block["home"].startswith("specs/") and block["home"].endswith("/spec.md")
    id_less = next(block for block in legacy if block["id"] == "legacy-id-less")
    assert id_less["provenance"] == "derived legacy"
    assert re.fullmatch(r"R-[0-9]{3}-[0-9]{2}", id_less["derived_id"])
    assert "id:" not in id_less["block"]

    privacy = corpus["privacy"]
    assert [case["id"] for case in privacy] == PRIVACY_CASES
    for case in privacy:
        assert case["check"] in {
            "acceptance_pii_v1",
            "acceptance_machine_path_v1",
            "gitleaks",
            "all",
        }
        assert case["expected"] in {"FAIL", "INCOMPLETE", "CLEAN"}, case["id"]
        decoded = base64.b64decode(case["payload_base64"])
        assert decoded, case["id"]
        # Rule 8: the corpus may describe a secret, a personal datum or a machine path, and
        # may never commit one. Encoded is the whole point; a plaintext copy defeats it.
        assert decoded not in raw, case["id"]

    assert [case["id"] for case in corpus["gitleaks"]] == GITLEAKS_CASES
    for case in corpus["gitleaks"]:
        assert case["expected"] in {"FAIL", "INCOMPLETE", "CLEAN"}, case["id"]
    situations = {case["situation"] for case in corpus["gitleaks"]}
    assert situations == {"absent", "8.29.0", "exit_2", "8.30.1_exit_0", "8.30.1_exit_1"}
