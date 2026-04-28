"""Phase 4 GREEN: audit-report.json schema contract (spec-106 G-4).

Asserts the JSON shape emitted by ``scripts/skill-audit.sh``: a JSON array
where each entry is an object containing a ``skill`` field (string) and a
``result`` field (object with ``score`` and ``reason`` fields). The schema
is the contract downstream consumers (CI dashboards, hard-gate enforcement
in future specs) rely on.

Validated against ``tests/fixtures/audit_report_sample.json`` -- a small
hand-curated set of three entries (above-threshold, sub-threshold, eval-
failed-cli-missing) that exercises the full schema surface without
requiring the bash script to run during unit testing.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_REPORT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "audit_report_sample.json"


def _load_fixture() -> list[dict]:
    """Load the canonical audit-report sample fixture."""
    return json.loads(AUDIT_REPORT_FIXTURE.read_text(encoding="utf-8"))


def test_audit_report_is_json_array() -> None:
    """The report must be a JSON document whose root is a list."""
    assert AUDIT_REPORT_FIXTURE.exists(), (
        f"Missing fixture: {AUDIT_REPORT_FIXTURE}. Phase 4 T-4.4 requires the "
        "sample to validate the audit-report.json schema contract."
    )
    payload = _load_fixture()
    assert isinstance(payload, list), (
        f"audit-report.json root must be a JSON array, got {type(payload).__name__}"
    )
    assert len(payload) >= 1, "audit-report.json fixture must contain >=1 entry"


def test_each_entry_has_skill_field() -> None:
    """Every entry in the array must contain a `skill` field of string type."""
    payload = _load_fixture()
    for index, entry in enumerate(payload):
        assert isinstance(entry, dict), f"entry[{index}] must be an object"
        assert "skill" in entry, f"entry[{index}] missing required field 'skill'"
        assert isinstance(entry["skill"], str), (
            f"entry[{index}].skill must be string, got {type(entry['skill']).__name__}"
        )
        assert entry["skill"], f"entry[{index}].skill must be non-empty"


def test_each_entry_has_result_with_score_and_reason() -> None:
    """Every entry must contain a `result` object with `score` and `reason` fields.

    The `result` object holds the eval rubric output. `score` is numeric
    (int/float). `reason` is a string describing the score (rubric breakdown
    OR ``eval-failed-cli-missing`` when the underlying eval CLI is unavailable).
    """
    payload = _load_fixture()
    for index, entry in enumerate(payload):
        assert "result" in entry, f"entry[{index}] missing required field 'result'"
        result = entry["result"]
        assert isinstance(result, dict), (
            f"entry[{index}].result must be object, got {type(result).__name__}"
        )
        assert "score" in result, f"entry[{index}].result missing required field 'score'"
        assert "reason" in result, f"entry[{index}].result missing required field 'reason'"
        assert isinstance(result["score"], (int, float)), (
            f"entry[{index}].result.score must be numeric, got {type(result['score']).__name__}"
        )
        assert isinstance(result["reason"], str), (
            f"entry[{index}].result.reason must be string, got {type(result['reason']).__name__}"
        )
        assert result["reason"], f"entry[{index}].result.reason must be non-empty"


def test_score_is_numeric_in_zero_to_hundred_range() -> None:
    """Scores must be numeric and within the 0..100 range used by the rubric."""
    payload = _load_fixture()
    for index, entry in enumerate(payload):
        score = entry["result"]["score"]
        assert 0 <= score <= 100, (
            f"entry[{index}].result.score={score} outside [0, 100] rubric range"
        )
