"""Tests for StatePhase persistence semantics.

Ownership still UPSERTs into ``state.db`` (spec-132 D-132-08; P3 moves it
to a file) and its legacy ``ownership-map.json`` sidecar is still pruned.
spec-148 P2 inverts the decision contract: decisions are files-only, so
the phase WRITES the canonical ``decision-store.json`` and never prunes it.

These tests pin both contracts:

* ``ownership_map`` rows appear and no ``ownership-map.json`` lands.
* ``decision-store.json`` is created (and preserved) by the phase.
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
        surfaces=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
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


def test_state_phase_creates_decision_store_json(tmp_path: Path) -> None:
    """spec-148 P2: the state phase writes the canonical decision-store.json."""
    _seed_minimal_install(tmp_path)
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    assert store_path.is_file(), (
        f"decision-store.json must exist (spec-148 P2 files-only); expected at {store_path}"
    )
    from ai_engineering.state.repository import DurableStateRepository

    # A fresh install seeds an empty (default) store — no decisions yet.
    assert DurableStateRepository(tmp_path).load_decisions().decisions == []


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


def test_state_phase_keeps_decision_store_json(tmp_path: Path) -> None:
    """spec-148 P2: decision-store.json is the SoT — written, never pruned."""
    state_dir = _state_dir(tmp_path)
    (state_dir / "decision-store.json").write_text("{}", encoding="utf-8")
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    store_path = state_dir / "decision-store.json"
    assert store_path.is_file(), (
        "decision-store.json must survive the state phase (spec-148 P2 files-only)"
    )
