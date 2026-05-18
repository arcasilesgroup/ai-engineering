"""Tests for ``ai-eng doctor --check state-db`` (spec-138 M5.T3).

The state-db sub-check connects to ``.ai-engineering/state/state.db``,
enumerates the canonical tables, and prints a structured report with
row counts, last_modified mtime, and advisory flags for rows-expected
empty tables (``decisions``, ``install_steps``).

Always exits 0 per spec-138 M5 acceptance gate (informational only;
never blocks).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner


@pytest.fixture()
def app() -> typer.Typer:
    from ai_engineering.cli_factory import create_app

    return create_app()


@pytest.fixture()
def fresh_project(tmp_path: Path) -> Path:
    """Tmp project root with the state directory present but no state.db."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _bootstrap_state_db(project_root: Path) -> None:
    """Force-create state.db with every migration applied."""
    from ai_engineering.state import state_db

    conn = state_db.connect(project_root)
    conn.close()


# ---------------------------------------------------------------------------
# Happy-path: fresh DB with every canonical table reported.
# ---------------------------------------------------------------------------


class TestDoctorCheckStateDb:
    def test_doctor_check_state_db_reports_canonical_tables(
        self, app: typer.Typer, fresh_project: Path
    ) -> None:
        """Bootstrap creates the DB; the report lists every canonical table."""
        _bootstrap_state_db(fresh_project)

        result = CliRunner().invoke(app, ["doctor", "--check", "state-db", str(fresh_project)])

        assert result.exit_code == 0, result.output
        # Structured table headers must appear so operators can grep output.
        for header in ("table", "rows", "last_modified", "advisory"):
            assert header in result.output, f"missing column header {header}: {result.output}"
        # Every canonical table must show up in the report. The legacy
        # ``hooks_integrity`` table was dropped in migration 0008 per
        # spec-138 D-138-01 and must NOT appear.
        for name in (
            "_migrations",
            "decisions",
            "events",
            "gate_findings",
            "install_state",
            "install_steps",
            "ownership_map",
            "risk_acceptances",
            "tool_capabilities",
        ):
            assert name in result.output, f"missing table {name}: {result.output}"
        assert "hooks_integrity" not in result.output

    def test_doctor_check_state_db_flags_empty_decisions(
        self, app: typer.Typer, fresh_project: Path
    ) -> None:
        """``decisions`` and ``install_steps`` are empty on a fresh DB --
        the report must flag them as advisory."""
        _bootstrap_state_db(fresh_project)

        result = CliRunner().invoke(app, ["doctor", "--check", "state-db", str(fresh_project)])

        assert result.exit_code == 0, result.output
        assert "ADVISORY" in result.output
        # Both rows-expected tables should call out their empty state.
        # The exact phrasing comes from doctor_state_db._collect_table_reports.
        assert "empty" in result.output.lower()

    def test_doctor_check_state_db_exits_zero_when_db_absent(
        self, app: typer.Typer, fresh_project: Path
    ) -> None:
        """Missing state.db file produces an informational report,
        exits 0 (never blocks)."""
        # Deliberately do NOT call _bootstrap_state_db -- the DB stays absent.
        db_path = fresh_project / ".ai-engineering" / "state" / "state.db"
        if db_path.exists():
            db_path.unlink()

        result = CliRunner().invoke(app, ["doctor", "--check", "state-db", str(fresh_project)])

        assert result.exit_code == 0, result.output
        # Missing DB surfaces every canonical table with an advisory.
        assert "db absent" in result.output or "ADVISORY" in result.output

    def test_doctor_check_state_db_rejects_unknown_check_value(
        self, app: typer.Typer, fresh_project: Path
    ) -> None:
        """Sanity: unknown --check value still raises BadParameter."""
        _bootstrap_state_db(fresh_project)

        result = CliRunner().invoke(
            app, ["doctor", "--check", "not-a-real-check", str(fresh_project)]
        )

        assert result.exit_code != 0
        # Confirm the supported values are listed (so the new addition
        # propagates into the error string).
        assert "state-db" in result.output

    def test_run_state_db_check_returns_reports(self, fresh_project: Path) -> None:
        """Direct entry point returns the structured report rows."""
        from ai_engineering.cli_commands.doctor_state_db import run_state_db_check

        _bootstrap_state_db(fresh_project)
        reports = run_state_db_check(fresh_project)

        names = {r.name for r in reports}
        assert "events" in names
        assert "decisions" in names
        # Hard contract: the dropped table is absent from the report.
        assert "hooks_integrity" not in names
        # Empty decisions on a fresh DB must carry an advisory.
        decisions = next(r for r in reports if r.name == "decisions")
        assert decisions.row_count == 0
        assert decisions.advisory is not None
