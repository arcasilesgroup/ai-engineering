"""Migration integrity gate tests (spec-122-b T-2.1)."""

from __future__ import annotations

import sqlite3
import textwrap
from pathlib import Path

import pytest

from ai_engineering.state.migrations import (
    MigrationIntegrityError,
    _runner,
    run_pending,
    verify_integrity,
)


@pytest.fixture
def tmp_migrations_dir(tmp_path, monkeypatch):
    """Point the runner at an isolated migrations directory."""
    fake_dir = tmp_path / "migrations"
    fake_dir.mkdir()
    monkeypatch.setattr(_runner, "_migrations_dir", lambda: fake_dir)
    return fake_dir


def _write_migration(target_dir: Path, name: str, body_sha: str | None = None) -> Path:
    """Write a noop migration with a deterministic BODY_SHA256."""
    file_path = target_dir / name
    body = textwrap.dedent(
        """
        from __future__ import annotations
        import sqlite3

        BODY_SHA256 = "PLACEHOLDER"

        def apply(conn: sqlite3.Connection) -> None:
            conn.execute("CREATE TABLE IF NOT EXISTS noop (id INTEGER) STRICT")
        """
    ).lstrip()
    file_path.write_text(body, encoding="utf-8")
    # Compute the real body sha and update the placeholder.
    real_sha = _runner._hash_migration_body(file_path)
    if body_sha is None:
        body_sha = real_sha
    file_path.write_text(
        body.replace('BODY_SHA256 = "PLACEHOLDER"', f'BODY_SHA256 = "{body_sha}"'),
        encoding="utf-8",
    )
    return file_path


def _make_conn(tmp_path) -> sqlite3.Connection:
    db_path = tmp_path / "state.db"
    return sqlite3.connect(db_path)


def _import_fake_migration(monkeypatch, fake_dir: Path) -> None:
    """Force ``_load_module`` to import from the fake directory."""
    import importlib.util
    import sys

    real_load = _runner._load_module

    def loader(path: Path):
        spec = importlib.util.spec_from_file_location(f"fake_migrations.{path.stem}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    monkeypatch.setattr(_runner, "_load_module", loader)


def test_clean_apply_records_sha256(tmp_path, tmp_migrations_dir, monkeypatch):
    """Applying a fresh migration records its sha256 in `_migrations`."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "enforce")
    _write_migration(tmp_migrations_dir, "0001_noop.py")
    _import_fake_migration(monkeypatch, tmp_migrations_dir)

    conn = _make_conn(tmp_path)
    try:
        applied = run_pending(conn)
        assert applied == ["0001_noop"]
        row = conn.execute(
            "SELECT id, sha256 FROM _migrations WHERE id = ?",
            ("0001_noop",),
        ).fetchone()
        assert row is not None
        assert len(row[1]) == 64  # hex sha256
    finally:
        conn.close()


def test_tampered_body_under_enforce_raises(tmp_path, tmp_migrations_dir, monkeypatch):
    """Re-applying after body edit raises in enforce mode."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "enforce")
    path = _write_migration(tmp_migrations_dir, "0001_noop.py")
    _import_fake_migration(monkeypatch, tmp_migrations_dir)

    conn = _make_conn(tmp_path)
    try:
        run_pending(conn)
        # Tamper with body; sha256 ledger row still references original.
        path.write_text(
            path.read_text(encoding="utf-8") + "\n# tampered comment\n",
            encoding="utf-8",
        )
        emitted = []
        monkeypatch.setattr(
            _runner,
            "_emit_integrity_violation",
            lambda mid, exp, act: emitted.append((mid, exp, act)),
        )
        with pytest.raises(MigrationIntegrityError):
            run_pending(conn)
        assert emitted, "framework_error telemetry should be emitted before raising"
    finally:
        conn.close()


def test_tampered_body_under_warn_proceeds(tmp_path, tmp_migrations_dir, monkeypatch):
    """warn mode logs but does not raise; downstream code continues."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "warn")
    path = _write_migration(tmp_migrations_dir, "0001_noop.py")
    _import_fake_migration(monkeypatch, tmp_migrations_dir)

    conn = _make_conn(tmp_path)
    try:
        run_pending(conn)
        path.write_text(
            path.read_text(encoding="utf-8") + "\n# tampered comment\n",
            encoding="utf-8",
        )
        emitted = []
        monkeypatch.setattr(
            _runner,
            "_emit_integrity_violation",
            lambda mid, exp, act: emitted.append((mid, exp, act)),
        )
        # Should NOT raise.
        run_pending(conn)
        assert emitted, "warn mode still emits telemetry"
    finally:
        conn.close()


def test_off_mode_skips_check(tmp_path, tmp_migrations_dir, monkeypatch):
    """off mode skips the check entirely (no telemetry, no raise)."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "off")
    path = _write_migration(tmp_migrations_dir, "0001_noop.py")
    _import_fake_migration(monkeypatch, tmp_migrations_dir)

    conn = _make_conn(tmp_path)
    try:
        run_pending(conn)
        path.write_text(
            path.read_text(encoding="utf-8") + "\n# tampered comment\n",
            encoding="utf-8",
        )
        emitted = []
        monkeypatch.setattr(
            _runner,
            "_emit_integrity_violation",
            lambda mid, exp, act: emitted.append((mid, exp, act)),
        )
        run_pending(conn)
        assert not emitted, "off mode emits no telemetry"
    finally:
        conn.close()


def test_verify_integrity_returns_violations_in_warn(tmp_path, tmp_migrations_dir, monkeypatch):
    """verify_integrity returns a list of violations in warn mode."""
    monkeypatch.setenv("AIENG_HOOK_INTEGRITY_MODE", "warn")
    path = _write_migration(tmp_migrations_dir, "0001_noop.py")
    _import_fake_migration(monkeypatch, tmp_migrations_dir)

    conn = _make_conn(tmp_path)
    try:
        run_pending(conn)
        path.write_text(
            path.read_text(encoding="utf-8") + "\n# extra\n",
            encoding="utf-8",
        )
        violations = verify_integrity(conn)
        assert len(violations) == 1
        assert violations[0]["migration_id"] == "0001_noop"
    finally:
        conn.close()
