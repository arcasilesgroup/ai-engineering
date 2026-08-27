from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ai_engineering import evidence, outcome, paths

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "policy" / "check-evidence-v1.schema.json"
COMMON = [
    "schema",
    "schema_version",
    "kind",
    "id",
    "applicability",
    "command",
    "tool_version",
    "input_digest",
    "artifact_digest",
    "started_at",
    "finished_at",
    "max_age_seconds",
    "outcome",
]
HUMAN = [
    "test_id",
    "owner_role",
    "protocol_id",
    "protocol_version",
    "environment_id",
    "environment_version",
    "observation_date",
    "receipt_digest",
]
RFC3339_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")


def _format(value: str, name: str) -> bool:
    try:
        if name == "date":
            return date.fromisoformat(value).isoformat() == value
        if RFC3339_UTC.fullmatch(value) is None:
            return False
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        return parsed.utcoffset().total_seconds() == 0
    except (AttributeError, ValueError):
        return False


def _resolve(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = node.get("$ref")
    return root["$defs"][reference.removeprefix("#/$defs/")] if reference else node


def _valid(value: Any, node: dict[str, Any], root: dict[str, Any]) -> bool:
    node = _resolve(node, root)
    if "const" in node and value != node["const"]:
        return False
    if "enum" in node and value not in node["enum"]:
        return False
    expected = node.get("type")
    if expected == "object" and not isinstance(value, dict):
        return False
    if expected == "string" and not isinstance(value, str):
        return False
    if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        return False
    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            return False
        if "pattern" in node and __import__("re").search(node["pattern"], value) is None:
            return False
        if "format" in node and not _format(value, node["format"]):
            return False
    if isinstance(value, int) and value < node.get("minimum", value):
        return False
    if isinstance(value, dict):
        if set(node.get("required", ())) - set(value):
            return False
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False and set(value) - set(properties):
            return False
        if any(
            key in value and not _valid(value[key], rule, root) for key, rule in properties.items()
        ):
            return False
    if "allOf" in node and not all(_valid(value, rule, root) for rule in node["allOf"]):
        return False
    if "anyOf" in node and not any(_valid(value, rule, root) for rule in node["anyOf"]):
        return False
    if "not" in node and _valid(value, node["not"], root):
        return False
    if "if" in node:
        branch = "then" if _valid(value, node["if"], root) else "else"
        if branch in node and not _valid(value, node[branch], root):
            return False
    return True


def _record(kind: str = "automated") -> dict[str, Any]:
    record = {
        "schema": "urn:ai-engineering:check-evidence:1",
        "schema_version": "1",
        "kind": kind,
        "id": "quality.test",
        "applicability": "applicable",
        "command": "just test",
        "tool_version": "pytest-9.1.1",
        "input_digest": "sha256:" + "a" * 64,
        "artifact_digest": "sha256:" + "b" * 64,
        "started_at": "2026-08-13T20:00:00Z",
        "finished_at": "2026-08-13T20:01:00Z",
        "max_age_seconds": 86400,
        "outcome": "PASS",
    }
    if kind in {"human", "external"}:
        record.update(
            test_id="journey.checkout",
            owner_role="product maintainer",
            protocol_id="checkout.protocol",
            protocol_version="1",
            environment_id="release.fixture",
            environment_version="1",
            observation_date="2026-08-13",
            receipt_digest="sha256:" + "c" * 64,
        )
    if kind == "external":
        record.update(independent_path="external.checkout", limits="One clean fixture")
    return record


def _expectation(record: dict[str, Any]) -> evidence.Expectation:
    conditional = {
        field: record[field]
        for field in [
            *(field for field in HUMAN if field != "observation_date"),
            "independent_path",
            "limits",
            "reason",
        ]
        if field in record
    }
    return evidence.Expectation(
        kind=record["kind"],
        id=record["id"],
        applicability=record["applicability"],
        command=record["command"],
        tool_version=record["tool_version"],
        input_digest=record["input_digest"],
        artifact_digest=record["artifact_digest"],
        max_age_seconds=record["max_age_seconds"],
        **conditional,
    )


def test_check_evidence_schema_requires_receipt_owner_protocol_and_independence() -> None:
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
        "x-evidence-policy",
    }
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:ai-engineering:check-evidence:1"
    assert schema["additionalProperties"] is False
    assert schema["required"] == COMMON
    assert schema["properties"]["input_digest"] == {"$ref": "#/$defs/digest"}
    assert schema["properties"]["artifact_digest"] == {"$ref": "#/$defs/digest"}
    assert schema["properties"]["receipt_digest"] == {"$ref": "#/$defs/digest"}
    assert schema["x-evidence-policy"] == {
        "freshness_field": "max_age_seconds",
        "missing": "INCOMPLETE",
        "stale": "INCOMPLETE",
        "malformed": "INCOMPLETE",
        "digest_mismatch": "INCOMPLETE",
        "executed_fail": "FAIL",
        "metadata_is_proof": False,
        "not_applicable_covers_applicable": False,
        "independent_kind": "external",
    }
    assert all(_valid(_record(kind), schema, schema) for kind in ("automated", "human", "external"))

    invalid = []
    for field in HUMAN:
        candidate = _record("human")
        del candidate[field]
        invalid.append(candidate)
    for field in ("independent_path", "limits"):
        candidate = _record("external")
        del candidate[field]
        invalid.append(candidate)
    for field in [*HUMAN, "independent_path", "limits"]:
        candidate = _record()
        candidate[field] = _record("external")[field]
        invalid.append(candidate)
    not_applicable = _record()
    not_applicable["applicability"] = "not_applicable"
    invalid.append(not_applicable)
    invented = {**_record(), "green": True}
    invalid.append(invented)
    bad_digest = {**_record(), "artifact_digest": "sha256:ABC"}
    invalid.append(bad_digest)
    bad_age = {**_record(), "max_age_seconds": 0}
    invalid.append(bad_age)
    assert all(not _valid(candidate, schema, schema) for candidate in invalid)

    not_applicable["reason"] = "No deployable artifact exists"
    assert _valid(not_applicable, schema, schema)
    applicable_reason = deepcopy(_record())
    applicable_reason["reason"] = "skip"
    assert not _valid(applicable_reason, schema, schema)


