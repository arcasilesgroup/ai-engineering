"""state.db health surface for ``ai-eng doctor --check state-db`` (spec-138 M5.T3).

Connects to ``.ai-engineering/state/state.db``, enumerates the canonical
tables declared by migrations 0001 through 0008 (minus the dropped
``hooks_integrity`` table per spec-138 D-138-01), and prints a structured
report containing:

* table name
* row count
* DB-file ``last_modified`` mtime (ISO-8601 UTC; one mtime per file)
* advisory flag when a rows-expected table is empty (``decisions`` post-M3,
  ``install_steps`` post-installer-run)

The check is informational only. Exit code is always 0 per the spec-138 M5
acceptance gate ("never block"). Operators consume the table via terminal
output; downstream tooling can parse the structured rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Canonical tables created by the migration runner. ``_migrations`` is
# the runner's own ledger (created in ``_runner._ensure_ledger``); the
# rest land via migrations 0001 (``events``, ``decisions``,
# ``risk_acceptances``, ``gate_findings``, ``ownership_map``,
# ``install_steps``), 0004 (``install_state``), and 0005
# (``tool_capabilities``). The legacy ``hooks_integrity`` table was
# dropped in migration 0008 per spec-138 D-138-01.
_CANONICAL_TABLES: tuple[str, ...] = (
    "_migrations",
    "decisions",
    "events",
    "gate_findings",
    "install_state",
    "install_steps",
    "ownership_map",
    "risk_acceptances",
    "tool_capabilities",
)

# Tables that are expected to contain rows once steady-state operation
# kicks in. Empty rows are not a failure (these populate later in the
# operator lifecycle) but become advisory output so operators can spot
# missed backfill / install steps.
_ROWS_EXPECTED_TABLES: frozenset[str] = frozenset({"decisions", "install_steps"})


@dataclass(frozen=True)
class _TableReport:
    """One row in the doctor state-db report."""

    name: str
    row_count: int | None
    last_modified: str
    advisory: str | None


def _format_mtime(db_path: Path) -> str:
    """Return ISO-8601 UTC mtime of the DB file, or ``-`` when absent."""
    if not db_path.exists():
        return "-"
    ts = datetime.fromtimestamp(db_path.stat().st_mtime, tz=UTC)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect_table_reports(project_root: Path) -> list[_TableReport]:
    """Open state.db read-only and tally each canonical table."""
    from ai_engineering.state import state_db

    db_path = state_db.state_db_path(project_root)
    mtime = _format_mtime(db_path)

    if not db_path.exists() or db_path.stat().st_size == 0:
        # No DB yet; surface every canonical table as missing so the
        # operator sees the gap. Bootstrap will create the file on the
        # next write-mode connect; we deliberately avoid triggering it
        # here (doctor is read-only).
        return [
            _TableReport(name=name, row_count=None, last_modified=mtime, advisory="db absent")
            for name in _CANONICAL_TABLES
        ]

    # Read-only connect. Lazy bootstrap is suppressed by the read-only
    # mode so we never mutate the DB while reporting on it.
    conn = state_db.connect(project_root, read_only=True, apply_migrations=False)
    try:
        existing = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        reports: list[_TableReport] = []
        for name in _CANONICAL_TABLES:
            if name not in existing:
                reports.append(
                    _TableReport(
                        name=name,
                        row_count=None,
                        last_modified=mtime,
                        advisory="table missing (migrations not applied?)",
                    )
                )
                continue
            count = int(conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0])
            advisory: str | None = None
            if count == 0 and name in _ROWS_EXPECTED_TABLES:
                advisory = "empty -- rows expected once writer kicks in"
            reports.append(
                _TableReport(
                    name=name,
                    row_count=count,
                    last_modified=mtime,
                    advisory=advisory,
                )
            )
        return reports
    finally:
        conn.close()


def _format_table(reports: list[_TableReport]) -> str:
    """Render the structured table operators read in the terminal."""
    header = f"{'table':<22} {'rows':>8}  {'last_modified':<20}  advisory"
    rows = [header, "-" * len(header)]
    for r in reports:
        rows_value = "-" if r.row_count is None else str(r.row_count)
        advisory = r.advisory or ""
        rows.append(f"{r.name:<22} {rows_value:>8}  {r.last_modified:<20}  {advisory}")
    return "\n".join(rows)


def run_state_db_check(project_root: Path) -> list[_TableReport]:
    """Entry point for ``ai-eng doctor --check state-db``.

    Returns the list of :class:`_TableReport` for downstream test
    inspection. Always exits 0; advisories are printed inline. The
    function never raises on missing tables or missing DB file -- both
    surface as advisories in the report.
    """
    reports = _collect_table_reports(project_root)
    print(_format_table(reports))
    advisories = [r for r in reports if r.advisory]
    if advisories:
        print(
            f"\nADVISORY: {len(advisories)} table(s) flagged "
            "(missing / empty when rows expected). Informational only -- "
            "doctor --check state-db never blocks (spec-138 M5 acceptance gate)."
        )
    return reports


__all__ = ["run_state_db_check"]
