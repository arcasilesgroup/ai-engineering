"""Tests for spec 029 / B-029-2: the answer key decided before a gate runs.

The key is a closed, versioned contract: binary checks with `judged_by: run it | a/b pick`,
immutably digest-bound to the spec it judges. A reviewer applies it to the delivered work —
every check PASS, any FAIL, or `BLOCKED: U<n>` for an unknown observable, never a fabricated
score (wayfinder's falsifiable-standard pattern).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import answer_key  # noqa: E402

SCHEMA_PATH = ROOT / "policy" / "answer-key-v1.schema.json"


def _valid_key(spec: str = "029") -> dict:
    return {
        "schema": "urn:ai-engineering:answer-key:1",
        "schema_version": "1",
        "spec": spec,
        "spec_digest": "sha256:" + "0" * 64,
        "unknowns": ["U1"],
        "checks": [
            {
                "id": "c1",
                "statement": "the box is named",
                "judged_by": "run it",
                "command": "uv run python tests/test_answer_key.py",
            },
        ],
    }


def test_valid_key_passes_the_closed_schema():
    assert answer_key.validate(_valid_key()) == []


def test_the_schema_is_a_closed_2020_12_contract():
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    schema = json.loads(raw)
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema.get("additionalProperties") is False


def test_unknown_field_is_refused():
    key = _valid_key()
    key["extra"] = True
    assert any("unknown" in p for p in answer_key.validate(key))


def test_missing_spec_digest_is_refused():
    """spec_digest is required; a key that cannot bind to its spec is no standard."""
    key = _valid_key()
    del key["spec_digest"]
    assert any("required" in p or "spec" in p for p in answer_key.validate(key))


def test_non_binary_judged_by_is_refused():
    key = _valid_key()
    key["checks"][0]["judged_by"] = "taste"
    assert any("judged_by" in p for p in answer_key.validate(key))


def test_consuming_an_unknown_returns_blocked_not_a_score():
    verdict = answer_key.apply(_valid_key(), touched={"U1"})
    assert verdict == "BLOCKED: U1"


def test_consuming_all_run_it_passes():
    verdict = answer_key.apply(_valid_key(), touched=set(), failures=None)
    assert verdict == "PASS"


def test_consuming_a_failed_decided_check_is_fail():
    verdict = answer_key.apply(_valid_key(), touched=set(), failures={"c1"})
    assert verdict == "FAIL"
