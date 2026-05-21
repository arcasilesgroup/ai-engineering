"""Spec-138 M3.T3: ``ai-eng decision backfill`` walks specs + archive + CHANGELOG.

The backfill subcommand is the cold-path autopopulator: it discovers
every ``D-NNN-NN`` marker across active specs, archived specs, the
CHANGELOG, the constitution, and CLAUDE.md, then UPSERTs the result
into ``decision-store.json`` (spec-148 P2). Idempotent on re-run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.cli_commands import decisions_cmd
from ai_engineering.state.decision_store_io import list_decision_rows

_ACTIVE_SPEC = """---
spec: spec-900
status: approved
---

## Decisions

- **D-900-01 -- Active decision.** Rationale: lands first.
"""

_ARCHIVED_SPEC = """---
spec: spec-901
status: shipped
---

## Decisions

- **D-901-01 -- Archived decision.** Rationale: still authoritative for history.
- **D-901-02 -- Second archived.** Rationale: ditto.
"""

_CHANGELOG = """# Changelog

## [Unreleased]

### Added — autopopulation (M3)

- D-902-01 referenced in changelog body.
"""


def _seed_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lay down a synthetic repo with active + archived specs + CHANGELOG."""
    specs = tmp_path / ".ai-engineering" / "specs"
    archive = specs / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (specs / "spec.md").write_text(_ACTIVE_SPEC, encoding="utf-8")
    (archive / "spec-901-archived.md").write_text(_ARCHIVED_SPEC, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(_CHANGELOG, encoding="utf-8")
    # Pretend the project root resolves to tmp_path.
    monkeypatch.setattr(decisions_cmd, "find_project_root", lambda: tmp_path)


def test_decision_backfill_walks_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both active spec.md AND archive/*.md are scanned."""
    _seed_repo(tmp_path, monkeypatch)
    decisions_cmd.decision_backfill(sources=None, dry_run=False)
    rows = list_decision_rows(tmp_path)
    decision_ids = sorted(r["decision_id"] for r in rows)
    # All four IDs across the three sources.
    assert decision_ids == ["D-900-01", "D-901-01", "D-901-02", "D-902-01"]


def test_decision_backfill_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-running backfill twice yields the same row set."""
    _seed_repo(tmp_path, monkeypatch)
    decisions_cmd.decision_backfill(sources=None, dry_run=False)
    decisions_cmd.decision_backfill(sources=None, dry_run=False)
    rows = list_decision_rows(tmp_path)
    decision_ids = sorted(r["decision_id"] for r in rows)
    assert decision_ids == ["D-900-01", "D-901-01", "D-901-02", "D-902-01"]


def test_decision_backfill_dry_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run mode prints candidates but never UPSERTs."""
    _seed_repo(tmp_path, monkeypatch)
    decisions_cmd.decision_backfill(sources=None, dry_run=True)
    rows = list_decision_rows(tmp_path)
    assert rows == []


def test_decision_backfill_archive_label_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The archive subdirectory is reported as a distinct source label."""
    _seed_repo(tmp_path, monkeypatch)
    files = decisions_cmd._iter_source_files(tmp_path, decisions_cmd._DEFAULT_BACKFILL_GLOBS)
    rels = [f.relative_to(tmp_path).as_posix() for f in files]
    assert any(r.startswith(".ai-engineering/specs/archive/") for r in rels)
    # And the label resolver returns ``specs-archive`` for those paths.
    assert (
        decisions_cmd._label_for_path(".ai-engineering/specs/archive/spec-901.md")
        == "specs-archive"
    )
