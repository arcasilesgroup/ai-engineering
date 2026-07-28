"""spec-201 sub-001 T-1.1/T-1.2: audit-chain relink core.

`relink_entries` is the pure repair core: it re-stamps `prev_event_hash`
pointers so every entry chains to its predecessor, mirroring the
resolution rules of :func:`verify_audit_chain` exactly. It is consumed by
the ``ai-eng audit relink`` verb *and* by the decision writers, so its
contract is pinned here rather than in the CLI tests.

Pinned invariants (each one is a way the repair could corrupt the very
tamper-evidence it exists to restore):

* payload fields are never touched -- only the pointer field;
* the field spelling each entry already uses is preserved (decisions use
  the camelCase ``prevEventHash`` alias, events use snake_case
  ``prev_event_hash``); writing both would change nothing about the hash
  but would silently double the surface a future reader must resolve;
* legacy entries with no pointer at all stay pointer-less and re-anchor
  the chain, exactly as the verifier treats them (D-107-10);
* entry 0 anchors at ``None``;
* relinking is idempotent and leaves an intact chain byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.audit_chain import (
    compute_entry_hash,
    relink_audit_chain,
    relink_entries,
    verify_audit_chain,
)


def _event(index: int, **extra: object) -> dict:
    """Minimal event payload; ``index`` keeps each entry's hash distinct."""
    payload: dict = {
        "kind": "framework_operation",
        "timestamp": f"2026-07-27T00:00:{index:02d}Z",
        "detail": {"operation": f"op-{index}"},
    }
    payload.update(extra)
    return payload


def _chained(count: int, *, field: str = "prev_event_hash") -> list[dict]:
    """Build a correctly chained list of ``count`` entries."""
    entries: list[dict] = []
    prior: str | None = None
    for index in range(count):
        entry = _event(index)
        entry[field] = prior
        entries.append(entry)
        prior = compute_entry_hash(entry)
    return entries


def _write_ndjson(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in entries),
        encoding="utf-8",
    )


