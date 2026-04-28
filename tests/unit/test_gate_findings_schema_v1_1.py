"""Unit tests for spec-105 D-105-08 — gate-findings.json schema v1 + v1.1.

Validates:
* Literal Union (v1, v1.1) accept both schema strings.
* Round-trip of intact v1 fixture (legacy producers/consumers preserved).
* Round-trip of populated v1.1 fixture (new fields parse correctly).
* ``AcceptedFinding`` model is frozen and round-trips.
* v1 reader silently drops v1.1 fields when ``extra="ignore"`` is honoured
  (consolidates the planned ``test_v1_consumer_reads_v1_1.py`` per
  Phase 2 T-2.10 plan note).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


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


def test_v1_fixture_roundtrips() -> None:
    """Canonical v1 fixture (Phase 1 fixture) parses + dumps without loss."""
    from ai_engineering.state.models import GateFindingsDocument

    payload = json.loads((FIXTURES / "gate_findings_v1.json").read_text(encoding="utf-8"))
    doc = GateFindingsDocument.model_validate(payload)
    dumped = doc.model_dump(by_alias=True, mode="json")
    redoc = GateFindingsDocument.model_validate(dumped)
    assert redoc.schema_ == "ai-engineering/gate-findings/v1"
    assert len(redoc.findings) == len(doc.findings) == 4
    # spec-104 contract: v1 reader-then-writer never accidentally upgrades to v1.1
    # because the source has no v1.1 fields.
    assert redoc.accepted_findings == []
    assert redoc.expiring_soon == []


def test_v1_1_fixture_roundtrips_with_populated_arrays() -> None:
    """v1.1 fixture round-trips with `accepted_findings` + `expiring_soon`."""
    from ai_engineering.state.models import GateFindingsDocument

    payload = json.loads((FIXTURES / "gate_findings_v1_1.json").read_text(encoding="utf-8"))
    doc = GateFindingsDocument.model_validate(payload)
    assert doc.schema_ == "ai-engineering/gate-findings/v1.1"
    assert len(doc.accepted_findings) == 3
    assert doc.expiring_soon == ["DEC-2026-04-27-A1B2"]
    # Verify field-level fidelity on the first accepted entry.
    first = doc.accepted_findings[0]
    assert first.dec_id == "DEC-2026-04-27-A1B2"
    assert first.rule_id == "aws-access-token"
    assert first.severity == "critical"

    # Round-trip dumps preserve the new arrays.
    dumped = doc.model_dump(by_alias=True, mode="json")
    redoc = GateFindingsDocument.model_validate(dumped)
    assert len(redoc.accepted_findings) == 3
    assert redoc.expiring_soon == ["DEC-2026-04-27-A1B2"]


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


def test_accepted_finding_expires_at_optional() -> None:
    """`expires_at` is optional (None means no expiry)."""
    from ai_engineering.state.models import AcceptedFinding

    af = AcceptedFinding(
        check="gitleaks",
        rule_id="custom-rule",
        file="src/x.py",
        line=1,
        severity="high",
        message="custom",
        dec_id="DEC-PERMANENT",
    )
    assert af.expires_at is None


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


def test_v1_consumer_silently_drops_unknown_fields_from_v1_1() -> None:
    """A v1 consumer reading a v1.1 doc must succeed thanks to `extra=\"ignore\"`.

    Simulates the spec-104 reader that does not yet know about
    ``accepted_findings`` / ``expiring_soon``: those fields are silently
    dropped and the rest of the document parses normally. This is the R-2
    backward-compat guarantee.
    """
    from ai_engineering.state.models import GateFindingsDocument

    # Take v1.1 fixture but synthesise a "v1 reader expecting v1 schema":
    # the schema literal is a Union, so even when the doc is labelled v1.1
    # the consumer can read everything, and downstream code can branch on
    # the schema literal explicitly. We additionally inject an unknown
    # field to validate ``extra="ignore"`` semantics.
    payload = json.loads((FIXTURES / "gate_findings_v1_1.json").read_text(encoding="utf-8"))
    payload["future_unknown_field"] = {"foo": "bar"}
    doc = GateFindingsDocument.model_validate(payload)
    assert doc.schema_ == "ai-engineering/gate-findings/v1.1"
    assert not hasattr(doc, "future_unknown_field")
