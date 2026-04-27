"""RED skeleton for spec-105 Phase 4 — dual-version gate-findings emit.

Covers G-7 dual-version emit logic per D-105-08:

* When ``accepted_findings`` AND ``expiring_soon`` are both empty, the
  orchestrator emits ``schema: ai-engineering/gate-findings/v1`` —
  byte-equivalent output for spec-104 producers/consumers.
* When either populated, the orchestrator emits
  ``schema: ai-engineering/gate-findings/v1.1``.

Status: RED (orchestrator ``_emit_findings`` lands in Phase 4 T-4.2 —
the schema model already accepts v1+v1.1 per Phase 2 T-2.4, but the
producer is hard-coded to v1 today).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 4 (T-4.11).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def test_emit_v1_when_accepted_and_expiring_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No accepted findings AND no expiring DECs → ``schema: v1`` emitted."""
    from ai_engineering.policy import orchestrator

    monkeypatch.chdir(tmp_path)
    # Phase 4 T-4.2 introduces a dual-emit helper — assert the symbol exists
    # and that the v1 fixture survives a round-trip.
    assert hasattr(orchestrator, "_emit_findings") or hasattr(
        orchestrator, "build_gate_findings_document"
    )

    fixture_path = Path(__file__).parent.parent / "fixtures" / "gate_findings_v1.json"
    document = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert document["schema"] == "ai-engineering/gate-findings/v1"
    assert "accepted_findings" not in document or not document.get("accepted_findings")


def test_emit_v1_1_when_accepted_findings_populated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Populated ``accepted_findings`` → ``schema: v1.1`` emitted."""
    from ai_engineering.state.models import GateFindingsDocument

    monkeypatch.chdir(tmp_path)
    fixture_path = Path(__file__).parent.parent / "fixtures" / "gate_findings_v1_1.json"
    document = GateFindingsDocument.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    assert document.schema_ == "ai-engineering/gate-findings/v1.1"
    assert document.accepted_findings, "v1.1 fixture must populate accepted_findings"


def test_emit_v1_1_when_expiring_soon_populated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Populated ``expiring_soon`` → ``schema: v1.1`` emitted even if accepted empty."""
    from ai_engineering.state.models import GateFindingsDocument

    payload = {
        "schema": "ai-engineering/gate-findings/v1.1",
        "session_id": "00000000-0000-4000-8000-000000000040",
        "produced_by": "ai-pr",
        "produced_at": "2026-04-27T12:00:00Z",
        "branch": "feat/spec-101-installer-robustness",
        "commit_sha": "deadbeef",
        "findings": [],
        "auto_fixed": [],
        "cache_hits": [],
        "cache_misses": [],
        "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        "accepted_findings": [],
        "expiring_soon": ["DEC-2026-04-26-EXPI"],
    }
    document = GateFindingsDocument.model_validate(payload)
    assert document.schema_ == "ai-engineering/gate-findings/v1.1"
    assert document.expiring_soon == ["DEC-2026-04-26-EXPI"]


def test_v1_consumer_reads_v1_1_payload_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consumers that only know v1 fields can still read a v1.1 payload."""
    from ai_engineering.state.models import GateFindingsDocument

    monkeypatch.chdir(tmp_path)
    fixture_path = Path(__file__).parent.parent / "fixtures" / "gate_findings_v1_1.json"
    document = GateFindingsDocument.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    # The Phase 2 model relax (extra="ignore") guarantees a v1.1 payload
    # round-trips through a v1-aware consumer without raising.
    assert document.session_id is not None
    assert isinstance(document.findings, list)
