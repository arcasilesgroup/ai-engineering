"""spec-148 G1 / T-P5.4: no SQLite anywhere (files-only).

The embedded SQLite ``state.db`` was retired in spec-148. This guard
asserts that no framework source module nor any hook imports ``sqlite3``
— EXCEPT the one-shot legacy migration
(``updater/state_db_export.py``), which must read a pre-spec-148
``state.db`` to ingest then delete it.

Replaces the narrower ``test_no_sql_on_hot_path.py`` (which only covered
hot-path hooks): the files-only model forbids ``sqlite3`` across the
whole package and every hook, not just the hot path.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src" / "ai_engineering"
CANONICAL_HOOKS = PROJECT_ROOT / ".ai-engineering" / "scripts" / "hooks"
TEMPLATE_HOOKS = (
    PROJECT_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts" / "hooks"
)

# The SOLE sanctioned sqlite3 reader: the legacy state.db export migration
# (ai-eng update). It reads a pre-spec-148 state.db to ingest + delete it.
_EXEMPT = frozenset({SRC / "updater" / "state_db_export.py"})

_SQLITE_IMPORT = re.compile(r"^[ \t]*(?:import sqlite3|from sqlite3\b)", re.MULTILINE)


def _py_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _offenders(root: Path) -> list[str]:
    found: list[str] = []
    for path in _py_files(root):
        if path in _EXEMPT:
            continue
        if _SQLITE_IMPORT.search(path.read_text(encoding="utf-8")):
            found.append(str(path.relative_to(PROJECT_ROOT)))
    return sorted(found)


def test_no_sqlite_import_in_src() -> None:
    """No framework source imports sqlite3 (except the legacy export migration)."""
    offenders = _offenders(SRC)
    assert not offenders, (
        "spec-148 is files-only — sqlite3 must not be imported in src. "
        f"Offenders: {offenders}. (Only updater/state_db_export.py may read "
        "the legacy state.db, and it is exempt.)"
    )


def test_no_sqlite_import_in_hooks() -> None:
    """No hook (canonical or template mirror) imports sqlite3."""
    offenders = _offenders(CANONICAL_HOOKS) + _offenders(TEMPLATE_HOOKS)
    assert not offenders, f"sqlite3 must not be imported in hooks. Offenders: {sorted(offenders)}"


def test_export_migration_is_the_only_sqlite_reader() -> None:
    """The exemption is real: the migration module imports sqlite3 (sanity check)."""
    migration = SRC / "updater" / "state_db_export.py"
    assert migration.is_file()
    assert _SQLITE_IMPORT.search(migration.read_text(encoding="utf-8")), (
        "the export migration should be the one module that reads the legacy state.db"
    )
