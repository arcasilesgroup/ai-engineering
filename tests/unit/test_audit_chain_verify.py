"""GREEN tests for spec-107 G-12 (Phase 6) -- H2 hash-chained audit trail.

Spec-107 D-107-10 introduces a tamper-evident audit chain layered over
``framework-events.ndjson`` and ``decision-store.json``. Each entry adds
an optional ``prev_event_hash`` field carrying the SHA256 of the prior
entry's canonical-JSON payload (excluding the field itself). The
``state/audit_chain.py`` module ships ``verify_audit_chain(file_path,
mode)`` returning an :class:`AuditChainVerdict` dataclass with ``ok``,
``entries_checked``, ``first_break_index`` and ``first_break_reason``.

Decision protocol:

* Empty file -> verdict ok=True (vacuously valid).
* Single entry -> verdict ok=True (no chain to verify yet).
* Linear chain with each ``prev_event_hash`` matching SHA256 of prior
  payload -> verdict ok=True.
* Mid-chain mutation, truncation, or append-injection -> verdict
  ok=False with the first break index + a human-readable reason.
* Legacy entries lacking ``prev_event_hash`` -> verdict ok=True.

These tests are the GREEN acceptance contract for T-6.1 / T-6.4 / T-6.8.
The RED markers from Phase 5 have been removed -- the suite is part of
the default CI run.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Module shape contract (T-6.1 surface)
# ---------------------------------------------------------------------------


def test_audit_chain_module_exists() -> None:
    """G-12: state/audit_chain.py module ships with verify_audit_chain()."""
    module_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "audit_chain.py"
    assert module_path.is_file(), (
        f"state/audit_chain.py missing -- Phase 6 T-6.1 must create the module "
        f"with verify_audit_chain(file_path) -> AuditChainVerdict at {module_path}"
    )


def test_audit_chain_verdict_dataclass_exists() -> None:
    """G-12: AuditChainVerdict dataclass returned by verify_audit_chain()."""
    from ai_engineering.state.audit_chain import AuditChainVerdict

    verdict = AuditChainVerdict(
        ok=True,
        entries_checked=0,
        first_break_index=None,
        first_break_reason=None,
    )
    assert verdict.ok is True
    assert verdict.entries_checked == 0
    assert verdict.first_break_index is None
    assert verdict.first_break_reason is None


def test_verify_audit_chain_function_exists() -> None:
    """G-12: verify_audit_chain(file_path) walker function exists."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    assert callable(verify_audit_chain)


def test_compute_entry_hash_function_exists() -> None:
    """G-12: compute_entry_hash() helper for canonical-JSON SHA256 of an entry."""
    from ai_engineering.state.audit_chain import compute_entry_hash

    assert callable(compute_entry_hash)


def test_decision_model_carries_prev_event_hash_field() -> None:
    """G-12: Decision model has additive `prev_event_hash` field (D-107-10)."""
    from ai_engineering.state.models import Decision

    fields = Decision.model_fields
    assert "prev_event_hash" in fields, (
        "Decision missing `prev_event_hash` field -- Phase 6 T-6.3 must add the "
        "additive backward-compat field"
    )
    # Default must be None to preserve backward-compat for legacy decisions.
    assert fields["prev_event_hash"].default is None


def test_observability_emits_prev_event_hash() -> None:
    """G-12: observability writes `prev_event_hash` into emitted events."""
    obs_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "observability.py"
    text = obs_path.read_text(encoding="utf-8")
    assert "prev_event_hash" in text, (
        "state/observability.py missing prev_event_hash wiring -- "
        "Phase 6 T-6.2 must populate prev_event_hash on every event emission"
    )


def test_doctor_audit_chain_advisory_checks_exist() -> None:
    """G-12: doctor advisory checks `audit-chain-events` + `audit-chain-decisions`."""
    doctor_dir = REPO_ROOT / "src" / "ai_engineering" / "doctor"
    found_events = False
    found_decisions = False
    for path in doctor_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "audit-chain-events" in text:
            found_events = True
        if "audit-chain-decisions" in text:
            found_decisions = True
    assert found_events and found_decisions, (
        "doctor missing `audit-chain-events`/`audit-chain-decisions` advisory "
        "checks -- Phase 6 T-6.5 must add WARN-only advisory checks"
    )


def test_audit_verify_cli_subcommand_registered() -> None:
    """G-12: `ai-eng audit verify` is registered in the cli factory."""
    from ai_engineering.cli_factory import create_app

    app = create_app()
    audit_groups = [
        g
        for g in app.registered_groups
        if g.typer_instance and g.typer_instance.info.name == "audit"
    ]
    assert audit_groups, "`audit` Typer sub-group not registered -- Phase 6 T-6.7"
    audit_app = audit_groups[0].typer_instance
    verify_commands = [cmd for cmd in audit_app.registered_commands if cmd.name == "verify"]
    assert verify_commands, (
        "`audit verify` subcommand not registered -- Phase 6 T-6.7 must register it"
    )


