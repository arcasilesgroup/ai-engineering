"""Tests for skill schema validation — ensures all skills on disk have valid structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.lib.parsing import parse_frontmatter

pytestmark = pytest.mark.unit

_SKILLS_DIR = Path(__file__).resolve().parents[2] / ".ai-engineering" / "skills"
_REQUIRED_FIELDS = {"name"}


def _all_skill_dirs() -> list[Path]:
    """Return all skill directories that contain SKILL.md."""
    if not _SKILLS_DIR.is_dir():
        return []
    return sorted(d for d in _SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


@pytest.mark.parametrize("skill_dir", _all_skill_dirs(), ids=lambda d: d.name)
def test_skill_has_valid_frontmatter(skill_dir: Path) -> None:
    """Every SKILL.md must have YAML frontmatter with a 'name' field."""
    skill_file = skill_dir / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")

    # Must start with ---
    assert text.startswith("---"), f"{skill_dir.name}/SKILL.md missing frontmatter"

    fm = parse_frontmatter(text)
    for field in _REQUIRED_FIELDS:
        assert fm.get(field), f"{skill_dir.name}/SKILL.md missing '{field}' in frontmatter"


@pytest.mark.parametrize("skill_dir", _all_skill_dirs(), ids=lambda d: d.name)
def test_skill_not_truncated(skill_dir: Path) -> None:
    """No skill should be under 30 lines (truncation indicator)."""
    skill_file = skill_dir / "SKILL.md"
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    name = skill_dir.name
    assert len(lines) >= 30, f"{name}/SKILL.md only {len(lines)} lines"


def test_skill_count_matches_manifest() -> None:
    """Skill count on disk must match manifest.yml governance_surface.skills.total."""
    import yaml

    # Arrange — read expected count from manifest (single source of truth)
    manifest_path = _SKILLS_DIR.parent / "manifest.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    expected = manifest["governance_surface"]["skills"]["total"]

    # Act
    skills = _all_skill_dirs()

    # Assert
    assert len(skills) == expected, (
        f"Manifest says {expected} skills, found {len(skills)} on disk: {[d.name for d in skills]}"
    )
