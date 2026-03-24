"""Verify Copilot prompt template copies are byte-for-byte identical to root.

The project maintains a three-platform mirror system.  Copilot prompt files
live in two locations:

  - Root (canonical): ``.github/prompts/ai-*.prompt.md``
  - Template (installed copy): ``src/ai_engineering/templates/project/prompts/ai-*.prompt.md``

Template copies MUST be identical to the canonical root files so that
``ai-eng install`` delivers the exact same prompts to downstream projects.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ROOT_PROMPTS = _PROJECT_ROOT / ".github" / "prompts"
_TEMPLATE_PROMPTS = _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / "project" / "prompts"


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 digest for *path*."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prompt_files() -> list[Path]:
    """Collect all ``*.prompt.md`` files from the canonical root directory."""
    files = sorted(_ROOT_PROMPTS.glob("*.prompt.md"))
    assert files, f"No .prompt.md files found in {_ROOT_PROMPTS}"
    return files


class TestTemplatePromptParity:
    """Every root prompt file must have an identical template copy."""

    @pytest.fixture(scope="class")
    def root_prompts(self) -> list[Path]:
        return _prompt_files()

    # -- Completeness: every root file has a template counterpart -----------

    def test_no_missing_template_copies(self, root_prompts: list[Path]) -> None:
        """All root prompt files must exist in the template directory."""
        missing = [f.name for f in root_prompts if not (_TEMPLATE_PROMPTS / f.name).is_file()]
        assert not missing, f"Template copies missing for {len(missing)} prompt(s): {missing}"

    # -- Content parity: byte-for-byte match via SHA-256 --------------------

    def test_no_divergent_content(self, root_prompts: list[Path]) -> None:
        """Template copies must be byte-for-byte identical to the root."""
        divergent: list[str] = []
        for root_file in root_prompts:
            template_file = _TEMPLATE_PROMPTS / root_file.name
            if not template_file.is_file():
                continue  # already caught by test_no_missing_template_copies
            if _sha256(root_file) != _sha256(template_file):
                divergent.append(root_file.name)
        assert not divergent, (
            f"Content diverged for {len(divergent)} prompt(s): {divergent}. "
            "Run: python scripts/sync_command_mirrors.py"
        )

    # -- No extra templates without a canonical root file -------------------

    def test_no_orphan_template_files(self, root_prompts: list[Path]) -> None:
        """Template dir must not contain prompts absent from the root."""
        root_names = {f.name for f in root_prompts}
        orphans = [
            f.name
            for f in sorted(_TEMPLATE_PROMPTS.glob("*.prompt.md"))
            if f.name not in root_names
        ]
        assert not orphans, f"Orphan template prompt(s) with no root counterpart: {orphans}"

    # -- Parametrized per-file test for granular failure reporting ----------

    @pytest.mark.parametrize(
        "prompt_name",
        [f.name for f in _prompt_files()],
        ids=[f.stem for f in _prompt_files()],
    )
    def test_individual_file_parity(self, prompt_name: str) -> None:
        """Each prompt file is individually byte-identical across locations."""
        root_file = _ROOT_PROMPTS / prompt_name
        template_file = _TEMPLATE_PROMPTS / prompt_name
        assert template_file.is_file(), (
            f"Missing template copy: {template_file.relative_to(_PROJECT_ROOT)}"
        )
        assert _sha256(root_file) == _sha256(template_file), (
            f"Content mismatch for {prompt_name}. Run: python scripts/sync_command_mirrors.py"
        )