# ---------------------------------------------------------------------------
# Behavioral contract: chain validation across modes and tamper patterns.
# ---------------------------------------------------------------------------


def test_verify_audit_chain_returns_ok_for_empty_file(tmp_path: Path) -> None:
    """Empty audit file is vacuously valid (no entries -> OK verdict)."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    empty_path = tmp_path / "framework-events.ndjson"
    empty_path.write_text("", encoding="utf-8")
    verdict = verify_audit_chain(empty_path)
    assert verdict.ok is True
    assert verdict.entries_checked == 0
    assert verdict.first_break_index is None


def test_verify_audit_chain_returns_ok_for_single_entry(tmp_path: Path) -> None:
    """Single entry chain anchor (prev_event_hash=None) is valid."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    entry = {"id": "e1", "kind": "control_outcome", "prev_event_hash": None}
    chain_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is True
    assert verdict.entries_checked == 1


def test_verify_audit_chain_accepts_valid_three_entry_chain(tmp_path: Path) -> None:
    """Three-entry chain with correct prev_event_hash pointers is valid."""
    from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    entry1 = {"id": "e1", "kind": "control_outcome", "outcome": "pass"}
    entry1["prev_event_hash"] = None
    entry2 = {"id": "e2", "kind": "control_outcome", "outcome": "pass"}
    entry2["prev_event_hash"] = compute_entry_hash(entry1)
    entry3 = {"id": "e3", "kind": "control_outcome", "outcome": "pass"}
    entry3["prev_event_hash"] = compute_entry_hash(entry2)

    chain_path.write_text(
        "\n".join(json.dumps(e) for e in (entry1, entry2, entry3)) + "\n",
        encoding="utf-8",
    )
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is True
    assert verdict.entries_checked == 3


def test_verify_audit_chain_detects_mid_chain_tampering(tmp_path: Path) -> None:
    """Mid-chain mutation must be detected with first_break_index pointing to it."""
    from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    entry1 = {"id": "e1", "kind": "control_outcome", "outcome": "pass"}
    entry1["prev_event_hash"] = None
    entry2 = {"id": "e2", "kind": "control_outcome", "outcome": "pass"}
    entry2["prev_event_hash"] = compute_entry_hash(entry1)
    entry3 = {"id": "e3", "kind": "control_outcome", "outcome": "pass"}
    entry3["prev_event_hash"] = compute_entry_hash(entry2)
    # Tamper entry2 AFTER entry3 was hashed -> entry3 prev_hash now stale.
    entry2["outcome"] = "fail"

    chain_path.write_text(
        "\n".join(json.dumps(e) for e in (entry1, entry2, entry3)) + "\n",
        encoding="utf-8",
    )
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is False
    assert verdict.first_break_index == 2
    assert verdict.first_break_reason and "mismatch" in verdict.first_break_reason


def test_verify_audit_chain_detects_append_injection(tmp_path: Path) -> None:
    """An entry whose prev_event_hash points to a phantom prior is rejected."""
    from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    entry1 = {"id": "e1", "kind": "control_outcome", "prev_event_hash": None}
    # Forged entry whose pointer doesn't match entry1.
    entry2 = {"id": "INJECTED", "kind": "control_outcome"}
    entry2["prev_event_hash"] = compute_entry_hash({"id": "FAKE_PRIOR"})
    chain_path.write_text(
        "\n".join(json.dumps(e) for e in (entry1, entry2)) + "\n",
        encoding="utf-8",
    )
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is False
    assert verdict.first_break_index == 1


def test_verify_audit_chain_detects_head_truncation(tmp_path: Path) -> None:
    """First entry with non-null prev_event_hash signals a head truncation."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    entry1 = {"id": "e1", "kind": "control_outcome"}
    entry1["prev_event_hash"] = "deadbeef" * 8
    chain_path.write_text(json.dumps(entry1) + "\n", encoding="utf-8")
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is False
    assert verdict.first_break_index == 0
    assert verdict.first_break_reason and "head truncation" in verdict.first_break_reason


def test_verify_audit_chain_accepts_legacy_entries(tmp_path: Path) -> None:
    """Legacy entries lacking prev_event_hash must NOT mark the chain broken."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    legacy = {"id": "old1", "kind": "control_outcome"}
    chain_path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is True
    assert verdict.entries_checked == 1


