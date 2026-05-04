"""spec-119 T-1.8 -- lint-violation envelope schema (D-119-05) conformance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.eval

_SCHEMA_REL = Path(".ai-engineering") / "schemas" / "lint-violation.schema.json"


@pytest.fixture()
def schema(repo_root: Path) -> dict:
    return json.loads((repo_root / _SCHEMA_REL).read_text(encoding="utf-8"))


def _validate(schema: dict, doc: dict) -> tuple[bool, str]:
    """Lightweight validator. Avoids pulling jsonschema into the dev surface
    when the schema is small and stable. Returns (ok, reason)."""
    required = set(schema["required"])
    missing = required - doc.keys()
    if missing:
        return False, f"missing required: {sorted(missing)}"
    allowed = set(schema["properties"].keys())
    extra = doc.keys() - allowed
    if schema.get("additionalProperties") is False and extra:
        return False, f"unknown keys: {sorted(extra)}"
    severity_enum = set(schema["properties"]["severity"]["enum"])
    if doc["severity"] not in severity_enum:
        return False, f"severity must be in {sorted(severity_enum)}"
    rule_id = doc["rule_id"]
    if not rule_id or not rule_id[0].islower():
        return False, "rule_id must be kebab-case starting with lowercase letter"
    if "line" in doc and (not isinstance(doc["line"], int) or doc["line"] < 1):
        return False, "line must be 1-indexed integer"
    return True, ""


class TestLintViolationSchema:
    def test_canonical_envelope_is_valid(self, schema: dict):
        envelope = {
            "rule_id": "logger-structured-args",
            "severity": "error",
            "expected": "logger.info({event, ...data})",
            "actual": "console.log(`event=${event}`)",
            "fix_hint": "Replace console.log with logger.info passing a structured object",
            "file": "src/auth/login.ts",
            "line": 42,
        }
        ok, reason = _validate(schema, envelope)
        assert ok, reason

    def test_minimum_required_envelope(self, schema: dict):
        envelope = {
            "rule_id": "no-magic-numbers",
            "severity": "warning",
            "expected": "named constant",
            "actual": "literal 42",
            "fix_hint": "extract to a named constant",
        }
        ok, reason = _validate(schema, envelope)
        assert ok, reason

    def test_rejects_missing_fix_hint(self, schema: dict):
        envelope = {
            "rule_id": "x-y",
            "severity": "info",
            "expected": "a",
            "actual": "b",
        }
        ok, reason = _validate(schema, envelope)
        assert not ok
        assert "fix_hint" in reason

    def test_rejects_unknown_severity(self, schema: dict):
        envelope = {
            "rule_id": "x-y",
            "severity": "blocker",
            "expected": "a",
            "actual": "b",
            "fix_hint": "do thing",
        }
        ok, reason = _validate(schema, envelope)
        assert not ok
        assert "severity" in reason

    def test_rejects_unknown_extra_field(self, schema: dict):
        envelope = {
            "rule_id": "x-y",
            "severity": "error",
            "expected": "a",
            "actual": "b",
            "fix_hint": "do thing",
            "owner": "team-x",  # not in schema
        }
        ok, reason = _validate(schema, envelope)
        assert not ok
        assert "owner" in reason

    def test_rejects_zero_line_number(self, schema: dict):
        envelope = {
            "rule_id": "x-y",
            "severity": "error",
            "expected": "a",
            "actual": "b",
            "fix_hint": "do thing",
            "line": 0,
        }
        ok, reason = _validate(schema, envelope)
        assert not ok
        assert "line" in reason
