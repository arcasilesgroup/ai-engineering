"""Tests for StatePhase UPSERT semantics (spec-132 D-132-08).

Spec-132 requires the installer's state phase to write ownership +
decision rows directly into ``state.db`` instead of materialising the
legacy ``ownership-map.json`` / ``decision-store.json`` JSON sidecars.
The phase also performs a one-shot cleanup pass that removes the
legacy files if they already exist (D-132-18).

These tests pin both contracts:

* Rows appear in ``ownership_map`` and ``decisions`` after the phase.
* No legacy JSON files exist on disk after the phase completes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_engineering.installer.phases import InstallContext, InstallMode
from ai_engineering.installer.phases.state import StatePhase
from ai_engineering.state import state_db


def _ctx(tmp_path: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
    )


def _state_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".ai-engineering" / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _seed_minimal_install(tmp_path: Path) -> None:
    """Seed the minimum on-disk shape so the state phase can run.

    The state phase expects:
      * ``.ai-engineering/`` to exist (manifest.yml is optional for our
        rows -- the loader returns an empty mapping when absent).
      * ``.ai-engineering/state/`` to exist (it creates state.db inside).
    """
    _state_dir(tmp_path)


def test_state_phase_upserts_ownership_rows(tmp_path: Path) -> None:
    """spec-132 D-132-08: ownership_map table is populated post-execute."""
    _seed_minimal_install(tmp_path)
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    db_path = state_db.state_db_path(tmp_path)
    assert db_path.is_file(), "state.db missing after state phase"

    conn = sqlite3.connect(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM ownership_map").fetchone()[0]
    finally:
        conn.close()

    assert count > 0, "ownership_map should have rows after state phase"


def test_state_phase_does_not_create_ownership_json(tmp_path: Path) -> None:
    """spec-132 D-132-08: no ownership-map.json sidecar on disk."""
    _seed_minimal_install(tmp_path)
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    legacy = tmp_path / ".ai-engineering" / "state" / "ownership-map.json"
    assert not legacy.exists(), (
        f"Legacy ownership-map.json must not exist (spec-132 D-132-08); found at {legacy}"
    )


def test_state_phase_does_not_create_decision_store_json(tmp_path: Path) -> None:
    """spec-132 D-132-08: no decision-store.json sidecar on disk."""
    _seed_minimal_install(tmp_path)
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    legacy = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    assert not legacy.exists(), (
        f"Legacy decision-store.json must not exist (spec-132 D-132-08); found at {legacy}"
    )


def test_state_phase_cleans_up_legacy_ownership_json(tmp_path: Path) -> None:
    """spec-132 D-132-18: pre-existing ownership-map.json is removed."""
    state_dir = _state_dir(tmp_path)
    (state_dir / "ownership-map.json").write_text("{}", encoding="utf-8")
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    legacy = state_dir / "ownership-map.json"
    assert not legacy.exists(), (
        "Pre-existing ownership-map.json should be cleaned up by the state phase"
    )


def test_state_phase_cleans_up_legacy_decision_store_json(tmp_path: Path) -> None:
    """spec-132 D-132-18: pre-existing decision-store.json is removed."""
    state_dir = _state_dir(tmp_path)
    (state_dir / "decision-store.json").write_text("{}", encoding="utf-8")
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    legacy = state_dir / "decision-store.json"
    assert not legacy.exists(), (
        "Pre-existing decision-store.json should be cleaned up by the state phase"
    )