def test_evidence_verifier_distinguishes_fail_missing_stale_malformed_and_digest_mismatch() -> None:
    now = datetime(2026, 8, 13, 20, 2, tzinfo=UTC)
    record = _record()
    expected = _expectation(record)

    passed = evidence.verify(record, expected=expected, now=now)
    assert passed.result == outcome.result("PASS")
    assert (passed.outcome, passed.code) == ("PASS", "EVIDENCE_VERIFIED")

    failed_record = {**record, "outcome": "FAIL"}
    failed = evidence.verify(failed_record, expected=expected, now=now)
    assert failed.result == outcome.result("FAIL")
    assert failed.code == "EVIDENCE_EXECUTED_FAIL"

    cases = [
        (None, now, "EVIDENCE_MISSING"),
        (
            {
                **record,
                "started_at": "2026-08-12T20:00:00Z",
                "finished_at": "2026-08-12T20:01:59Z",
            },
            now,
            "EVIDENCE_STALE",
        ),
        ({"outcome": "PASS", "green": True}, now, "EVIDENCE_MALFORMED"),
        (
            {**failed_record, "artifact_digest": "sha256:" + "c" * 64},
            now,
            "EVIDENCE_DIGEST_MISMATCH",
        ),
    ]
    for candidate, observed_at, code in cases:
        result = evidence.verify(candidate, expected=expected, now=observed_at)
        assert result.result == outcome.result("INCOMPLETE")
        assert (result.outcome, result.code) == ("INCOMPLETE", code)

    not_applicable = {
        **record,
        "applicability": "not_applicable",
        "reason": "No deployable artifact exists",
        "outcome": "PASS",
    }
    mismatch = evidence.verify(record, expected=_expectation(not_applicable), now=now)
    assert (mismatch.outcome, mismatch.code) == (
        "INCOMPLETE",
        "EVIDENCE_APPLICABILITY_MISMATCH",
    )
    skipped = evidence.verify(
        not_applicable,
        expected=_expectation(not_applicable),
        now=now,
    )
    assert skipped.result == outcome.result("PASS")
    assert skipped.code == "EVIDENCE_NOT_APPLICABLE"


