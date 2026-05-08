"""RED lifecycle invariants for spec-116 decision-store normalization.

Spec-125 D-125-09 deleted the canonical ``decision-store.json`` file and
moved the projection into the state.db ``decisions`` table; the JSON
shape these RED tests pin no longer exists on disk. The whole module
is skipped when the artifact is missing so the lifecycle invariants
remain auditable in branches that still carry the legacy file but
don't break CI on the modern surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.state.control_plane import resolve_state_plane_artifact_path

REPO_ROOT = Path(__file__).resolve().parents[2]
DECISION_STORE_PATH = REPO_ROOT / ".ai-engineering" / "state" / "decision-store.json"

if not DECISION_STORE_PATH.exists():
    pytest.skip(
        "decision-store.json removed in spec-125 D-125-09; lifecycle "
        "invariants migrated to state.db.decisions queries.",
        allow_module_level=True,
    )
LEGACY_AUDIT_FINDINGS_PATH = (
    REPO_ROOT / ".ai-engineering" / "state" / "spec-116-t41-audit-findings.json"
)
AUDIT_FINDINGS_PATH = resolve_state_plane_artifact_path(
    REPO_ROOT,
    ".ai-engineering/state/spec-116-t41-audit-findings.json",
)

RETIRED_BUCKETS = frozenset({"superseded history", "completed cleanup", "archive candidate"})
LIVE_RISK_BUCKET = "live risk"
FORBIDDEN_CANONICAL_REFERENCES = (
    "/ai-execute",
    "GOVERNANCE_SOURCE.md",
    "project-identity",
    "checkpoint.execute",
    "checkpoint.release",
)
PLACEHOLDER_LINEAGE_VALUES = frozenset({"", "RECONSTRUCTED"})


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decision_entries(store_payload: dict[str, object]) -> list[dict[str, object]]:
    raw_entries = store_payload["decisions"]
    assert isinstance(raw_entries, list)
    return [entry for entry in raw_entries if isinstance(entry, dict)]


def _normalized_active_slice(store_payload: dict[str, object]) -> list[dict[str, object]]:
    active_decisions = store_payload.get("active_decisions")
    if isinstance(active_decisions, list):
        return [entry for entry in active_decisions if isinstance(entry, dict)]

    active_section = store_payload.get("active")
    if isinstance(active_section, dict):
        nested_decisions = active_section.get("decisions")
        if isinstance(nested_decisions, list):
            return [entry for entry in nested_decisions if isinstance(entry, dict)]

    return _decision_entries(store_payload)


def _expand_audit_ids(audit_entry: dict[str, object]) -> list[str]:
    member_ids = audit_entry.get("member_ids")
    if isinstance(member_ids, list):
        return [entry_id for entry_id in member_ids if isinstance(entry_id, str)]

    return [part.strip() for part in str(audit_entry["id"]).split(",") if part.strip()]


def _audit_bucket_by_id(audit_payload: dict[str, object]) -> dict[str, str]:
    buckets: dict[str, str] = {}
    for audit_entry in audit_payload["entries"]:
        assert isinstance(audit_entry, dict)
        bucket = audit_entry["classification_bucket"]
        assert isinstance(bucket, str)
        for decision_id in _expand_audit_ids(audit_entry):
            buckets[decision_id] = bucket
    return buckets


def test_spec_116_audit_findings_relocation_keeps_legacy_shim_readable() -> None:
    assert AUDIT_FINDINGS_PATH.exists() is True
    assert LEGACY_AUDIT_FINDINGS_PATH.exists() is True
    assert AUDIT_FINDINGS_PATH != LEGACY_AUDIT_FINDINGS_PATH
    assert _load_json(AUDIT_FINDINGS_PATH) == _load_json(LEGACY_AUDIT_FINDINGS_PATH)


def test_normalized_active_slice_excludes_retired_lifecycle_entries() -> None:
    store_payload = _load_json(DECISION_STORE_PATH)
    audit_payload = _load_json(AUDIT_FINDINGS_PATH)

    active_ids = {entry["id"] for entry in _normalized_active_slice(store_payload)}
    retired_ids = {
        decision_id
        for audit_entry in audit_payload["entries"]
        if audit_entry["classification_bucket"] in RETIRED_BUCKETS
        for decision_id in _expand_audit_ids(audit_entry)
    }

    assert active_ids.isdisjoint(retired_ids), (
        "Normalized active decision slice still contains retired lifecycle entries: "
        f"{sorted(active_ids & retired_ids)}"
    )


def test_superseded_entries_have_existing_successor_links() -> None:
    store_payload = _load_json(DECISION_STORE_PATH)
    decisions = _decision_entries(store_payload)

    existing_ids = {entry["id"] for entry in decisions}
    broken_links: list[tuple[str, object]] = []
    for entry in decisions:
        if entry["status"] != "superseded":
            continue
        successor = entry.get("superseded_by")
        if not isinstance(successor, str) or successor not in existing_ids:
            broken_links.append((str(entry["id"]), successor))

    assert not broken_links, (
        "Superseded lifecycle records require valid superseded_by links to "
        f"existing DEC entries: {broken_links}"
    )


def test_active_formal_decision_records_do_not_reference_removed_surfaces() -> None:
    store_payload = _load_json(DECISION_STORE_PATH)
    audit_payload = _load_json(AUDIT_FINDINGS_PATH)

    audit_buckets = _audit_bucket_by_id(audit_payload)
    offending_records: dict[str, list[str]] = {}

    for entry in _normalized_active_slice(store_payload):
        entry_id = str(entry["id"])
        if audit_buckets.get(entry_id) == LIVE_RISK_BUCKET:
            continue

        serialized_entry = json.dumps(entry, sort_keys=True)
        forbidden_hits = [
            token for token in FORBIDDEN_CANONICAL_REFERENCES if token in serialized_entry
        ]
        if forbidden_hits:
            offending_records[entry_id] = forbidden_hits

    assert not offending_records, (
        "Active formal-decision records still reference removed commands or "
        f"nonexistent canonical surfaces: {offending_records}"
    )


def test_normalized_active_slice_preserves_non_placeholder_lineage() -> None:
    store_payload = _load_json(DECISION_STORE_PATH)

    invalid_entries: dict[str, list[str]] = {}
    for entry in _normalized_active_slice(store_payload):
        problems: list[str] = []

        source = entry.get("source")
        if not isinstance(source, str) or source.strip() in PLACEHOLDER_LINEAGE_VALUES:
            problems.append(f"source={source!r}")

        spec = entry.get("spec")
        if not isinstance(spec, str) or spec.strip() in PLACEHOLDER_LINEAGE_VALUES:
            problems.append(f"spec={spec!r}")

        if problems:
            invalid_entries[str(entry["id"])] = problems

    assert not invalid_entries, (
        "Normalized active decision slice must preserve non-placeholder "
        "source/spec lineage from the canonical decisions ledger: "
        f"{invalid_entries}"
    )
