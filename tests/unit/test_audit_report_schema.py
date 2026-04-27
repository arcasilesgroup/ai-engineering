"""Phase 4 RED: audit-report.json schema contract (spec-106 G-4).

Asserts the JSON shape emitted by ``scripts/skill-audit.sh``: a JSON array
where each entry is an object containing a ``skill`` field (string) and a
``result`` field (object with ``score`` and ``reason`` fields). The schema
is the contract downstream consumers (CI dashboards, hard-gate enforcement
in future specs) rely on.

Marked ``spec_106_red``: excluded from the default CI run until Phase 4
delivers the GREEN script implementation and the audit-report fixture or
runtime-emitted file the test can validate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_REPORT = REPO_ROOT / "audit-report.json"


@pytest.mark.spec_106_red
def test_audit_report_is_json_array() -> None:
    """The report must be a JSON document whose root is a list."""
    # Deferred import per spec-106 RED contract.
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.4: audit-report.json must be a JSON array "
        "(top-level value is a list, not an object)."
    )


@pytest.mark.spec_106_red
def test_each_entry_has_skill_field() -> None:
    """Every entry in the array must contain a `skill` field of string type."""
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.4: each audit-report.json entry must include "
        "a `skill` field (string identifier matching the skill directory name)."
    )


@pytest.mark.spec_106_red
def test_each_entry_has_result_with_score_and_reason() -> None:
    """Every entry must contain a `result` object with `score` and `reason` fields.

    The `result` object holds the eval rubric output. `score` is numeric
    (int/float). `reason` is a string describing the score (rubric breakdown
    OR ``eval-failed`` when the underlying eval CLI is unavailable).
    """
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.4: each audit-report.json entry must include "
        "a `result` object with `score` (number) and `reason` (string) fields."
    )


@pytest.mark.spec_106_red
def test_score_is_numeric_in_zero_to_hundred_range() -> None:
    """Scores must be numeric and within the 0..100 range used by the rubric."""
    raise NotImplementedError(
        "spec-106 Phase 4 T-4.4: each entry's result.score must be numeric "
        "and within [0, 100] (skill-creator rubric range)."
    )
