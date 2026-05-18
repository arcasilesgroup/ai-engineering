"""Spec-138 M3.T1/M3.T2: brainstorm/plan approval writes decisions.

The approval handler is the entry point invoked by ``/ai-brainstorm``
when a spec moves to ``status: approved`` (and ``/ai-plan`` for new
decisions surfaced during planning). These tests pin the contract that
every ``D-NNN-NN`` marker in the spec markdown's ``## Decisions``
section lands in ``state.db.decisions`` exactly once.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.brainstorm.spec_approval import (
    extract_decisions,
    handle_spec_approval,
)
from ai_engineering.state.state_db import list_decisions

_SAMPLE_SPEC = """---
spec: spec-999
slug: writer-integration
status: approved
---

# spec-999 -- Writer Integration

## Summary

Pretend prose so the heading detector has something to skip.

## Decisions

- **D-999-01 -- Pin Foo to bar.** Body sentence. Rationale: foo and bar
  must align; otherwise downstream breaks.
- **D-999-02 -- Disable widget.** Single-line entry.
  *Rationale*: the widget has been YAGNI debt since the spec-997 cleanup.
- **D-999-03 -- Adopt baz.**
  **Rationale**: align with the upstream convention.

## Risks

| ... | ... |
"""


def _seed_spec(tmp_path: Path, content: str = _SAMPLE_SPEC) -> Path:
    spec_dir = tmp_path / ".ai-engineering" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / "spec.md"
    spec_path.write_text(content, encoding="utf-8")
    return spec_path


def test_extract_decisions_finds_three_rows(tmp_path: Path) -> None:
    """The pure parser surfaces every D-NNN-NN with its title."""
    spec_path = _seed_spec(tmp_path)
    rows = extract_decisions(spec_path)
    decision_ids = sorted(r["decision_id"] for r in rows)
    assert decision_ids == ["D-999-01", "D-999-02", "D-999-03"]
    titles = {r["decision_id"]: r["title"] for r in rows}
    assert "Pin Foo to bar" in (titles["D-999-01"] or "")
    assert "Disable widget" in (titles["D-999-02"] or "")
    assert "Adopt baz" in (titles["D-999-03"] or "")


def test_extract_decisions_resolves_rationale(tmp_path: Path) -> None:
    """Inline + next-line Rationale: markers resolve to a non-empty string."""
    spec_path = _seed_spec(tmp_path)
    rows = {r["decision_id"]: r for r in extract_decisions(spec_path)}
    # D-999-01: inline 'Rationale:' on the same line.
    assert rows["D-999-01"]["rationale"] is not None
    assert "downstream" in rows["D-999-01"]["rationale"]
    # D-999-02: '*Rationale*:' on the next non-blank line.
    assert rows["D-999-02"]["rationale"] is not None
    assert "YAGNI" in rows["D-999-02"]["rationale"]
    # D-999-03: '**Rationale**:' on the next non-blank line.
    assert rows["D-999-03"]["rationale"] is not None
    assert "upstream" in rows["D-999-03"]["rationale"]


def test_handle_spec_approval_writes_rows(tmp_path: Path) -> None:
    """The approval handler UPSERTs every parsed decision into state.db."""
    spec_path = _seed_spec(tmp_path)
    attempted = handle_spec_approval(tmp_path, spec_path)
    assert attempted == 3
    rows = list_decisions(tmp_path)
    decision_ids = sorted(r["decision_id"] for r in rows)
    assert decision_ids == ["D-999-01", "D-999-02", "D-999-03"]
    by_id = {r["decision_id"]: r for r in rows}
    assert by_id["D-999-01"]["spec_id"] == "spec-999"
    assert by_id["D-999-01"]["status"] == "active"


def test_handle_spec_approval_is_idempotent(tmp_path: Path) -> None:
    """Re-running the handler with the same input does not duplicate rows."""
    spec_path = _seed_spec(tmp_path)
    handle_spec_approval(tmp_path, spec_path)
    handle_spec_approval(tmp_path, spec_path)
    rows = list_decisions(tmp_path)
    decision_ids = sorted(r["decision_id"] for r in rows)
    # Still exactly three -- not six.
    assert decision_ids == ["D-999-01", "D-999-02", "D-999-03"]


def test_handle_spec_approval_returns_zero_when_missing(tmp_path: Path) -> None:
    """A missing spec.md yields zero rows attempted and no state.db rows."""
    missing = tmp_path / ".ai-engineering" / "specs" / "spec.md"
    attempted = handle_spec_approval(tmp_path, missing)
    assert attempted == 0
    # list_decisions returns [] when state.db has no rows.
    assert list_decisions(tmp_path) == []


def test_extract_decisions_ignores_non_decisions_section(tmp_path: Path) -> None:
    """D-IDs outside the ``## Decisions`` block are NOT picked up."""
    body = """---
spec: spec-998
status: approved
---

## Summary

We cite D-998-77 in passing here, but it is not an active decision.

## Decisions

- **D-998-01 -- Real decision.** Rationale: this one matters.

## References

See D-998-99 from a prior spec.
"""
    spec_path = _seed_spec(tmp_path, body)
    rows = extract_decisions(spec_path)
    decision_ids = sorted(r["decision_id"] for r in rows)
    # D-998-77 (summary) and D-998-99 (references) are intentionally
    # ignored; only the ``## Decisions`` bullet is captured.
    assert decision_ids == ["D-998-01"]
