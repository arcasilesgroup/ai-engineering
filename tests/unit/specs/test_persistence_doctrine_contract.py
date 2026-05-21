"""spec-148 persistence-doctrine contract tests (files-only).

The doctrine must describe the three-tier files-only model: NDJSON audit /
JSON-YAML records+config / Markdown. There is no SQLite tier.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCTRINE = PROJECT_ROOT / "docs" / "persistence-doctrine.md"


def test_doctrine_is_files_only_no_sqlite_tier() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "## The three tiers" in doctrine
    assert "No SQLite anywhere (spec-148 files-only)" in doctrine
    assert "test_no_sqlite.py" in doctrine
    # The retired SQLite tier heading must be gone.
    assert "### Tier 2 — SQLite" not in doctrine
    assert "## The four tiers" not in doctrine


def test_doctrine_names_the_canonical_file_stores() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "decision-store.json" in doctrine
    assert "ownership-map.json" in doctrine
    assert "install-state.json" in doctrine
    assert "framework-capabilities.json" in doctrine
    assert "framework-events.ndjson" in doctrine


def test_gate_findings_json_is_primary_for_gate_risk_verify() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "`.ai-engineering/state/gate-findings.json`" in doctrine
    assert "primary gate/risk/verify artifact" in doctrine


def test_ownership_map_doctrine_is_the_update_source() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "ownership-map.json" in doctrine
    assert "`ai-eng update` reads it" in doctrine
    # No SQLite table claim survives.
    assert "`state.db.ownership_map`" not in doctrine


def test_doctrine_describes_export_migration() -> None:
    doctrine = DOCTRINE.read_text(encoding="utf-8")

    assert "export → verify → delete" in doctrine
    assert "never deleted unless every export verifies" in doctrine
