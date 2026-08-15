"""The eight production-ready boxes, ticked only by receipts that were executed.

The spec's rule is that nothing gets a URL until every box is ticked by observed
evidence. This suite holds the reader to it from both sides: eight fresh executed
receipts read PASS, and every way a box can fail to be proven reads something other
than PASS — missing, stale, mismatched, undeclared, or belonging to another box.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from ai_engineering import evidence, readiness

ROOT = Path(__file__).parents[1]
SPEC = ROOT / "specs" / "010-governed-agentic-engineering-foundation" / "spec.md"
NOW = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)


def _digest(text: str) -> str:
    return "sha256:" + sha256(text.encode()).hexdigest()


def _declared(box: readiness.Box) -> dict[str, Any]:
    """What a repository must state about a box before any receipt can tick it."""

    declared: dict[str, Any] = {
        "applicability": "applicable",
        "command": f"just {box.id}",
        "tool_version": "1.2.3",
        "input_digest": _digest(f"input {box.id}"),
        "artifact_digest": _digest(f"artifact {box.id}"),
        "max_age_seconds": 86_400,
    }
    if box.kind == "external":
        declared.update(
            {
                "test_id": "external-check-1",
                "owner_role": "release-manager",
                "protocol_id": "uptime-probe",
                "protocol_version": "2",
                "environment_id": "production",
                "environment_version": "2026-03",
                "receipt_digest": _digest("external receipt"),
                "independent_path": "status-page",
                "limits": "checks the public endpoint only, every 60 seconds",
            }
        )
    return declared


def _receipt(box: readiness.Box, declared: dict[str, Any], *, finished: datetime) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": "urn:ai-engineering:check-evidence:1",
        "schema_version": "1",
        "kind": box.kind,
        "id": box.id,
        "started_at": (finished - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "outcome": "PASS",
    }
    record.update(declared)
    if box.kind in {"human", "external"}:
        record["observation_date"] = finished.astimezone(UTC).date().isoformat()
    return record


def _repository(
    tmp_path: Path,
    *,
    declarations: dict[str, dict[str, Any]] | None = None,
    finished: dict[str, datetime] | None = None,
    written: dict[str, dict[str, Any]] | None = None,
    omitted: frozenset[str] = frozenset(),
) -> Path:
    """A repository whose eight boxes are declared and receipted, minus what a control
    deliberately removes or replaces."""

    root = tmp_path / "repository"
    receipts = root / readiness.RECEIPTS
    receipts.mkdir(parents=True)
    declarations = declarations or {}
    finished = finished or {}
    written = written or {}
    boxes = {}
    for box in readiness.BOXES:
        if box.id in omitted:
            continue
        declared = declarations.get(box.id, _declared(box))
        boxes[box.id] = declared
        receipt = written.get(
            box.id, _receipt(box, declared, finished=finished.get(box.id, NOW - timedelta(hours=1)))
        )
        if receipt is not None:
            (receipts / f"{box.id}.json").write_text(json.dumps(receipt), encoding="utf-8")
    (root / readiness.DECLARATION).write_text(
        json.dumps(
            {"schema": readiness.SCHEMA, "schema_version": readiness.VERSION, "boxes": boxes}
        ),
        encoding="utf-8",
    )
    return root


def _codes(report: readiness.Readiness) -> dict[str, str]:
    return {box.id: box.code for box in report.boxes}


def test_readiness_requires_eight_executable_fresh_receipts_and_negative_controls(tmp_path):
    labels = [
        line.split(" — ", 1)[0].removeprefix("- [ ] ").strip()
        for line in SPEC.read_text(encoding="utf-8").splitlines()
        if line.startswith("- [ ] ") and " — " in line
    ]
    production_ready = labels[-8:]
    assert [box.label for box in readiness.BOXES] == production_ready
    assert len(readiness.BOXES) == 8
    assert len({box.id for box in readiness.BOXES}) == 8

    proven = readiness.read(_repository(tmp_path / "proven"), now=NOW)
    assert proven.result.outcome == "PASS"
    assert set(_codes(proven).values()) == {evidence.VERIFIED}
    assert all(box.age_seconds == 3_600 for box in proven.boxes)

    unreceipted = _repository(tmp_path / "missing", written={"security": None})
    missing = readiness.read(unreceipted, now=NOW)
    assert missing.result.outcome == "INCOMPLETE"
    assert _codes(missing)["security"] == evidence.MISSING
    assert missing.age_of("security") is None

    stale = readiness.read(
        _repository(tmp_path / "stale", finished={"logs": NOW - timedelta(days=3)}), now=NOW
    )
    assert stale.result.outcome == "INCOMPLETE"
    assert _codes(stale)["logs"] == evidence.STALE

    box = next(entry for entry in readiness.BOXES if entry.id == "ci_cd")
    failed = _receipt(box, _declared(box), finished=NOW - timedelta(hours=1)) | {"outcome": "FAIL"}
    executed = readiness.read(_repository(tmp_path / "failed", written={"ci_cd": failed}), now=NOW)
    assert executed.result.outcome == "FAIL"
    assert _codes(executed)["ci_cd"] == evidence.EXECUTED_FAIL

    borrowed = _receipt(box, _declared(box), finished=NOW - timedelta(hours=1)) | {"id": "logs"}
    lent = readiness.read(_repository(tmp_path / "borrowed", written={"ci_cd": borrowed}), now=NOW)
    assert lent.result.outcome == "INCOMPLETE"
    assert _codes(lent)["ci_cd"] == evidence.REQUIREMENT_MISMATCH

    tampered = _receipt(box, _declared(box) | {"artifact_digest": _digest("other")}, finished=NOW)
    swap = _repository(tmp_path / "swapped", written={"ci_cd": tampered})
    swapped = readiness.read(swap, now=NOW)
    assert swapped.result.outcome == "INCOMPLETE"
    assert _codes(swapped)["ci_cd"] == evidence.DIGEST_MISMATCH

    undeclared = readiness.read(
        _repository(tmp_path / "undeclared", omitted=frozenset({"traces"})), now=NOW
    )
    assert undeclared.result.outcome == "INCOMPLETE"
    assert undeclared.code == readiness.BOXES_MISMATCH
    assert undeclared.boxes == ()

    extra = _repository(tmp_path / "extra")
    declaration = json.loads((extra / readiness.DECLARATION).read_text(encoding="utf-8"))
    declaration["boxes"]["marketing"] = _declared(box)
    (extra / readiness.DECLARATION).write_text(json.dumps(declaration), encoding="utf-8")
    invented = readiness.read(extra, now=NOW)
    assert invented.result.outcome == "INCOMPLETE"
    assert invented.code == readiness.BOXES_MISMATCH

    absent = readiness.read(tmp_path / "nothing", now=NOW)
    assert absent.result.outcome == "INCOMPLETE"
    assert absent.code == readiness.DECLARATION_MISSING
    assert absent.boxes == ()

    unreadable = tmp_path / "unreadable"
    (unreadable / readiness.RECEIPTS).mkdir(parents=True)
    (unreadable / readiness.DECLARATION).write_text("{not json", encoding="utf-8")
    assert readiness.read(unreadable, now=NOW).code == readiness.DECLARATION_MALFORMED

    hopless = _declared(box) | {"applicability": "not_applicable", "reason": "one hop, no trace"}
    traces = next(entry for entry in readiness.BOXES if entry.id == "traces")
    unhopped = _repository(
        tmp_path / "unhopped",
        declarations={"traces": hopless},
        written={"traces": _receipt(traces, hopless, finished=NOW - timedelta(hours=1))},
    )
    excused = readiness.read(unhopped, now=NOW)
    assert excused.result.outcome == "PASS"
    assert _codes(excused)["traces"] == evidence.NOT_APPLICABLE

    here = readiness.read(ROOT, now=datetime.now(UTC))
    assert here.result.outcome != "PASS"
