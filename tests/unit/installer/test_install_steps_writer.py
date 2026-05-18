"""Spec-138 M3.T4: installer pipeline UPSERTs ``install_steps`` rows.

The pipeline runner records one ``install_steps`` row per phase outcome
(``done`` / ``failed`` / ``non_critical_failure``) so ``ai-eng doctor
--check state-db`` sees a row per phase and forensic queries can replay
what each install did.

These tests exercise the ``upsert_install_step`` helper directly AND
the full ``PipelineRunner.run`` loop with fake phases so the wiring is
asserted end-to-end without going through a real install.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
)
from ai_engineering.installer.phases.pipeline import PipelineRunner
from ai_engineering.state import state_db


class _FakePhase:
    """Minimal ``PhaseProtocol`` impl for runner tests."""

    def __init__(self, name: str, *, passes: bool = True, critical: bool = True) -> None:
        self._name = name
        self._passes = passes
        self.critical = critical

    @property
    def name(self) -> str:
        return self._name

    def plan(self, _context: InstallContext) -> PhasePlan:
        return PhasePlan(phase_name=self._name, actions=[])

    def execute(self, _plan: PhasePlan, _context: InstallContext) -> PhaseResult:
        return PhaseResult(phase_name=self._name, created=[f"created/{self._name}"])

    def verify(self, _result: PhaseResult, _context: InstallContext) -> PhaseVerdict:
        return PhaseVerdict(
            phase_name=self._name,
            passed=self._passes,
            errors=[] if self._passes else [f"{self._name} failed"],
        )


def _state_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".ai-engineering" / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ctx(tmp_path: Path) -> InstallContext:
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        surfaces=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
    )


def _count_rows(db_path: Path, table: str = "install_steps") -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_upsert_install_step_writes_row(tmp_path: Path) -> None:
    """Spec-138 M3.T4: the helper INSERTs a row with the right shape."""
    _state_dir(tmp_path)
    state_db.upsert_install_step(
        tmp_path,
        "detect",
        status="done",
        installed=True,
        authenticated=False,
        integrity_verified=True,
        detail={"created": ["foo"]},
    )
    db_path = state_db.state_db_path(tmp_path)
    assert db_path.is_file()
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT step_id, status, installed, authenticated, integrity_verified "
            "FROM install_steps WHERE step_id = 'detect'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    step_id, status, installed, authenticated, integrity_verified = row
    assert step_id == "detect"
    assert status == "done"
    assert installed == 1
    assert authenticated == 0
    assert integrity_verified == 1


def test_upsert_install_step_is_idempotent(tmp_path: Path) -> None:
    """Re-running UPSERTs in place; the row count stays at 1."""
    _state_dir(tmp_path)
    state_db.upsert_install_step(tmp_path, "detect", status="pending")
    state_db.upsert_install_step(tmp_path, "detect", status="done", installed=True)
    db_path = state_db.state_db_path(tmp_path)
    assert _count_rows(db_path) == 1
    conn = sqlite3.connect(db_path)
    try:
        status, installed = conn.execute(
            "SELECT status, installed FROM install_steps WHERE step_id = 'detect'"
        ).fetchone()
    finally:
        conn.close()
    assert status == "done"
    assert installed == 1


def test_pipeline_runner_records_completed_phases(tmp_path: Path) -> None:
    """spec-138 M3.T4: PipelineRunner.run() writes one row per phase."""
    _state_dir(tmp_path)
    phases = [
        _FakePhase("detect"),
        _FakePhase("governance"),
        _FakePhase("state"),
    ]
    runner = PipelineRunner(phases)
    runner.run(_ctx(tmp_path))

    db_path = state_db.state_db_path(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT step_id, status FROM install_steps ORDER BY step_id").fetchall()
    finally:
        conn.close()
    by_id = dict(rows)
    assert "detect" in by_id
    assert "governance" in by_id
    assert "state" in by_id
    assert by_id["detect"] == "done"
    assert by_id["governance"] == "done"
    assert by_id["state"] == "done"


def test_pipeline_runner_records_failed_phase(tmp_path: Path) -> None:
    """A failed critical phase still writes a row with status='failed'."""
    _state_dir(tmp_path)
    phases = [
        _FakePhase("detect"),
        _FakePhase("governance", passes=False, critical=True),
        _FakePhase("state"),  # never executed
    ]
    runner = PipelineRunner(phases)
    summary = runner.run(_ctx(tmp_path))

    assert summary.failed_phase == "governance"
    assert summary.completed_phases == ["detect"]
    db_path = state_db.state_db_path(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        rows = dict(
            conn.execute("SELECT step_id, status FROM install_steps ORDER BY step_id").fetchall()
        )
    finally:
        conn.close()
    assert rows.get("detect") == "done"
    assert rows.get("governance") == "failed"
    # ``state`` never ran -- no row was UPSERTed for it.
    assert "state" not in rows


def test_pipeline_runner_dry_run_writes_nothing(tmp_path: Path) -> None:
    """Dry-run mode plans only; install_steps stays empty."""
    _state_dir(tmp_path)
    phases = [_FakePhase("detect"), _FakePhase("governance")]
    runner = PipelineRunner(phases)
    runner.run(_ctx(tmp_path), dry_run=True)

    db_path = state_db.state_db_path(tmp_path)
    if not db_path.exists():
        # Dry-run did not even bootstrap state.db -- that is also acceptable.
        return
    assert _count_rows(db_path) == 0
