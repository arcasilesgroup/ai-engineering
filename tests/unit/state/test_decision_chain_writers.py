"""spec-201 sub-001 T-2.1/T-2.2: decision writers preserve the hash chain.

`decision-store.json` is git-tracked, so a break in its chain is a
reviewable defect — and every writer that mutates an *existing* entry
invalidates the pointer of the entry after it. Three writers do exactly
that (`renew_decision`, `revoke_decision`, `mark_remediated`), and a
fourth (`upsert_decision_rows_raw`, the path `ai-eng decision record` /
`backfill` and `brainstorm.spec_approval` take) used to drop the pointer
entirely and stamp a fresh `updated_at` on every re-record.

The contract pinned here is a single rule: **whoever mutates an entry
owns re-linking everything after it.** Tests assert the on-disk verdict
via `verify_audit_chain`, not the implementation, so the writers stay
free to change how they do it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_engineering.state.audit_chain import verify_audit_chain
from ai_engineering.state.decision_store_io import (
    decision_store_path,
    list_decision_rows,
    upsert_decision_rows_raw,
)
from ai_engineering.state.models import DecisionStore, RiskSeverity
from ai_engineering.state.repository import DurableStateRepository
from skill_domain.decision_logic import (
    create_risk_acceptance,
    mark_remediated,
    renew_decision,
    revoke_decision,
)


def _seeded_store() -> DecisionStore:
    """Three chained risk acceptances: the middle one is the mutation target."""
    store = DecisionStore()
    for index in range(3):
        create_risk_acceptance(
            store,
            decision_id=f"spec-201-{index:03d}",
            context=f"finding {index}",
            decision_text=f"accept finding {index}",
            severity=RiskSeverity.LOW,
            follow_up="remediate later",
            spec="spec-201",
            accepted_by="tester",
            expires_at=datetime.now(tz=UTC) + timedelta(days=30),
        )
    return store


def _persist(tmp_path: Path, store: DecisionStore) -> Path:
    DurableStateRepository(tmp_path).save_decisions(store)
    return decision_store_path(tmp_path)


def _row(decision_id: str, **over: str | None) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "decision_id": decision_id,
        "spec_id": "spec-201",
        "status": "active",
        "title": f"title for {decision_id}",
        "rationale": "because reasons",
        "context": "spec.md:1",
        "consequences": None,
        "superseded_by": None,
        "expires_at": None,
    }
    base.update(over)
    return base


# ── the seed itself must be chained, or every test below is vacuous ──────


def test_seeded_store_chain_is_intact(tmp_path: Path) -> None:
    path = _persist(tmp_path, _seeded_store())
    assert verify_audit_chain(path, mode="json_array").ok


# ── in-place mutations relink the tail ───────────────────────────────────


def test_revoke_relinks_the_tail(tmp_path: Path) -> None:
    """Revoking a mid-ledger decision must not orphan the entries after it."""
    store = _seeded_store()
    revoke_decision(store, decision_id="spec-201-000")

    path = _persist(tmp_path, store)

    assert verify_audit_chain(path, mode="json_array").ok


def test_mark_remediated_relinks_the_tail(tmp_path: Path) -> None:
    store = _seeded_store()
    mark_remediated(store, decision_id="spec-201-001")

    path = _persist(tmp_path, store)

    assert verify_audit_chain(path, mode="json_array").ok


def test_renew_relinks_the_tail_and_chains_the_new_entry(tmp_path: Path) -> None:
    """Renew supersedes a mid-ledger entry *and* appends -- both must chain."""
    store = _seeded_store()
    renew_decision(
        store,
        decision_id="spec-201-000",
        justification="still not fixed",
        spec="spec-201",
        actor="tester",
    )

    path = _persist(tmp_path, store)

    verdict = verify_audit_chain(path, mode="json_array")
    assert verdict.ok, verdict.first_break_reason
    assert verdict.entries_checked == 4


def test_mutation_does_not_rewrite_other_payloads(tmp_path: Path) -> None:
    """Relinking the tail moves pointers only -- never decision content."""
    store = _seeded_store()
    before = {d.id: d.decision for d in store.decisions}

    revoke_decision(store, decision_id="spec-201-000")

    after = {d.id: d.decision for d in store.decisions}
    assert after == before
    assert verify_audit_chain(_persist(tmp_path, store), mode="json_array").ok


# ── the row writer (decision record / backfill / spec approval) ──────────


def test_upsert_preserves_an_existing_chain_pointer(tmp_path: Path) -> None:
    """A re-record must not strip the pointer the original write stamped."""
    store = _seeded_store()
    _persist(tmp_path, store)
    original = DurableStateRepository(tmp_path).load_decisions().decisions[1]
    assert original.prev_event_hash is not None

    upsert_decision_rows_raw(tmp_path, [_row(original.id, title="renamed")])

    reloaded = {d.id: d for d in DurableStateRepository(tmp_path).load_decisions().decisions}
    assert reloaded[original.id].prev_event_hash == original.prev_event_hash


def test_upsert_of_identical_data_is_idempotent(tmp_path: Path) -> None:
    """Re-recording byte-identical data must not bump ``updated_at``.

    An unconditional bump mutates the entry, which breaks the pointer of
    every entry after it on every single re-record -- perpetual churn
    that a tail-relink would only paper over.
    """
    upsert_decision_rows_raw(tmp_path, [_row("D-201-01"), _row("D-201-02")])
    before = {r["decision_id"]: r["updated_at"] for r in list_decision_rows(tmp_path)}

    upsert_decision_rows_raw(tmp_path, [_row("D-201-01"), _row("D-201-02")])

    after = {r["decision_id"]: r["updated_at"] for r in list_decision_rows(tmp_path)}
    assert after == before


def test_upsert_of_changed_data_bumps_updated_at(tmp_path: Path) -> None:
    """Idempotency must not become "never records a change"."""
    upsert_decision_rows_raw(tmp_path, [_row("D-201-01", title="first")])
    before = list_decision_rows(tmp_path)[0]["updated_at"]

    upsert_decision_rows_raw(tmp_path, [_row("D-201-01", title="second", context="spec.md:9")])

    after = list_decision_rows(tmp_path)[0]
    assert after["title"] == "second"
    assert after["updated_at"] != before or after["context"] == "spec.md:9"


def test_upsert_leaves_the_chain_verifiable(tmp_path: Path) -> None:
    """A record into an already-chained ledger keeps the chain intact."""
    store = _seeded_store()
    path = _persist(tmp_path, store)

    upsert_decision_rows_raw(tmp_path, [_row("spec-201-000", title="edited in place")])

    verdict = verify_audit_chain(path, mode="json_array")
    assert verdict.ok, verdict.first_break_reason


def test_repeated_upserts_never_break_the_chain(tmp_path: Path) -> None:
    """The `decision backfill` loop is the real-world shape -- run it twice."""
    store = _seeded_store()
    path = _persist(tmp_path, store)
    rows = [_row(f"D-201-{i:02d}") for i in range(3)]

    upsert_decision_rows_raw(tmp_path, rows)
    upsert_decision_rows_raw(tmp_path, rows)

    verdict = verify_audit_chain(path, mode="json_array")
    assert verdict.ok, verdict.first_break_reason
