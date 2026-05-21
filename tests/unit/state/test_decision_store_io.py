"""spec-148 P2 (RED→GREEN): file-backed decision-store row adapter.

`decision_store_io` replaces the retired SQLite `decisions` table helpers
(`state_db.list_decisions` / `upsert_decision_rows_raw`). `decision-store.json`
is the single source of truth; the adapter maps between the CLI/backfill
row-dict vocabulary and the canonical `Decision` model. These tests pin:

* round-trip parity (upsert rows → list returns the same row fields);
* status filtering and `decision_id` ASC ordering;
* UPSERT merge-by-id semantics + the attempted-count contract;
* row-only fields (rationale / consequences / superseded_by) survive via
  the `Decision` model's `extra="allow"` ledger metadata;
* the canonical artifact is `decision-store.json` and nothing else
  (no `state.db`), readable through `DurableStateRepository.load_decisions`.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.decision_store_io import (
    decision_store_path,
    list_decision_rows,
    upsert_decision_rows_raw,
)
from ai_engineering.state.repository import DurableStateRepository


def _row(decision_id: str, **over: str | None) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "decision_id": decision_id,
        "spec_id": "spec-148",
        "status": "active",
        "title": f"title for {decision_id}",
        "rationale": "because reasons",
        "context": "ctx.md:1",
        "consequences": None,
        "superseded_by": None,
        "expires_at": None,
    }
    base.update(over)
    return base


def test_canonical_artifact_is_decision_store_json(tmp_path: Path) -> None:
    """The sole SoT is `decision-store.json` under the state dir; no state.db."""
    assert decision_store_path(tmp_path).name == "decision-store.json"
    upsert_decision_rows_raw(tmp_path, [_row("D-148-01")])
    assert decision_store_path(tmp_path).is_file()
    assert not (tmp_path / ".ai-engineering" / "state" / "state.db").exists()


def test_upsert_then_list_round_trip(tmp_path: Path) -> None:
    """Rows written via the adapter come back through `list_decision_rows`."""
    attempted = upsert_decision_rows_raw(
        tmp_path, [_row("D-148-02", title="alpha"), _row("D-148-01", title="beta")]
    )
    assert attempted == 2

    rows = list_decision_rows(tmp_path)
    # decision_id ASC ordering (parity with the retired SQL `ORDER BY`).
    assert [r["decision_id"] for r in rows] == ["D-148-01", "D-148-02"]
    by_id = {r["decision_id"]: r for r in rows}
    assert by_id["D-148-01"]["title"] == "beta"
    assert by_id["D-148-02"]["spec_id"] == "spec-148"


def test_status_filter(tmp_path: Path) -> None:
    """`status=` narrows the result set the way the SQL filter did."""
    upsert_decision_rows_raw(
        tmp_path,
        [_row("D-148-01", status="active"), _row("D-148-02", status="expired")],
    )
    active = list_decision_rows(tmp_path, status="active")
    assert [r["decision_id"] for r in active] == ["D-148-01"]
    expired = list_decision_rows(tmp_path, status="expired")
    assert [r["decision_id"] for r in expired] == ["D-148-02"]


def test_upsert_merges_by_id(tmp_path: Path) -> None:
    """Re-upserting an existing id updates in place (no duplicate row)."""
    upsert_decision_rows_raw(tmp_path, [_row("D-148-01", status="active", title="v1")])
    upsert_decision_rows_raw(tmp_path, [_row("D-148-01", status="revoked", title="v2")])

    rows = list_decision_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "revoked"
    assert rows[0]["title"] == "v2"


def test_row_only_fields_survive(tmp_path: Path) -> None:
    """rationale / consequences / superseded_by persist across the JSON round-trip."""
    upsert_decision_rows_raw(
        tmp_path,
        [
            _row(
                "D-148-01",
                rationale="keeps one SoT",
                consequences="state.db retired",
                superseded_by="D-148-10",
            )
        ],
    )
    row = list_decision_rows(tmp_path)[0]
    assert row["rationale"] == "keeps one SoT"
    assert row["consequences"] == "state.db retired"
    assert row["superseded_by"] == "D-148-10"


def test_empty_rows_is_zero_and_idempotent(tmp_path: Path) -> None:
    """An empty upsert writes nothing new and returns 0 (parity with raw)."""
    assert upsert_decision_rows_raw(tmp_path, []) == 0
    assert list_decision_rows(tmp_path) == []


def test_repository_load_sees_adapter_writes(tmp_path: Path) -> None:
    """The model-level repository reads the same `decision-store.json`."""
    upsert_decision_rows_raw(tmp_path, [_row("D-148-01", title="shared")])
    store = DurableStateRepository(tmp_path).load_decisions()
    ids = {d.id for d in store.decisions}
    assert "D-148-01" in ids
