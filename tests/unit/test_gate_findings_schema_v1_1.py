"""RED skeleton for spec-105 Phase 2 — gate-findings schema v1.1.

Covers spec-105 schema relax to accept Literal Union of v1+v1.1 plus the new
`AcceptedFinding` model and `expiring_soon` list on `GateFindingsDocument`.

Status: RED — current model rejects v1.1 schema literal and lacks new fields.
Marker: `@pytest.mark.spec_105_red` — excluded by default CI run.
Will be unmarked in Phase 2 (T-2.11) once schema relaxation lands.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.spec_105_red

# Imports are deferred inside each test so collection succeeds even though
# `AcceptedFinding` and `expiring_soon`/`accepted_findings` fields do not exist
# yet. Tests fail at execution time (when the marker is enabled), not at
# collection time. This keeps `pytest -m 'not spec_105_red'` clean for CI.


def test_v1_1_schema_literal_accepted() -> None:
    """`schema: ai-engineering/gate-findings/v1.1` parses successfully."""
    from ai_engineering.state.models import GateFindingsDocument

    payload = {
        "schema": "ai-engineering/gate-findings/v1.1",
        "session_id": "00000000-0000-4000-8000-000000000001",
        "produced_by": "ai-pr",
        "produced_at": "2026-04-27T12:00:00Z",
        "branch": "feat/x",
        "commit_sha": "abcdef0",
        "findings": [],
        "auto_fixed": [],
        "cache_hits": [],
        "cache_misses": [],
        "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        "accepted_findings": [],
        "expiring_soon": [],
    }
    doc = GateFindingsDocument.model_validate(payload)
    assert doc.schema_ == "ai-engineering/gate-findings/v1.1"


def test_v1_schema_literal_still_accepted_for_backward_compat() -> None:
    """`schema: v1` (legacy) still parses — Literal Union, not breaking change."""
    from ai_engineering.state.models import GateFindingsDocument

    payload = {
        "schema": "ai-engineering/gate-findings/v1",
        "session_id": "00000000-0000-4000-8000-000000000002",
        "produced_by": "ai-pr",
        "produced_at": "2026-04-27T12:00:00Z",
        "branch": "feat/x",
        "commit_sha": "abcdef0",
        "findings": [],
        "auto_fixed": [],
        "cache_hits": [],
        "cache_misses": [],
        "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
    }
    doc = GateFindingsDocument.model_validate(payload)
    assert doc.schema_ == "ai-engineering/gate-findings/v1"


def test_accepted_finding_round_trips() -> None:
    """`AcceptedFinding` is frozen, round-trips via dump/validate."""
    from pydantic import ValidationError

    from ai_engineering.state.models import AcceptedFinding

    af = AcceptedFinding(
        check="ruff",
        rule_id="E501",
        file="src/long.py",
        line=120,
        severity="low",
        message="line too long",
        dec_id="DEC-2026-100",
        expires_at="2026-07-27T12:00:00Z",
    )
    dumped = af.model_dump()
    redec = AcceptedFinding.model_validate(dumped)
    assert redec.dec_id == "DEC-2026-100"
    assert redec.rule_id == "E501"

    # frozen=True → assignment must raise pydantic ValidationError.
    with pytest.raises(ValidationError):
        af.dec_id = "DEC-2026-101"  # type: ignore[misc]


def test_expiring_soon_field_defaults_to_empty_list() -> None:
    """`expiring_soon` defaults to empty list when not provided."""
    from ai_engineering.state.models import GateFindingsDocument

    payload = {
        "schema": "ai-engineering/gate-findings/v1.1",
        "session_id": "00000000-0000-4000-8000-000000000003",
        "produced_by": "ai-pr",
        "produced_at": "2026-04-27T12:00:00Z",
        "branch": "feat/x",
        "commit_sha": "abcdef0",
        "findings": [],
        "auto_fixed": [],
        "cache_hits": [],
        "cache_misses": [],
        "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
    }
    doc = GateFindingsDocument.model_validate(payload)
    assert doc.expiring_soon == []
    assert doc.accepted_findings == []
