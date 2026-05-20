"""Spec-146 persistence-doctrine contract tests.

The doctrine must classify each ``state.db`` surface by role instead of
calling the whole database a replayable projection.  Gate findings remain
JSON-primary in this spec; the SQLite table is only transitional.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATE_DB = PROJECT_ROOT / "src" / "ai_engineering" / "state" / "state_db.py"
DOCTRINE = PROJECT_ROOT / "docs" / "persistence-doctrine.md"


def _state_db_docstring() -> str:
    return ast.get_docstring(ast.parse(STATE_DB.read_text(encoding="utf-8"))) or ""


def test_state_db_docstring_describes_mixed_lifecycle_database() -> None:
    docstring = _state_db_docstring()

    assert "mixed lifecycle database" in docstring
    assert "state.db.events" in docstring
    assert "NDJSON-derived cache" in docstring
    assert "gate_findings" in docstring
    assert "non-primary placeholder" in docstring
    assert "this DB is a derived projection that can be rebuilt by replay" not in docstring


def test_persistence_doctrine_classifies_state_db_tables_by_role() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "| `decisions` | mixed lifecycle/cache" in doctrine
    assert "| `risk_acceptances` | canonical lifecycle" in doctrine
    assert "| `ownership_map` | canonical lifecycle" in doctrine
    assert "| `install_steps` | canonical lifecycle" in doctrine
    assert "| `events` | derived cache" in doctrine
    assert "| `gate_findings` | transitional placeholder" in doctrine
    assert "stateful lifecycle data — decisions" not in doctrine


def test_gate_findings_json_is_primary_for_gate_risk_verify() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "`.ai-engineering/state/gate-findings.json`" in doctrine
    assert "primary gate/risk/verify artifact" in doctrine
    assert "`state.db.gate_findings`" in doctrine
    assert "non-primary placeholder/transitional" in doctrine


def test_ownership_map_doctrine_uses_sqlite_as_update_source() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "`state.db.ownership_map`" in doctrine
    assert "`ai-eng update` reads this table" in doctrine
    assert "one-time legacy `ownership-map.json` fallback" in doctrine
    assert "operator-provided `ownership-map.json` (Tier 3 / 4)" not in doctrine
