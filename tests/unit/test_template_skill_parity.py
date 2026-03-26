"""Verify Copilot skill template copies are byte-for-byte identical to root.

The project maintains a three-platform mirror system.  Copilot skill files
live in two locations:

  - Root (canonical): ``.github/skills/ai-*/SKILL.md`` (plus handlers)
  - Template (installed copy): ``src/ai_engineering/templates/project/.github/skills/ai-*/SKILL.md``

Template copies MUST be identical to the canonical root files so that
``ai-eng install`` delivers the exact same skills to downstream projects.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ROOT_SKILLS = _PROJECT_ROOT / ".github" / "skills"
_TEMPLATE_SKILLS = (
    _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".github" / "skills"
)


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 digest for *path*."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _skill_files() -> list[Path]:
    """Collect all markdown files from the canonical root skills directory."""
    files = sorted(f for f in _ROOT_SKILLS.rglob("*.md") if f.is_file())
    assert files, f"No .md files found in {_ROOT_SKILLS}"
    return files


class TestTemplateSkillParity:
    """Every root skill file must have an identical template copy."""

    @pytest.fixture(scope="class")
    def root_skills(self) -> list[Path]:
        return _skill_files()

    # -- Completeness: every root file has a template counterpart -----------

    def test_no_missing_template_copies(self, root_skills: list[Path]) -> None:
        """All root skill files must exist in the template directory."""
        missing = [
            f.relative_to(_ROOT_SKILLS).as_posix()
            for f in root_skills
            if not (_TEMPLATE_SKILLS / f.relative_to(_ROOT_SKILLS)).is_file()
        ]
        assert not missing, f"Template copies missing for {len(missing)} skill file(s): {missing}"

    # -- Content parity: byte-for-byte match via SHA-256 --------------------

    def test_no_divergent_content(self, root_skills: list[Path]) -> None:
        """Template copies must be byte-for-byte identical to the root."""
        divergent: list[str] = []
        for root_file in root_skills:
            rel = root_file.relative_to(_ROOT_SKILLS)
            template_file = _TEMPLATE_SKILLS / rel
            if not template_file.is_file():
                continue  # already caught by test_no_missing_template_copies
            if _sha256(root_file) != _sha256(template_file):
                divergent.append(rel.as_posix())
        assert not divergent, (
            f"Content diverged for {len(divergent)} skill file(s): {divergent}. "
            "Run: python scripts/sync_command_mirrors.py"
        )

    # -- No extra templates without a canonical root file -------------------

    def test_no_orphan_template_files(self, root_skills: list[Path]) -> None:
        """Template dir must not contain skills absent from the root."""
        root_rels = {f.relative_to(_ROOT_SKILLS).as_posix() for f in root_skills}
        orphans = [
            f.relative_to(_TEMPLATE_SKILLS).as_posix()
            for f in sorted(_TEMPLATE_SKILLS.rglob("*.md"))
            if f.is_file() and f.relative_to(_TEMPLATE_SKILLS).as_posix() not in root_rels
        ]
        assert not orphans, f"Orphan template skill file(s) with no root counterpart: {orphans}"

    # -- Parametrized per-file test for granular failure reporting ----------

    @pytest.mark.parametrize(
        "skill_rel",
        [f.relative_to(_ROOT_SKILLS).as_posix() for f in _skill_files()],
        ids=[f.relative_to(_ROOT_SKILLS).as_posix() for f in _skill_files()],
    )
    def test_individual_file_parity(self, skill_rel: str) -> None:
        """Each skill file is individually byte-identical across locations."""
        root_file = _ROOT_SKILLS / skill_rel
        template_file = _TEMPLATE_SKILLS / skill_rel
        assert template_file.is_file(), (
            f"Missing template copy: {template_file.relative_to(_PROJECT_ROOT)}"
        )
        assert _sha256(root_file) == _sha256(template_file), (
            f"Content mismatch for {skill_rel}. Run: python scripts/sync_command_mirrors.py"
        )
