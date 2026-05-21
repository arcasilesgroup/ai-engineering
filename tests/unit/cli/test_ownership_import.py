"""``ai-eng ownership import`` parses CODEOWNERS (spec-148 P3 files-only).

The importer reads ``.github/CODEOWNERS`` (or ``--source <path>``),
collapses each ``<pattern> @owner...`` rule into an ``OwnershipEntry``
(pattern + ownership level + framework-update policy), and merges it into
the canonical ``ownership-map.json`` by pattern. Idempotent. (Originally
spec-138 M3.T5 against ``state.db.ownership_map``.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.cli_commands import ownership_cmd

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


def _ownership_patterns(tmp_path: Path) -> list[str]:
    """Sorted patterns from the canonical ownership-map.json (empty if absent)."""
    from ai_engineering.state.repository import DurableStateRepository

    store = DurableStateRepository(tmp_path).load_ownership()
    return sorted(entry.pattern for entry in store.paths)


def _ownership_entries(tmp_path: Path) -> dict[str, object]:
    """Map pattern -> OwnershipEntry from the canonical ownership-map.json."""
    from ai_engineering.state.repository import DurableStateRepository

    store = DurableStateRepository(tmp_path).load_ownership()
    return {entry.pattern: entry for entry in store.paths}


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


def test_ownership_import_populates_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """spec-148 P3: ownership-map.json carries an entry per CODEOWNERS rule."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    assert _ownership_patterns(tmp_path) == ["*", ".ai-engineering/manifest.yml", "docs/"]


def test_ownership_import_collapses_owner_to_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-148 P3: each rule collapses to an OwnershipEntry (level + policy).

    CODEOWNERS @team/@user owners are not OwnershipLevel enum values, so
    they collapse to TEAM_MANAGED (matching the prior state.db semantics).
    """
    from ai_engineering.state.models import FrameworkUpdatePolicy, OwnershipLevel

    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    entries = _ownership_entries(tmp_path)
    docs = entries["docs/"]
    assert docs.owner == OwnershipLevel.TEAM_MANAGED
    # No explicit severity in CODEOWNERS -> conservative DENY policy.
    assert docs.framework_update == FrameworkUpdatePolicy.DENY


def test_ownership_import_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-running the import yields the same entries, not duplicates."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    ownership_cmd.ownership_import(source=None, dry_run=False)
    # Three rules, still three entries -- not six.
    assert len(_ownership_patterns(tmp_path)) == 3


def test_ownership_import_missing_file_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing CODEOWNERS file is a no-op; the store file is not written."""
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    # No .github/CODEOWNERS exists -> import bails before touching the store.
    ownership_cmd.ownership_import(source=None, dry_run=False)
    assert not (tmp_path / ".ai-engineering" / "state" / "ownership-map.json").exists()


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
    assert _ownership_patterns(tmp_path) == ["alt/path"]


def test_ownership_import_dry_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run lists the parsed rules but does not write the store file."""
    _seed_codeowners(tmp_path)
    monkeypatch.setattr(ownership_cmd, "find_project_root", lambda: tmp_path)
    ownership_cmd.ownership_import(source=None, dry_run=True)
    assert not (tmp_path / ".ai-engineering" / "state" / "ownership-map.json").exists()