def _write_decision_store(path: Path, decisions: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "active_decisions": [],
        "decisions": decisions,
        "schemaVersion": "1.1",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ── relink_entries: the pure core ────────────────────────────────────────


def test_intact_chain_is_left_alone() -> None:
    """A healthy chain relinks to zero changes and identical objects."""
    entries = _chained(4)
    relinked, changed = relink_entries(entries)

    assert changed == 0
    assert relinked == entries


def test_broken_pointer_is_repaired() -> None:
    """A mutated mid-chain pointer is re-stamped and the chain verifies."""
    entries = _chained(4)
    entries[2]["prev_event_hash"] = "0" * 64

    relinked, changed = relink_entries(entries)

    assert changed == 1
    assert relinked[2]["prev_event_hash"] == compute_entry_hash(relinked[1])


def test_inputs_are_not_mutated() -> None:
    """The core is pure: the caller's entries survive untouched."""
    entries = _chained(3)
    entries[1]["prev_event_hash"] = "deadbeef"

    relink_entries(entries)

    assert entries[1]["prev_event_hash"] == "deadbeef"


def test_payload_fields_are_never_touched() -> None:
    """Only the pointer moves -- a relink must not rewrite ledger content."""
    entries = _chained(3)
    entries[2]["prev_event_hash"] = "0" * 64

    relinked, _ = relink_entries(entries)

    for before, after in zip(entries, relinked, strict=True):
        assert {k: v for k, v in before.items() if k != "prev_event_hash"} == {
            k: v for k, v in after.items() if k != "prev_event_hash"
        }


def test_camel_case_alias_spelling_is_preserved() -> None:
    """Decision entries keep ``prevEventHash``; the snake form is not added."""
    entries = _chained(3, field="prevEventHash")
    entries[1]["prevEventHash"] = "0" * 64

    relinked, changed = relink_entries(entries)

    assert changed == 1
    assert relinked[1]["prevEventHash"] == compute_entry_hash(relinked[0])
    assert "prev_event_hash" not in relinked[1]


def test_pointerless_entries_stay_pointerless_and_reanchor() -> None:
    """Legacy pointer-less entries are left alone and re-anchor the chain."""
    entries = _chained(3)
    del entries[1]["prev_event_hash"]
    entries[2]["prev_event_hash"] = "0" * 64

    relinked, changed = relink_entries(entries)

    assert "prev_event_hash" not in relinked[1]
    assert "prevEventHash" not in relinked[1]
    # entry 2 re-anchors on the pointer-less entry rather than skipping it.
    assert relinked[2]["prev_event_hash"] == compute_entry_hash(relinked[1])
    assert changed == 1


def test_first_entry_anchors_at_none() -> None:
    """A non-null head pointer (head truncation) is reset to the anchor."""
    entries = _chained(2)
    entries[0]["prev_event_hash"] = "f" * 64

    relinked, changed = relink_entries(entries)

    assert relinked[0]["prev_event_hash"] is None
    assert changed >= 1


def test_relink_is_idempotent() -> None:
    """A second pass over a repaired chain changes nothing."""
    entries = _chained(5)
    entries[3]["prev_event_hash"] = "0" * 64

    once, first_changed = relink_entries(entries)
    twice, second_changed = relink_entries(once)

    assert first_changed == 1
    assert second_changed == 0
    assert twice == once


def test_empty_entries_are_vacuously_relinked() -> None:
    relinked, changed = relink_entries([])
    assert relinked == []
    assert changed == 0


# ── relink_audit_chain: the file-level rewrite ───────────────────────────


def test_ndjson_file_relink_repairs_the_chain(tmp_path: Path) -> None:
    """A broken events ndjson verifies clean after the rewrite."""
    path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    entries = _chained(5)
    entries[3]["prev_event_hash"] = "0" * 64
    _write_ndjson(path, entries)
    assert not verify_audit_chain(path, mode="ndjson").ok

    result = relink_audit_chain(path, mode="ndjson", project_root=tmp_path)

    assert result.ok
    assert result.relinked == 1
    assert result.written is True
    assert result.entries_total == 5
    assert verify_audit_chain(path, mode="ndjson").ok


def test_ndjson_relink_rewrites_only_the_broken_lines(tmp_path: Path) -> None:
    """Unchanged entries keep their original bytes (minimal rewrite)."""
    path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    entries = _chained(4)
    entries[2]["prev_event_hash"] = "0" * 64
    _write_ndjson(path, entries)
    before = path.read_text(encoding="utf-8").splitlines()

    relink_audit_chain(path, mode="ndjson", project_root=tmp_path)

    after = path.read_text(encoding="utf-8").splitlines()
    assert len(after) == len(before)
    assert [before[i] == after[i] for i in range(4)] == [True, True, False, True]


def test_ndjson_relink_dry_run_does_not_write(tmp_path: Path) -> None:
    path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    entries = _chained(3)
    entries[1]["prev_event_hash"] = "0" * 64
    _write_ndjson(path, entries)
    before = path.read_bytes()

    result = relink_audit_chain(path, mode="ndjson", project_root=tmp_path, dry_run=True)

    assert result.ok
    assert result.relinked == 1
    assert result.written is False
    assert path.read_bytes() == before


def test_intact_ndjson_is_not_rewritten(tmp_path: Path) -> None:
    path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    _write_ndjson(path, _chained(3))
    before = path.read_bytes()

    result = relink_audit_chain(path, mode="ndjson", project_root=tmp_path)

    assert result.relinked == 0
    assert result.written is False
    assert path.read_bytes() == before


def test_json_array_relink_repairs_decisions(tmp_path: Path) -> None:
    """The decision-store shape is repaired without disturbing other keys."""
    path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    decisions = _chained(3, field="prevEventHash")
    decisions[1]["prevEventHash"] = "0" * 64
    _write_decision_store(path, decisions)

    result = relink_audit_chain(path, mode="json_array", project_root=tmp_path)

    assert result.ok
    assert result.relinked == 1
    assert result.written is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"active_decisions", "decisions", "schemaVersion"}
    assert payload["schemaVersion"] == "1.1"
    assert verify_audit_chain(path, mode="json_array").ok


def test_json_array_relink_keeps_serialization_stable(tmp_path: Path) -> None:
    """An already-intact store is byte-stable through the verb."""
    path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    _write_decision_store(path, _chained(3, field="prevEventHash"))
    before = path.read_bytes()

    result = relink_audit_chain(path, mode="json_array", project_root=tmp_path)

    assert result.relinked == 0
    assert path.read_bytes() == before


def test_missing_file_is_vacuously_ok(tmp_path: Path) -> None:
    path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"

    result = relink_audit_chain(path, mode="ndjson", project_root=tmp_path)

    assert result.ok
    assert result.entries_total == 0
    assert result.relinked == 0
    assert result.written is False


def test_unparseable_file_is_refused_not_rewritten(tmp_path: Path) -> None:
    """A malformed ledger is reported, never silently rewritten."""
    path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"kind": "a"}\nnot json at all\n', encoding="utf-8")
    before = path.read_bytes()

    result = relink_audit_chain(path, mode="ndjson", project_root=tmp_path)

    assert result.ok is False
    assert result.written is False
    assert result.reason is not None
    assert path.read_bytes() == before
