"""Tests for StatePhase persistence semantics (spec-148 P2/P3 files-only).

Both ownership and decisions are files-only: the state phase WRITES the
canonical ``ownership-map.json`` and ``decision-store.json`` and never
prunes them.

These tests pin the contract:

* ``ownership-map.json`` is created (with entries) and preserved.
* ``decision-store.json`` is created (default empty) and preserved.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.installer.phases import InstallContext, InstallMode
from ai_engineering.installer.phases.state import StatePhase


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


def test_state_phase_writes_ownership_map_json(tmp_path: Path) -> None:
    """spec-148 P3: ownership-map.json is populated post-execute."""
    _seed_minimal_install(tmp_path)
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    from ai_engineering.state.repository import DurableStateRepository

    store_path = tmp_path / ".ai-engineering" / "state" / "ownership-map.json"
    assert store_path.is_file(), "ownership-map.json must exist after the state phase (spec-148 P3)"
    assert DurableStateRepository(tmp_path).load_ownership().paths, (
        "ownership-map.json should carry the default ownership entries"
    )


def test_state_phase_ownership_map_parses_as_model(tmp_path: Path) -> None:
    """spec-148 P3: the written ownership-map.json round-trips the model."""
    _seed_minimal_install(tmp_path)
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    from ai_engineering.state.io import read_json_model
    from ai_engineering.state.models import OwnershipMap

    store_path = tmp_path / ".ai-engineering" / "state" / "ownership-map.json"
    ownership = read_json_model(store_path, OwnershipMap)
    assert all(entry.pattern for entry in ownership.paths)


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


def test_state_phase_keeps_ownership_map_json(tmp_path: Path) -> None:
    """spec-148 P3: ownership-map.json is the SoT — written, never pruned."""
    state_dir = _state_dir(tmp_path)
    (state_dir / "ownership-map.json").write_text("{}", encoding="utf-8")
    phase = StatePhase()
    ctx = _ctx(tmp_path)
    phase.execute(phase.plan(ctx), ctx)

    store_path = state_dir / "ownership-map.json"
    assert store_path.is_file(), (
        "ownership-map.json must survive the state phase (spec-148 P3 files-only)"
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
