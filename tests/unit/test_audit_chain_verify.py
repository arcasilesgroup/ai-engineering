"""RED skeleton for spec-107 G-12 (Phase 6) — H2 hash-chained audit trail verifier.

Spec-107 D-107-10 introduces a tamper-evident audit chain layered over
``framework-events.ndjson`` and ``decision-store.json``. Each entry adds an
optional ``prev_event_hash`` field carrying the SHA256 of the prior entry's
canonical-JSON payload (excluding the field itself). A new module
``state/audit_chain.py`` provides ``verify_audit_chain(file_path) -> AuditChainVerdict``
that walks the entries in order and flags the first break index.

Decision protocol:
- Empty file -> verdict OK (vacuously valid).
- Single entry -> verdict OK (no chain to verify yet).
- Linear chain with each ``prev_event_hash`` matching SHA256 of prior payload
  -> verdict OK.
- Mid-chain mutation, truncation, or append-injection -> verdict NOT_OK with
  the first break index + a human-readable reason.
- Legacy entries lacking ``prev_event_hash`` -> verdict OK with a "legacy"
  warning (additive backward-compat per D-107-10).

These tests are marked ``spec_107_red`` and excluded from the CI default run
until Phase 6 lands the GREEN implementation. They form the acceptance
contract for T-6.1 / T-6.4 / T-6.8.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.spec_107_red
def test_audit_chain_module_exists() -> None:
    """G-12: state/audit_chain.py module ships with verify_audit_chain()."""
    module_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "audit_chain.py"
    assert module_path.is_file(), (
        f"state/audit_chain.py missing — Phase 6 T-6.1 must create the module "
        f"with verify_audit_chain(file_path) -> AuditChainVerdict at {module_path}"
    )


@pytest.mark.spec_107_red
def test_audit_chain_verdict_dataclass_exists() -> None:
    """G-12: AuditChainVerdict dataclass returned by verify_audit_chain()."""
    module_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "audit_chain.py"
    if not module_path.is_file():
        pytest.skip("state/audit_chain.py missing — covered by sibling test")
    text = module_path.read_text(encoding="utf-8")
    assert "AuditChainVerdict" in text, (
        "state/audit_chain.py missing AuditChainVerdict dataclass — "
        "Phase 6 T-6.1 must declare the verdict shape"
    )


@pytest.mark.spec_107_red
def test_verify_audit_chain_function_exists() -> None:
    """G-12: verify_audit_chain(file_path) walker function exists."""
    module_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "audit_chain.py"
    if not module_path.is_file():
        pytest.skip("state/audit_chain.py missing — covered by sibling test")
    text = module_path.read_text(encoding="utf-8")
    assert "def verify_audit_chain(" in text, (
        "state/audit_chain.py missing verify_audit_chain() — "
        "Phase 6 T-6.1 must implement the walker"
    )


@pytest.mark.spec_107_red
def test_compute_entry_hash_function_exists() -> None:
    """G-12: compute_entry_hash() helper for canonical-JSON SHA256 of an entry."""
    module_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "audit_chain.py"
    if not module_path.is_file():
        pytest.skip("state/audit_chain.py missing — covered by sibling test")
    text = module_path.read_text(encoding="utf-8")
    assert "def compute_entry_hash(" in text, (
        "state/audit_chain.py missing compute_entry_hash() — Phase 6 T-6.1 "
        "must declare the canonical-JSON SHA256 helper used by both the "
        "verifier and the writer wiring (T-6.4)"
    )


@pytest.mark.spec_107_red
def test_decision_model_carries_prev_event_hash_field() -> None:
    """G-12: Decision model has additive `prev_event_hash` field (D-107-10)."""
    models_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "models.py"
    text = models_path.read_text(encoding="utf-8")
    assert "prev_event_hash" in text, (
        "state/models.py missing `prev_event_hash` field — "
        "Phase 6 T-6.3 must add the additive backward-compat field to Decision"
    )


@pytest.mark.spec_107_red
def test_observability_emits_prev_event_hash() -> None:
    """G-12: observability emit_control_outcome wires prev_event_hash."""
    obs_path = REPO_ROOT / "src" / "ai_engineering" / "state" / "observability.py"
    text = obs_path.read_text(encoding="utf-8")
    assert "prev_event_hash" in text or "prevEventHash" in text, (
        "state/observability.py missing prev_event_hash wiring — "
        "Phase 6 T-6.2 must populate prev_event_hash on every event emission"
    )


@pytest.mark.spec_107_red
def test_doctor_audit_chain_advisory_checks_exist() -> None:
    """G-12: doctor advisory checks `audit-chain-events` + `audit-chain-decisions`."""
    doctor_dir = REPO_ROOT / "src" / "ai_engineering" / "doctor"
    if not doctor_dir.is_dir():
        pytest.skip("doctor module missing — covered by Phase 6 T-6.5")
    found = False
    for path in doctor_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "audit-chain-events" in text or "audit-chain-decisions" in text:
            found = True
            break
    assert found, (
        "doctor missing `audit-chain-events`/`audit-chain-decisions` advisory checks "
        "— Phase 6 T-6.5 must add WARN-only advisory checks"
    )


@pytest.mark.spec_107_red
def test_audit_verify_cli_subcommand_exists() -> None:
    """G-12: `ai-eng audit verify [--file events|decisions|all]` CLI registered."""
    cli_dir = REPO_ROOT / "src" / "ai_engineering" / "cli"
    if not cli_dir.is_dir():
        pytest.skip("cli module missing — covered by Phase 6 T-6.6/T-6.7")
    found = False
    for path in cli_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "audit verify" in text or '"audit"' in text or "audit_app" in text:
            found = True
            break
    assert found, (
        "CLI missing `audit verify` subcommand — Phase 6 T-6.6/T-6.7 must "
        "register the `audit` sub-Typer app"
    )


@pytest.mark.spec_107_red
def test_verify_audit_chain_returns_ok_for_empty_file(tmp_path: Path) -> None:
    """Empty audit file is vacuously valid (no entries -> OK verdict)."""
    from ai_engineering.state.audit_chain import verify_audit_chain

    empty_path = tmp_path / "framework-events.ndjson"
    empty_path.write_text("", encoding="utf-8")
    verdict = verify_audit_chain(empty_path)
    assert getattr(verdict, "ok", False) is True, (
        "verify_audit_chain must return ok=True for empty file — Phase 6 T-6.1"
    )


@pytest.mark.spec_107_red
def test_verify_audit_chain_detects_mid_chain_tampering(tmp_path: Path) -> None:
    """Mid-chain mutation must be detected with first_break_index pointing to it."""
    import json

    from ai_engineering.state.audit_chain import (
        compute_entry_hash,
        verify_audit_chain,
    )

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
    assert getattr(verdict, "ok", True) is False, (
        "verify_audit_chain must detect mid-chain tampering — Phase 6 T-6.1"
    )


@pytest.mark.spec_107_red
def test_verify_audit_chain_accepts_legacy_entries(tmp_path: Path) -> None:
    """Legacy entries lacking prev_event_hash must NOT mark the chain broken."""
    import json

    from ai_engineering.state.audit_chain import verify_audit_chain

    chain_path = tmp_path / "framework-events.ndjson"
    legacy = {"id": "old1", "kind": "control_outcome"}
    chain_path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    verdict = verify_audit_chain(chain_path)
    # Legacy entries are additive backward-compat per D-107-10.
    assert getattr(verdict, "ok", False) is True, (
        "verify_audit_chain must accept legacy entries (no prev_event_hash) — "
        "Phase 6 T-6.1 (additive backward-compat)"
    )


@pytest.mark.spec_107_red
def test_verify_audit_chain_detects_truncation(tmp_path: Path) -> None:
    """File truncation (entries dropped) must be detected when chain refers backward."""
    import json

    from ai_engineering.state.audit_chain import (
        compute_entry_hash,
        verify_audit_chain,
    )

    chain_path = tmp_path / "framework-events.ndjson"
    entry1 = {"id": "e1", "kind": "control_outcome"}
    entry1["prev_event_hash"] = None
    # Forge entry2 with prev_event_hash pointing to a non-existent entry.
    entry2 = {"id": "e2", "kind": "control_outcome"}
    entry2["prev_event_hash"] = compute_entry_hash({"id": "PHANTOM"})
    chain_path.write_text(
        "\n".join(json.dumps(e) for e in (entry1, entry2)) + "\n",
        encoding="utf-8",
    )
    verdict = verify_audit_chain(chain_path)
    assert getattr(verdict, "ok", True) is False, (
        "verify_audit_chain must detect truncation/forged prev_event_hash — Phase 6 T-6.1"
    )