def test_evidence_verifier_rejects_non_rfc3339_utc_timestamps() -> None:
    now = datetime(2026, 8, 13, 20, 2, tzinfo=UTC)
    record = _record()
    expected = _expectation(record)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    invalid = [
        "20260813T200100Z",
        "2026-W33-4T20:01:00Z",
        "2026-08-13T20:01Z",
        "2026-08-13 20:01:00Z",
        "2026-08-13T20:01:00,5Z",
        "2026-02-30T20:01:00Z",
    ]

    assert all(
        not _valid({**record, "finished_at": timestamp}, schema, schema) for timestamp in invalid
    )
    assert all(
        evidence.verify({**record, "finished_at": timestamp}, expected=expected, now=now).code
        == "EVIDENCE_MALFORMED"
        for timestamp in invalid
    )

    fractional = {**record, "finished_at": "2026-08-13T20:01:00.123456Z"}
    assert _valid(fractional, schema, schema)
    assert evidence.verify(fractional, expected=expected, now=now).outcome == "PASS"


def test_not_applicable_evidence_preserves_executed_fail_and_warn_outcomes() -> None:
    now = datetime(2026, 8, 13, 20, 2, tzinfo=UTC)
    record = {
        **_record(),
        "applicability": "not_applicable",
        "reason": "No deployable artifact exists",
    }
    expected = _expectation(record)
    cases = {
        "FAIL": ("FAIL", "EVIDENCE_EXECUTED_FAIL"),
        "WARN": ("WARN", "EVIDENCE_VERIFIED_WITH_WARNING"),
        "PASS": ("PASS", "EVIDENCE_NOT_APPLICABLE"),
    }

    for label, result in cases.items():
        verified = evidence.verify({**record, "outcome": label}, expected=expected, now=now)
        assert (verified.outcome, verified.code) == result


def test_evidence_verifier_binds_requirement_types_receipts_and_time() -> None:
    now = datetime(2026, 8, 13, 20, 2, tzinfo=UTC)
    human = _record("human")
    expected = _expectation(human)

    warning = evidence.verify({**human, "outcome": "WARN"}, expected=expected, now=now)
    assert warning.result == outcome.result("WARN")
    assert warning.code == "EVIDENCE_VERIFIED_WITH_WARNING"

    wrong_receipt = {**human, "receipt_digest": "sha256:" + "d" * 64}
    assert evidence.verify(wrong_receipt, expected=expected, now=now).code == (
        "EVIDENCE_DIGEST_MISMATCH"
    )

    mismatched = [
        {**human, "id": "quality.other"},
        {**human, "command": "true"},
        {**human, "max_age_seconds": human["max_age_seconds"] + 1},
        {**human, "protocol_version": "2"},
        _record(),
    ]
    assert all(
        evidence.verify(candidate, expected=expected, now=now).code
        == "EVIDENCE_REQUIREMENT_MISMATCH"
        for candidate in mismatched
    )

    malformed = [
        {**human, "started_at": "2026-08-13T20:03:00Z"},
        {**human, "finished_at": "2026-08-13T20:03:00Z"},
        {**human, "observation_date": "2026-08-12"},
        {**human, "max_age_seconds": True},
        json.dumps(human)[:-1] + ',"outcome":"FAIL"}',
    ]
    assert all(
        evidence.verify(candidate, expected=expected, now=now).code == "EVIDENCE_MALFORMED"
        for candidate in malformed
    )

    invalid_now = now.replace(tzinfo=None)
    invalid_expected = replace(expected, max_age_seconds=True)
    unserializable_expected = replace(expected, kind=object())
    assert evidence.verify(human, expected=expected, now=invalid_now).code == (
        "EVIDENCE_REQUIREMENT_INVALID"
    )
    assert evidence.verify(human, expected=invalid_expected, now=now).code == (
        "EVIDENCE_REQUIREMENT_INVALID"
    )
    assert evidence.verify(human, expected=unserializable_expected, now=now).code == (
        "EVIDENCE_REQUIREMENT_INVALID"
    )

    boundary = {
        **human,
        "started_at": (now - timedelta(days=1, minutes=1)).isoformat().replace("+00:00", "Z"),
        "finished_at": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
    }
    boundary["observation_date"] = "2026-08-12"
    assert evidence.verify(boundary, expected=expected, now=now).outcome == "PASS"

    external = _record("external")
    external_expected = _expectation(external)
    assert evidence.verify(external, expected=external_expected, now=now).outcome == "PASS"
    wrong_path = {**external, "independent_path": "internal.checkout"}
    assert evidence.verify(wrong_path, expected=external_expected, now=now).code == (
        "EVIDENCE_REQUIREMENT_MISMATCH"
    )


