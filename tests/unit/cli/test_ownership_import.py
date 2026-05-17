"""Spec-138 M3.T5: ``ai-eng ownership import`` parses CODEOWNERS.

The importer reads ``.github/CODEOWNERS`` (or ``--source <path>``) and
UPSERTs each ``<pattern> @owner...`` rule into the canonical
``state.db.ownership_map`` table. Idempotent.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ai_engineering.cli_commands import ownership_cmd
from ai_engineering.state.state_db import state_db_path

_SAMPLE_CODEOWNERS = """# AI Engineering Framework - Code Owners
# Comments are ignored.

# Default rule
*                                    @arcasilesgroup/maintainers

# spec-101 governance: manifest is the SoT
.ai-engineering/manifest.yml         @arcasilesgroup/maintainers

# A user-level owner
docs/                                @docs-team @writer-1
"""


def _seed_codeowners(tmp_path: Path, content: str = _SAMPLE_CODEOWNERS) -> Path:
    """Lay down a synthetic .github/CODEOWNERS file."""
    github_dir = tmp_path / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    path = github_dir / "CODEOWNERS"
    path.write_text(content, encoding="utf-8")
    return path


def _ownership_rows(tmp_path: Path) -> list[tuple[str, str]]:
    db_path = state_db_path(tmp_path)
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT path_pattern, owners_json FROM ownership_map ORDER BY path_pattern"
        ).fetchall()
    finally:
        conn.close()


def test_parse_codeowners_returns_three_rules() -> None:
    """The pure parser yields a row per non-comment rule."""
    rows = ownership_cmd.parse_codeowners(_SAMPLE_CODEOWNERS)
    patterns = sorted(str(r["path_pattern"]) for r in rows)
    # ASCII sort: ``*`` (0x2A) < ``.`` (0x2E) < ``d`` (0x64).
    assert patterns == ["*", ".ai-engineering/manifest.yml", "docs/"]


def test_parse_codeowners_resolves_owner_tokens() -> None:
    """Owner tokens (``@team`` / ``@user``) parse into the row's owners list."""
    rows = ownership_cmd.parse_codeowners(_SAMPLE_CODEOWNERS)
    by_pattern = {str(r["path_pattern"]): r["owners"] for r in rows}
    assert by_pattern["*"] == ["@arcasilesgroup/maintainers"]
    assert by_pattern["docs/"] == ["@docs-team", "@writer-1"]


def test_ownership_import_populates_state_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-138 M3.T5: ownership_map table is non-empty after import."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    rows = _ownership_rows(tmp_path)
    patterns = sorted(p for p, _ in rows)
    assert patterns == ["*", ".ai-engineering/manifest.yml", "docs/"]


def test_ownership_import_stores_owners_as_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owners list lands as a JSON-encoded array in ``owners_json``."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    rows = _ownership_rows(tmp_path)
    by_pattern = {p: json.loads(owners) for p, owners in rows}
    assert by_pattern["docs/"] == ["@docs-team", "@writer-1"]


def test_ownership_import_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-running the import yields the same row set, not duplicates."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    rows = _ownership_rows(tmp_path)
    patterns = [p for p, _ in rows]
    # Three rules, still three rows -- not six.
    assert len(patterns) == 3


def test_ownership_import_missing_file_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing CODEOWNERS file is a no-op; exit 0 and no rows written."""
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    # No .github/CODEOWNERS exists.
    ownership_cmd.ownership_import(source=None, dry_run=False)
    rows = _ownership_rows(tmp_path)
    assert rows == []


def test_ownership_import_respects_source_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--source`` lets operators import a non-default CODEOWNERS path."""
    alt_dir = tmp_path / "custom"
    alt_dir.mkdir(parents=True, exist_ok=True)
    alt = alt_dir / "OWNERS.txt"
    alt.write_text("alt/path  @custom-team\n", encoding="utf-8")
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=str(alt), dry_run=False)
    rows = _ownership_rows(tmp_path)
    patterns = [p for p, _ in rows]
    assert patterns == ["alt/path"]


def test_ownership_import_dry_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run lists the parsed rules but does not UPSERT."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=True)
    rows = _ownership_rows(tmp_path)
    assert rows == []