def test_verify_audit_chain_legacy_entries_can_anchor_subsequent_chain(tmp_path: Path) -> None:
    """A legacy entry followed by spec-107 entry: chain re-anchors gracefully."""
    from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    legacy = {"id": "old1", "kind": "control_outcome"}
    spec107_entry = {"id": "new1", "kind": "control_outcome"}
    spec107_entry["prev_event_hash"] = compute_entry_hash(legacy)
    chain_path.write_text(
        "\n".join(json.dumps(e) for e in (legacy, spec107_entry)) + "\n",
        encoding="utf-8",
    )
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is True


def test_verify_audit_chain_detects_truncation(tmp_path: Path) -> None:
    """File truncation (entries dropped) must be detected when chain refers backward."""
    from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    entry1 = {"id": "e1", "kind": "control_outcome", "prev_event_hash": None}
    # Forge entry2 with prev_event_hash pointing to a non-existent entry.
    entry2 = {"id": "e2", "kind": "control_outcome"}
    entry2["prev_event_hash"] = compute_entry_hash({"id": "PHANTOM"})
    chain_path.write_text(
        "\n".join(json.dumps(e) for e in (entry1, entry2)) + "\n",
        encoding="utf-8",
    )
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is False


def test_verify_audit_chain_supports_json_array_mode(tmp_path: Path) -> None:
    """Decision-store-style payload (json_array mode) chains correctly."""
    from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

    decisions_path = tmp_path / "decision-store.json"
    decision1 = {"id": "DEC-001", "context": "c1", "prev_event_hash": None}
    decision2 = {"id": "DEC-002", "context": "c2"}
    decision2["prev_event_hash"] = compute_entry_hash(decision1)
    payload = {
        "schemaVersion": "1.1",
        "decisions": [decision1, decision2],
    }
    decisions_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    verdict = verify_audit_chain(decisions_path, mode="json_array")
    assert verdict.ok is True
    assert verdict.entries_checked == 2


def test_verify_audit_chain_json_array_detects_break(tmp_path: Path) -> None:
    """Decision-store break detected in json_array mode."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    decisions_path = tmp_path / "decision-store.json"
    decision1 = {"id": "DEC-001", "context": "c1", "prev_event_hash": None}
    # Bogus prev_event_hash pointing to a phantom decision.
    decision2 = {"id": "DEC-002", "context": "c2", "prev_event_hash": "00" * 32}
    payload = {
        "schemaVersion": "1.1",
        "decisions": [decision1, decision2],
    }
    decisions_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    verdict = verify_audit_chain(decisions_path, mode="json_array")
    assert verdict.ok is False
    assert verdict.first_break_index == 1


def test_compute_entry_hash_excludes_prev_event_hash_field(tmp_path: Path) -> None:
    """Hash computation excludes prev_event_hash field for round-trip stability."""
    from ai_engineering.state.audit_chain import compute_entry_hash

    base = {"id": "e1", "kind": "control_outcome", "outcome": "pass"}
    hash_no_field = compute_entry_hash(base)
    base_with_field = {**base, "prev_event_hash": None}
    hash_with_field_none = compute_entry_hash(base_with_field)
    base_with_other = {**base, "prev_event_hash": "abc123"}
    hash_with_field_value = compute_entry_hash(base_with_other)
    # All three must yield the same hash because the chain field is
    # stripped before hashing.
    assert hash_no_field == hash_with_field_none == hash_with_field_value


def test_compute_entry_hash_also_strips_camelcase_alias(tmp_path: Path) -> None:
    """Pydantic camelCase alias `prevEventHash` is also stripped."""
    from ai_engineering.state.audit_chain import compute_entry_hash

    base = {"id": "e1", "kind": "control_outcome"}
    hash_canonical = compute_entry_hash(base)
    aliased = {**base, "prevEventHash": "deadbeef"}
    hash_aliased = compute_entry_hash(aliased)
    assert hash_canonical == hash_aliased


def test_verify_audit_chain_handles_missing_file(tmp_path: Path) -> None:
    """Missing file is treated as vacuously valid (no entries)."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    missing = tmp_path / "no-such-file.ndjson"
    verdict = verify_audit_chain(missing)
    assert verdict.ok is True
    assert verdict.entries_checked == 0


def test_verify_audit_chain_handles_malformed_ndjson_line(tmp_path: Path) -> None:
    """Malformed JSON line is reported as an unparseable file with first_break_index=0."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    chain_path.write_text("not-valid-json\n", encoding="utf-8")
    verdict = verify_audit_chain(chain_path)
    assert verdict.ok is False
    assert verdict.first_break_reason and "malformed JSON" in verdict.first_break_reason