def test_evidence_verifier_fails_closed_when_canonical_policy_changes(
    tmp_path: Path, monkeypatch: Any
) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema["description"] = "Unapproved replacement"
    changed = tmp_path / "check-evidence-v1.schema.json"
    changed.write_text(json.dumps(schema), encoding="utf-8")
    monkeypatch.setattr(evidence, "SCHEMA_PATH", changed)

    result = evidence.verify(
        _record(),
        expected=_expectation(_record()),
        now=datetime(2026, 8, 13, 20, 2, tzinfo=UTC),
    )
    assert result.result == outcome.result("INCOMPLETE")
    assert result.code == "EVIDENCE_POLICY_UNSUPPORTED"


def test_the_policy_is_read_from_one_bounded_regular_file_and_nothing_else(tmp_path):
    """Forty-seven mutants lived in the reader that decides which policy is in force.

    The shared `paths.read_bounded` is the same hardened shape as
    `update._read_pin`, and for the same reason:
    the bytes it returns decide what counts as evidence, so a file swapped underneath it is a
    way to change the rules a gate applies. Every refusal it can make is its own case here,
    because one wrong file and one refusal passes with the other conditions deleted.

    All of them arrive as the same code. That is deliberate — the caller's decision is that the
    policy cannot be trusted, not which of five ways it failed — so what each case asserts is
    that the refusal happened at all, and the conditions are separated by construction instead.
    """
    import os
    import stat as _stat

    from ai_engineering import evidence

    good = tmp_path / "policy.json"
    good.write_text("{}", encoding="utf-8")
    assert paths.read_bounded(good, 1_000, "evidence policy") == b"{}"

    # A symlink, even one pointing at a perfectly good policy. `O_NOFOLLOW` and the `S_ISLNK`
    # check together, because a platform without the flag still has the stat. The shared
    # reader raises OSError naming what happened; the caller wraps it as its problem.
    linked = tmp_path / "linked.json"
    linked.symlink_to(good)
    with pytest.raises(OSError):
        paths.read_bounded(linked, 1_000, "evidence policy")

    # A directory is not a file, and the refusal must come from the mode rather than from
    # whatever a read of a directory does on this platform.
    folder = tmp_path / "folder.json"
    folder.mkdir()
    with pytest.raises(OSError):
        paths.read_bounded(folder, 1_000, "evidence policy")

    # Absent is refused rather than read as an empty policy — an empty policy is one that
    # requires nothing, which is the most dangerous thing this file could return.
    with pytest.raises(OSError):
        paths.read_bounded(tmp_path / "absent.json", 1_000, "evidence policy")

    # And over the bound. The reader takes one byte more than the bound and refuses if it
    # arrives, so a policy exactly at the bound is still read.
    over = tmp_path / "over.json"
    over.write_bytes(b"x" * (evidence._MAX_POLICY_BYTES + 1))
    with pytest.raises(OSError):
        paths.read_bounded(over, evidence._MAX_POLICY_BYTES, "evidence policy")

    exact = tmp_path / "exact.json"
    exact.write_bytes(b"x" * evidence._MAX_POLICY_BYTES)
    raw = paths.read_bounded(exact, evidence._MAX_POLICY_BYTES, "evidence policy")
    assert len(raw) == evidence._MAX_POLICY_BYTES

    # A device or socket is neither a link nor a regular file, and the check is written as
    # "is regular" rather than "is not a link" for exactly that reason.
    assert _stat.S_ISREG(os.lstat(good).st_mode)


def test_a_policy_that_changes_while_it_is_read_is_refused(tmp_path, monkeypatch):
    """The two identity comparisons, which no arrangement of files can trigger from outside.

    One is between the stat before the open and the stat of the descriptor; the other is
    between that and a stat after the read. A policy replaced in either window is one this
    reader would return the wrong bytes for, and the wrong bytes here are the wrong rules.
    """
    from ai_engineering import evidence

    where = tmp_path / "policy.json"
    where.write_text("{}", encoding="utf-8")
    from ai_engineering import paths

    real = paths.os.fstat

    class Elsewhere:
        def __init__(self, base):
            self._base = base

        def __getattr__(self, name):
            if name == "st_ino":
                return 999_999
            return getattr(self._base, name)

    monkeypatch.setattr(paths.os, "fstat", lambda fd: Elsewhere(real(fd)))
    with pytest.raises(OSError):
        paths.read_bounded(where, evidence._MAX_POLICY_BYTES, "evidence policy")
