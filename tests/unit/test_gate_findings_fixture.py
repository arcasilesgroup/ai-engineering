"""spec-104 T-0.7: canonical fixture round-trip."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.models import GateFindingsDocument

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "gate_findings_v1.json"


def test_canonical_fixture_round_trips_through_model() -> None:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    doc = GateFindingsDocument.model_validate(raw)
    serialized = doc.model_dump(by_alias=True, mode="json")
    # exclude_none was not used, so we tolerate optional null fields preserved
    assert serialized["schema"] == raw["schema"]
    assert serialized["session_id"] == raw["session_id"]
    assert serialized["produced_by"] == raw["produced_by"]
    assert len(serialized["findings"]) == len(raw["findings"])
    assert serialized["wall_clock_ms"] == raw["wall_clock_ms"]


def test_canonical_fixture_severity_coverage() -> None:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    severities = {f["severity"] for f in raw["findings"]}
    assert severities >= {"critical", "high", "medium", "low"}
