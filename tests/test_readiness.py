"""The eight production-ready boxes, ticked only by receipts that were executed.

The spec's rule is that nothing gets a URL until every box is ticked by observed
evidence. This suite holds the reader to it from both sides: eight fresh executed
receipts read PASS, and every way a box can fail to be proven reads something other
than PASS — missing, stale, mismatched, undeclared, or belonging to another box.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from ai_engineering import evidence, readiness

ROOT = Path(__file__).parents[1]
SPEC = ROOT / "specs" / "010-governed-agentic-engineering-foundation" / "spec.md"
NOW = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)


def _adversarial():
    """The runner as the suite runs it — by path, because it is a script and not a
    package, and importing it any other way would test a copy."""

    loaded = importlib.util.spec_from_file_location(
        "adversarial_run", ROOT / "tests" / "adversarial" / "run.py"
    )
    module = importlib.util.module_from_spec(loaded)
    loaded.loader.exec_module(module)
    return module


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
    now: datetime = NOW,
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
        fresh = finished.get(box.id, now - timedelta(hours=1))
        receipt = written.get(box.id, _receipt(box, declared, finished=fresh))
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


def _receipts(root: Path) -> dict[str, dict[str, Any]]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / readiness.RECEIPTS).glob("*.json"))
    }


def _canonical(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + sha256(canonical.encode()).hexdigest()


def test_adversarial_runner_records_denials_and_clean_control(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(tmp_path / "home"))
    adversarial = _adversarial()
    caught, version = adversarial.probe(["git", "--version"])
    assert caught and version.startswith("git version ")
    absent, nothing = adversarial.probe([str(tmp_path / "no-such-tool"), "--version"])
    assert (absent, nothing) == (False, "")

    def outcomes(attack: bool, control: bool) -> dict[str, tuple[str, Any]]:
        return {
            "injection · file": ("injection_guard", lambda tmp: attack),
            "negative control": ("none", lambda tmp: control),
        }

    def run(root: Path, attack: bool, control: bool) -> tuple[int, dict[str, dict[str, Any]]]:
        monkeypatch.setattr(adversarial, "CASES", outcomes(attack, control))
        return adversarial.main(root=root), _receipts(root)

    exit_code, written = run(tmp_path / "green", True, True)
    assert exit_code == 0
    assert set(written) == {
        "adversarial-attacks",
        "adversarial-control",
        "local-command-git",
        "local-command-python",
    }
    assert written["local-command-git"]["tool_version"] == version
    assert {receipt["outcome"] for receipt in written.values()} == {"PASS"}

    inputs = adversarial.inputs_digest()
    for name, record in written.items():
        expected = evidence.Expectation(
            kind="automated",
            id=name,
            applicability="applicable",
            command=record["command"],
            tool_version=record["tool_version"],
            input_digest=inputs,
            artifact_digest=record["artifact_digest"],
            max_age_seconds=adversarial.RECEIPT_MAX_AGE,
        )
        verified = evidence.verify(record, expected=expected, now=datetime.now(UTC))
        assert verified.code == evidence.VERIFIED, (name, verified.code)

    assert written["adversarial-attacks"]["artifact_digest"] == _canonical(
        {"cases": {"injection · file": True}, "guards": {"injection_guard": True}}
    )
    assert written["adversarial-control"]["artifact_digest"] == _canonical(
        {"cases": {"negative control": True}}
    )

    missed_code, missed = run(tmp_path / "missed", False, True)
    assert missed_code == 1
    assert missed["adversarial-attacks"]["outcome"] == "FAIL"
    assert missed["adversarial-control"]["outcome"] == "PASS"

    fired_code, fired = run(tmp_path / "fired", True, False)
    assert fired_code == 1
    assert fired["adversarial-control"]["outcome"] == "FAIL"
    assert fired["adversarial-attacks"]["outcome"] == "PASS"

    serialized = json.dumps([_receipts(tmp_path / name) for name in ("green", "missed", "fired")])
    assert str(Path.home()) not in serialized
    assert str(tmp_path) not in serialized


def test_doctor_json_includes_readiness_receipt_status_and_age(tmp_path, monkeypatch):
    from ai_engineering import doctor, paths

    proven = _repository(tmp_path / "proven")
    facts = {fact.id: fact for fact in doctor.readiness_facts(proven, now=NOW)}
    assert set(facts) == {"readiness", *(f"readiness-{box.id}" for box in readiness.BOXES)}
    assert facts["readiness"].status == "PASS"
    assert facts["readiness"].detail == evidence.VERIFIED
    for box in readiness.BOXES:
        entry = facts[f"readiness-{box.id}"]
        assert entry.status == "PASS"
        assert entry.summary == box.label
        assert entry.detail == f"{evidence.VERIFIED} · 3600s old"

    unreceipted = _repository(tmp_path / "missing", written={"security": None})
    absent = {fact.id: fact for fact in doctor.readiness_facts(unreceipted, now=NOW)}
    assert absent["readiness"].status == "INCOMPLETE"
    assert absent["readiness-security"].status == "INCOMPLETE"
    assert absent["readiness-security"].detail == f"{evidence.MISSING} · no receipt to age"
    assert absent["readiness-logs"].status == "PASS"

    undeclared = {fact.id: fact for fact in doctor.readiness_facts(tmp_path / "empty", now=NOW)}
    assert set(undeclared) == {"readiness"}
    assert undeclared["readiness"].status == "INCOMPLETE"
    assert undeclared["readiness"].detail == readiness.DECLARATION_MISSING

    # Nothing here has a URL, so nothing here may report a ticked box.
    assert doctor.readiness_facts(ROOT, now=datetime.now(UTC))[0].status != "PASS"

    live = _repository(tmp_path / "live", now=datetime.now(UTC))
    monkeypatch.setattr(paths, "repo_root", lambda start=None: live)
    monkeypatch.setattr(doctor, "CHECKS", set())
    monkeypatch.setattr(doctor, "coverage", lambda root: [])
    reported = doctor.main([])
    # `checks` is the list cli.main serializes into the JSON envelope, one fact per entry.
    published = {fact.id: fact.as_dict() for fact in reported.checks}
    assert published["readiness"]["status"] == "PASS"
    assert published["readiness-external_check"]["summary"] == "External check"
    # Reported, not gated: giving something a URL is not this verb's decision to make.
    assert reported.result.outcome == "PASS"


def test_receipts_without_a_committed_declaration_are_a_repository_finding(tmp_path, monkeypatch):
    """The receipts are this machine's and are ignored. The requirement they are measured
    against is reviewed, so a repository holding one and not the other is a repository
    where the same hand wrote the question and the answer."""

    from ai_engineering import doctor

    root = tmp_path / "repository"
    (root / readiness.RECEIPTS).mkdir(parents=True)
    committed = [".ai/.gitignore", ".ai/intent.md"]
    monkeypatch.setattr(doctor, "tracked_files", lambda where: committed)
    assert f"{readiness.DECLARATION} is not committed" in (doctor.polarity(root) or "")

    committed.append(readiness.DECLARATION)
    assert doctor.polarity(root) is None
