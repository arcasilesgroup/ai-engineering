"""The immutable acceptance register, as tests that fail.

An acceptance record is the one artifact in this repository that says a known problem may
stay. If its contract can be widened by an unknown field, a second spelling of an identity,
a renewal that rewrites its predecessor, or a value the schema never bounded, then the
record stops being evidence and becomes a place to hide. Every test here names one way that
could happen and goes red the moment it can.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
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


def _corpus() -> dict[str, Any]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def _privacy_cases(check: str) -> list[dict[str, Any]]:
    return [case for case in _corpus()["privacy"] if case["check"] in {check, "all"}]


def test_acceptance_pii_v1_is_deterministic_and_fails_closed() -> None:
    from ai_engineering.acceptance_privacy import MAX_BYTES, Verdict, acceptance_pii_v1

    expected_outcome = {"FAIL": "FAIL", "INCOMPLETE": "INCOMPLETE", "CLEAN": "PASS"}
    for case in _privacy_cases("acceptance_pii_v1"):
        payload = base64.b64decode(case["payload_base64"]).decode("utf-8")
        verdict = acceptance_pii_v1(payload)
        assert verdict.outcome == expected_outcome[case["expected"]], case["id"]
        # Determinism is the property that makes this a check rather than an opinion.
        assert verdict == acceptance_pii_v1(payload), case["id"]
        # The verdict may name a class and may never carry the datum it found.
        assert payload not in repr(verdict), case["id"]
        assert payload not in json.dumps(verdict.as_dict()), case["id"]

    # Input this check cannot read is never clean.
    for unreadable in (None, 42, b"an email at jane.doe@example.com", ["text"]):
        assert acceptance_pii_v1(unreadable).code == "ACCEPTANCE_PRIVACY_UNSUPPORTED_INPUT"
    assert acceptance_pii_v1("\ud800").code == "ACCEPTANCE_PRIVACY_UNDECODABLE"
    assert acceptance_pii_v1("finding\x07bell").code == "ACCEPTANCE_PRIVACY_CONTROL_CHARACTER"

    # A bound must refuse, never report clean by giving up. The over-bound text below is
    # otherwise spotless, so only the bound can decide it.
    over = "a" * (MAX_BYTES + 1)
    assert acceptance_pii_v1(over) == Verdict(
        "INCOMPLETE",
        "ACCEPTANCE_PRIVACY_OVER_BOUND",
        f"the candidate exceeds the {MAX_BYTES}-byte scanning bound",
    )
    assert acceptance_pii_v1("a" * MAX_BYTES).outcome == "PASS"

    # A conclusive match outranks an ambiguity; text carrying both is already disqualified.
    both = "reviewed by Robin Case, reachable at jane.doe@example.com"
    assert acceptance_pii_v1(both).code == "ACCEPTANCE_PII_EMAIL"

    # Three shapes a looser scanner reads as personal data. Each one appears in real
    # acceptance prose, and refusing them would push people to reword until it passed.
    assert acceptance_pii_v1("accepted 2026-08-14 and expires 2026-11-14").outcome == "PASS"
    assert acceptance_pii_v1("the gate ran at 12:30:45 and stayed green").outcome == "PASS"
    assert acceptance_pii_v1("the scanner is gitleaks 8.30.1 exactly").outcome == "PASS"
    assert acceptance_pii_v1("repository maintainer accepted it").outcome == "PASS"


def test_acceptance_machine_path_v1_rejects_posix_windows_and_unc_paths() -> None:
    from ai_engineering import acceptance_privacy as privacy

    expected_outcome = {"FAIL": "FAIL", "INCOMPLETE": "INCOMPLETE", "CLEAN": "PASS"}
    for case in _privacy_cases("acceptance_machine_path_v1"):
        payload = base64.b64decode(case["payload_base64"]).decode("utf-8")
        verdict = privacy.acceptance_machine_path_v1(payload)
        assert verdict.outcome == expected_outcome[case["expected"]], case["id"]
        assert verdict == privacy.acceptance_machine_path_v1(payload), case["id"]
        assert payload not in repr(verdict), case["id"]
    codes = {
        case["id"]: privacy.acceptance_machine_path_v1(
            base64.b64decode(case["payload_base64"]).decode("utf-8")
        ).code
        for case in _privacy_cases("acceptance_machine_path_v1")
        if case["expected"] == "FAIL"
    }
    assert codes == {
        "machine-path-posix-home": "ACCEPTANCE_MACHINE_PATH_HOME",
        "machine-path-windows-drive": "ACCEPTANCE_MACHINE_PATH_WINDOWS_DRIVE",
        "machine-path-unc": "ACCEPTANCE_MACHINE_PATH_UNC",
    }

    # Unreadable input is unreadable for both checks, and by exactly the same answer.
    for unreadable in (None, 42, b"/home/somebody/x", ["text"]):
        assert privacy.acceptance_machine_path_v1(unreadable) == privacy.acceptance_pii_v1(
            unreadable
        )
    assert privacy.acceptance_machine_path_v1("x" * (privacy.MAX_BYTES + 1)).code.endswith(
        "OVER_BOUND"
    )

    # A repository-relative path is the only shape a record may carry, so it is the only
    # shape that reaches clean.
    for relative in (
        "specs/010-governed-foundation/spec.md",
        "the evidence is at docs/adr/0005-intent-supersedes-0004.md",
        "run just check and read the output",
        "see https://example.com/docs/renameat2 for the primary contract",
    ):
        assert privacy.acceptance_machine_path_v1(relative).outcome == "PASS", relative

    # An absolute path outside the three named families is undecidable, never clean.
    for absolute in ("the unit wrote /var/log/gate.txt", "compare against /etc/hosts first"):
        assert privacy.acceptance_machine_path_v1(absolute) == privacy.Verdict(
            "INCOMPLETE",
            "ACCEPTANCE_MACHINE_PATH_ABSOLUTE",
            "the candidate holds an absolute path this check cannot attribute to a machine",
        ), absolute

    # The two checks share compiled patterns and no mutable state, so interleaving them
    # cannot change either answer.
    home = "the log is at /home/somebody/gate.txt"
    person = "reviewed by Robin Case"
    isolated = (privacy.acceptance_machine_path_v1(home), privacy.acceptance_pii_v1(person))
    privacy.acceptance_pii_v1(home)
    privacy.acceptance_machine_path_v1(person)
    assert (privacy.acceptance_machine_path_v1(home), privacy.acceptance_pii_v1(person)) == isolated


def test_gitleaks_gate_requires_exact_version_and_three_clean_results(
    monkeypatch, tmp_path
) -> None:
    from ai_engineering import acceptance_privacy as privacy

    class _Result:
        def __init__(self, code: int, out: str = "") -> None:
            self.returncode, self.stdout, self.stderr = code, out, ""

    def _scanner(version: str | None, scan_code: int, *, error: Exception | None = None):
        calls: list[tuple[tuple[str, ...], Path]] = []

        def run(argv: tuple[str, ...], cwd: Path):
            calls.append((argv, cwd))
            if error is not None:
                raise error
            if argv[1] == "version":
                return _Result(0, f"{version}\n")
            return _Result(scan_code, "a redacted finding line")

        return run, calls

    situations = {case["situation"]: case["expected"] for case in _corpus()["gitleaks"]}
    assert situations == {
        "absent": "INCOMPLETE",
        "8.29.0": "INCOMPLETE",
        "exit_2": "INCOMPLETE",
        "8.30.1_exit_0": "CLEAN",
        "8.30.1_exit_1": "FAIL",
    }

    run, calls = _scanner(privacy.GITLEAKS_VERSION, 0)
    monkeypatch.setattr(privacy, "_run", run)
    assert privacy.gitleaks_v1(tmp_path).outcome == "PASS"
    # The exact command the specification names, run inside the unpublished record
    # directory and nowhere else.
    assert calls == [(("gitleaks", "version"), tmp_path), (privacy.GITLEAKS_ARGV, tmp_path)]
    assert privacy.GITLEAKS_ARGV == (
        "gitleaks",
        "dir",
        ".",
        "--redact",
        "--no-banner",
        "--exit-code",
        "1",
    )
    assert privacy.GITLEAKS_VERSION == "8.30.1"

    run, _ = _scanner(privacy.GITLEAKS_VERSION, 1)
    monkeypatch.setattr(privacy, "_run", run)
    found = privacy.gitleaks_v1(tmp_path)
    assert found.outcome == "FAIL" and found.code == "ACCEPTANCE_GITLEAKS_SECRET"
    # Exit 1 is the only conclusive failure, and the scanner's own output is not kept.
    assert "redacted finding line" not in repr(found)

    for version, code in ((privacy.GITLEAKS_VERSION, 2), ("8.29.0", 0), ("8.30.2", 0), (None, 0)):
        run, _ = _scanner(version, code)
        monkeypatch.setattr(privacy, "_run", run)
        verdict = privacy.gitleaks_v1(tmp_path)
        assert verdict.outcome == "INCOMPLETE", (version, code)
        assert verdict.code == "ACCEPTANCE_GITLEAKS_UNAVAILABLE", (version, code)

    for failure in (FileNotFoundError(), OSError("denied"), subprocess.SubprocessError()):
        run, _ = _scanner(privacy.GITLEAKS_VERSION, 0, error=failure)
        monkeypatch.setattr(privacy, "_run", run)
        assert privacy.gitleaks_v1(tmp_path).code == "ACCEPTANCE_GITLEAKS_UNAVAILABLE", failure

    # Only three clean results reach publication, and a conclusive failure outranks an
    # undecidable one: a candidate already known to carry a machine path is not rescued by
    # a second check that could not decide.
    run, _ = _scanner(privacy.GITLEAKS_VERSION, 0)
    monkeypatch.setattr(privacy, "_run", run)
    assert privacy.acceptance_privacy_gate(tmp_path, ["repository maintainer accepted it"]) is (
        privacy.CLEAN
    )
    assert privacy.acceptance_privacy_gate(tmp_path, ["the log is at /home/x/y.txt"]).outcome == (
        "FAIL"
    )
    assert privacy.acceptance_privacy_gate(tmp_path, ["reviewed by Robin Case"]).outcome == (
        "INCOMPLETE"
    )
    mixed = ["reviewed by Robin Case", "the log is at /home/x/y.txt"]
    assert privacy.acceptance_privacy_gate(tmp_path, mixed).outcome == "FAIL"

    run, _ = _scanner("8.29.0", 0)
    monkeypatch.setattr(privacy, "_run", run)
    assert privacy.acceptance_privacy_gate(tmp_path, ["clean text"]).outcome == "INCOMPLETE"


def _repository(tmp_path: Path, *, slug: str = "010-governed-foundation") -> Path:
    root = tmp_path / "repo"
    (root / "specs" / slug).mkdir(parents=True)
    for item in _corpus()["base"]["repository"]["files"]:
        target = root / item["path"].replace("010-governed-foundation", slug)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")
    return root


def _bound(root: Path, slug: str, **overrides: Any) -> dict[str, Any]:
    """The corpus base record, with its digests bound to what is actually on disk."""

    from ai_engineering import acceptance

    record = json.loads(json.dumps(_corpus()["base"]["record"]))
    record.update(overrides)
    spec = root / "specs" / slug / "spec.md"
    evidence_path = f"specs/{slug}/durability.md"
    record["spec_digest"] = "sha256:" + hashlib.sha256(spec.read_bytes()).hexdigest()
    record["evidence"] = {
        "path": evidence_path,
        "content_digest": "sha256:"
        + hashlib.sha256((root / evidence_path).read_bytes()).hexdigest(),
    }
    record["record_digest"] = acceptance.record_digest(record)
    return record


def _publish(root: Path, slug: str, record: dict[str, Any], leaf: str | None = None) -> Path:
    from ai_engineering import acceptance

    where = root / "specs" / slug / (leaf or "acceptance-" + record["id"].lower())
    where.mkdir(parents=True)
    (where / "record.json").write_bytes(acceptance.canonical_bytes(record))
    return where


def _legacy(root: Path, slug: str, block: str) -> None:
    spec = root / "specs" / slug / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8") + "\n" + block + "\n", encoding="utf-8")


def test_unified_reader_separates_integrity_from_binding_freshness(tmp_path) -> None:
    from ai_engineering import acceptance

    slug = "010-governed-foundation"
    root = _repository(tmp_path)
    record = _bound(root, slug)
    _publish(root, slug, record)

    decided = acceptance.read(root)
    assert decided.outcome == "PASS", decided.as_dict()
    assert [entry.id for entry in decided.entries] == ["R-010-01"]
    assert decided.entries[0].provenance == acceptance.CANONICAL_RECORD
    assert acceptance.current(root).outcome == "PASS"

    # Freshness. The spec moves; the record does not. Integrity still passes, the binding
    # does not, and the record keeps its place in the register so it stays renewable.
    spec = root / "specs" / slug / "spec.md"
    original = spec.read_bytes()
    spec.write_text("# Governed foundation, edited after the decision\n", encoding="utf-8")
    assert acceptance.read(root).outcome == "PASS"
    stale = acceptance.current(root)
    assert stale.outcome == "INCOMPLETE" and stale.code == "ACCEPTANCE_BINDING_STALE"
    assert [entry.id for entry in stale.entries] == ["R-010-01"]

    # Order. With the binding already stale, a corrupt self digest is what comes back:
    # integrity is decided first, and a corrupt record is never reported as merely stale.
    corrupt = dict(record, record_digest="sha256:" + "9" * 64)
    (root / "specs" / slug / "acceptance-r-010-01" / "record.json").write_bytes(
        acceptance.canonical_bytes(corrupt)
    )
    both = acceptance.current(root)
    assert both.outcome == "INCOMPLETE" and both.code == "ACCEPTANCE_CHECKSUM"
    assert both.entries == ()
    spec.write_bytes(original)
    assert acceptance.current(root).code == "ACCEPTANCE_CHECKSUM"


def test_unified_reader_reads_frozen_legacy_history_without_rewriting_it(tmp_path) -> None:
    from ai_engineering import acceptance

    slug = "001-v1-from-scratch"
    root = _repository(tmp_path, slug=slug)
    blocks = {case["id"]: case for case in _corpus()["legacy_blocks"]}
    spec = root / "specs" / slug / "spec.md"

    _legacy(root, slug, blocks["legacy-valid"]["block"])
    before = spec.read_bytes()
    decided = acceptance.read(root)
    assert decided.outcome == "PASS", decided.as_dict()
    assert [entry.provenance for entry in decided.entries] == [acceptance.STORED_LEGACY]
    assert spec.read_bytes() == before, "reading history may never rewrite it"

    # The digest covers the exact stored span, opening backtick through closing backtick.
    start = before.index(b"```yaml")
    end = before.index(b"```", start + 8) + 3
    assert decided.entries[0].digest == "sha256:" + hashlib.sha256(before[start:end]).hexdigest()

    _legacy(root, slug, blocks["legacy-id-less"]["block"])
    _legacy(root, slug, blocks["legacy-renewals-once"]["block"])
    _legacy(root, slug, blocks["legacy-not-an-acceptance"]["block"])
    decided = acceptance.read(root)
    assert decided.outcome == "PASS", decided.as_dict()
    # Three acceptances; the fourth block names no finding and no expiry, so the frozen
    # recognizer leaves it alone rather than guessing at somebody else's YAML.
    assert len(decided.entries) == 3
    assert [entry.provenance for entry in decided.entries] == [
        acceptance.STORED_LEGACY,
        acceptance.DERIVED_LEGACY,
        acceptance.STORED_LEGACY,
    ]
    # `once` is not a number and holds no digit, which is exactly the shipped behaviour.
    assert decided.entries[2].renewals == 0

    for malformed in (
        "legacy-unknown-key",
        "legacy-wrong-container-type",
        "legacy-renewals-out-of-range",
        "legacy-malformed-date",
    ):
        fresh = _repository(tmp_path / malformed, slug=slug)
        _legacy(fresh, slug, blocks[malformed]["block"])
        result = acceptance.read(fresh)
        assert result.outcome == "INCOMPLETE", malformed
        assert result.entries == (), malformed


def test_unified_reader_refuses_rather_than_returning_a_partial_register(tmp_path) -> None:
    from ai_engineering import acceptance

    slug = "010-governed-foundation"

    def fresh(name: str) -> Path:
        return _repository(tmp_path / name)

    # An unknown field, a non-canonical encoding and a wrong container are each refused.
    root = fresh("unknown")
    record = _bound(root, slug)
    where = _publish(root, slug, record)
    (where / "record.json").write_bytes(
        acceptance.canonical_bytes(dict(record, reviewer="not allowed"))
    )
    assert acceptance.read(root).code == "ACCEPTANCE_MALFORMED"

    root = fresh("noncanonical")
    record = _bound(root, slug)
    where = _publish(root, slug, record)
    (where / "record.json").write_text(json.dumps(record, indent=4), encoding="utf-8")
    assert acceptance.read(root).code == "ACCEPTANCE_MALFORMED"

    root = fresh("path")
    record = _bound(root, slug)
    _publish(root, slug, record, leaf="acceptance-r-010-07")
    assert acceptance.read(root).code == "ACCEPTANCE_PATH_MISMATCH"

    root = fresh("owner")
    record = _bound(root, slug, id="R-011-01")
    _publish(root, slug, record)
    assert acceptance.read(root).code == "ACCEPTANCE_OWNER_MISMATCH"

    root = fresh("duplicate")
    record = _bound(root, slug)
    _publish(root, slug, record)
    other = root / "specs" / "010-other"
    other.mkdir()
    (other / "spec.md").write_text("# Another home for the same number\n", encoding="utf-8")
    (other / "durability.md").write_text("No receipt.\n", encoding="utf-8")
    twin = _bound(root, "010-other")
    twin["spec_digest"] = record["spec_digest"]
    twin["evidence"] = record["evidence"]
    twin["record_digest"] = acceptance.record_digest(twin)
    _publish(root, "010-other", twin)
    assert acceptance.read(root).code == "ACCEPTANCE_DUPLICATE_ID"

    root = fresh("undecidable")
    nameless = root / "specs" / "note"
    nameless.mkdir()
    (nameless / "spec.md").write_text("# A leaf with no three-digit owner\n", encoding="utf-8")
    assert acceptance.read(root).code == "ACCEPTANCE_UNDECIDABLE_OWNER"

    # Bounds refuse; they never report what happened to fit.
    root = fresh("bound")
    (root / "specs" / slug / "spec.md").write_bytes(b"x" * (acceptance.MAX_SPEC_BYTES + 1))
    assert acceptance.read(root).code == "ACCEPTANCE_OVER_BOUND"

    root = fresh("total")
    monkey_budget = acceptance.MAX_TOTAL_BYTES
    try:
        acceptance.MAX_TOTAL_BYTES = 4
        assert acceptance.read(root).code == "ACCEPTANCE_OVER_BOUND"
    finally:
        acceptance.MAX_TOTAL_BYTES = monkey_budget

    # A path that is not exactly one singly linked regular file on this volume is refused.
    root = fresh("symlink")
    spec = root / "specs" / slug / "spec.md"
    real = root / "specs" / slug / "elsewhere.md"
    spec.rename(real)
    spec.symlink_to(real)
    assert acceptance.read(root).code == "ACCEPTANCE_UNSAFE_PATH"

    root = fresh("hardlink")
    spec = root / "specs" / slug / "spec.md"
    os.link(spec, root / "specs" / slug / "second-name.md")
    assert acceptance.read(root).code == "ACCEPTANCE_UNSAFE_PATH"


def test_no_acceptance_result_can_change_another_checks_status(tmp_path) -> None:
    """The one property that separates a record from a bypass.

    An acceptance says a known problem may stay. It has never turned a `FAIL` or an
    `INCOMPLETE` into a `PASS`, and this reader returns state a caller reads — never a
    verdict about somebody else's check.
    """

    from ai_engineering import acceptance

    slug = "010-governed-foundation"
    root = _repository(tmp_path)
    live = _bound(root, slug, expires="2099-01-01")
    _publish(root, slug, live)

    # A live acceptance is state, not permission: nothing here reports a check as passing.
    assert acceptance.expired(root).outcome == "PASS"
    assert acceptance.expired(root).entries == ()
    assert acceptance.read(root).outcome == "PASS"

    gone = json.loads(json.dumps(live))
    gone["expires"] = "2020-01-01"
    gone["accepted"] = "2019-01-01"
    gone["record_digest"] = acceptance.record_digest(gone)
    (root / "specs" / slug / "acceptance-r-010-01" / "record.json").write_bytes(
        acceptance.canonical_bytes(gone)
    )
    lapsed = acceptance.expired(root)
    assert lapsed.outcome == "PASS" and [entry.id for entry in lapsed.entries] == ["R-010-01"]

    # Every outcome this module can produce, over every state it can read, is one of two
    # words. Neither of them can upgrade another check's result.
    outcomes = {
        acceptance.read(root).outcome,
        acceptance.current(root).outcome,
        acceptance.expired(root).outcome,
        acceptance.read(tmp_path / "absent").outcome,
    }
    assert outcomes <= {"PASS", "INCOMPLETE"}
    assert set(acceptance.Register("PASS").as_dict()) == {"outcome", "count"}
    assert (
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["x-acceptance-policy"][
            "suppresses_failed_or_incomplete_checks"
        ]
        is False
    )
