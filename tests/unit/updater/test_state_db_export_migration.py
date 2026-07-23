"""spec-148 P5 (RED→GREEN): one-shot state.db → files export migration.

``ai-eng update`` runs ``migrate_state_db_to_files`` to ingest a legacy
``state.db`` (pre-spec-148 install) into the canonical file stores, VERIFY
the export, then DELETE ``state.db`` (+ WAL/SHM). Contract:

* No-op (and no error) when ``state.db`` is absent.
* Exports ``install_state`` → install-state.json, ``decisions`` →
  decision-store.json, ``ownership_map`` → ownership-map.json — only when
  the file home is absent (never clobbers newer file data).
* Hook-hash tooling entries in ``install_state`` survive (hook integrity).
* Fail-loud: a failed verify must NOT delete state.db.
* Deletes state.db + state.db-wal + state.db-shm on success.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ai_engineering.updater.state_db_export import migrate_state_db_to_files


def _make_legacy_state_db(root: Path) -> Path:
    """Create a minimal legacy state.db with install_state + decisions + ownership rows."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    db = state_dir / "state.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("CREATE TABLE install_state (id INTEGER PRIMARY KEY, state_json TEXT)")
        install_payload = {
            "schema_version": "2.0",
            "tooling": {"hook_hash:commit-msg": {"mode": "abc123", "authenticated": False}},
        }
        conn.execute(
            "INSERT INTO install_state (id, state_json) VALUES (1, ?)",
            (json.dumps(install_payload),),
        )
        conn.execute(
            "CREATE TABLE decisions (decision_id TEXT PRIMARY KEY, spec_id TEXT, status TEXT, "
            "title TEXT, rationale TEXT, context TEXT, consequences TEXT, superseded_by TEXT, "
            "expires_at TEXT, details_json TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO decisions (decision_id, spec_id, status, title, context, created_at) "
            "VALUES ('D-9-01', 'spec-9', 'active', 'legacy', 'ctx', '2026-01-01T00:00:00Z')"
        )
        conn.execute(
            "CREATE TABLE ownership_map (path_pattern TEXT PRIMARY KEY, owners_json TEXT, "
            "severity TEXT, reviewers_json TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO ownership_map (path_pattern, owners_json, severity) "
            "VALUES ('CLAUDE.md', '[\"team-managed\"]', 'deny')"
        )
        conn.commit()
    finally:
        conn.close()
    return db


def test_noop_when_state_db_absent(tmp_path: Path) -> None:
    """Absent state.db -> no-op, no error, no files written."""
    result = migrate_state_db_to_files(tmp_path)
    assert result["status"] == "noop"
    assert not (tmp_path / ".ai-engineering" / "state" / "install-state.json").exists()


def test_exports_then_deletes_state_db(tmp_path: Path) -> None:
    """Export install_state/decisions/ownership to files, then delete state.db."""
    db = _make_legacy_state_db(tmp_path)
    result = migrate_state_db_to_files(tmp_path)

    assert result["status"] == "migrated"
    state_dir = tmp_path / ".ai-engineering" / "state"
    # state.db (+ siblings) gone.
    assert not db.exists()
    assert not (state_dir / "state.db-wal").exists()
    assert not (state_dir / "state.db-shm").exists()
    # Files written.
    assert (state_dir / "install-state.json").is_file()
    assert (state_dir / "decision-store.json").is_file()
    assert (state_dir / "ownership-map.json").is_file()


def test_hook_hashes_survive_export(tmp_path: Path) -> None:
    """install_state hook_hash entries survive the migration (hook integrity)."""
    _make_legacy_state_db(tmp_path)
    migrate_state_db_to_files(tmp_path)

    from ai_engineering.state.service import load_install_state

    state = load_install_state(tmp_path / ".ai-engineering" / "state")
    assert "hook_hash:commit-msg" in state.tooling


def test_decisions_and_ownership_survive(tmp_path: Path) -> None:
    """Legacy decisions + ownership rows land in their file homes."""
    _make_legacy_state_db(tmp_path)
    migrate_state_db_to_files(tmp_path)

    from ai_engineering.state.repository import DurableStateRepository

    repo = DurableStateRepository(tmp_path)
    assert "D-9-01" in {d.id for d in repo.load_decisions().decisions}
    assert "CLAUDE.md" in {e.pattern for e in repo.load_ownership().paths}


def test_does_not_clobber_existing_files(tmp_path: Path) -> None:
    """A pre-existing install-state.json is preserved (state.db is the stale source)."""
    _make_legacy_state_db(tmp_path)
    state_dir = tmp_path / ".ai-engineering" / "state"
    # A newer install-state.json already on disk (schema_version 9.9).
    from ai_engineering.state.service import load_install_state, save_install_state
    from skill_domain.state_models import InstallState

    save_install_state(state_dir, InstallState.model_validate({"schema_version": "9.9"}))

    migrate_state_db_to_files(tmp_path)

    # The newer file wins; the stale state.db value did not overwrite it.
    assert load_install_state(state_dir).schema_version == "9.9"
    assert not (state_dir / "state.db").exists()


def test_idempotent(tmp_path: Path) -> None:
    """Running twice is safe: second run is a no-op (state.db already gone)."""
    _make_legacy_state_db(tmp_path)
    migrate_state_db_to_files(tmp_path)
    result2 = migrate_state_db_to_files(tmp_path)
    assert result2["status"] == "noop"


def test_fail_loud_keeps_state_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If verification fails, state.db is NOT deleted (no data loss)."""
    db = _make_legacy_state_db(tmp_path)
    import ai_engineering.updater.state_db_export as mod

    monkeypatch.setattr(mod, "_verify_export", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="verif"):
        migrate_state_db_to_files(tmp_path)
    assert db.exists(), "state.db must survive a failed verification"
