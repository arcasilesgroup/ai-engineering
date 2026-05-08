"""spec-128 T-010 RED test: Surface 6 (lang instructions generator) is gone.

Asserts that ``scripts/sync_mirrors/core.py`` no longer:

1. Defines the ``GITHUB_INSTRUCTIONS`` const
2. Defines the ``CONTEXTS_LANGUAGES`` const
3. Contains a "Surface 6" generation block that mirrors
   ``contexts/languages/<lang>.md`` -> ``.github/instructions/<lang>.instructions.md``
4. Lists ``(GITHUB_INSTRUCTIONS, "glob", "*.instructions.md")`` as an
   orphan-detection surface

Per spec-128 D-128-07: Surface 6 is removed entirely (not redirected).
``.github/instructions/*.instructions.md`` are not generated post-refactor;
``.github/copilot-instructions.md`` (Surface 8) remains as Copilot's baseline.

This test starts RED because Surface 6 still exists in the current code.
Turns GREEN once T-013 deletes the block and consts.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE = _REPO_ROOT / "scripts" / "sync_mirrors" / "core.py"


def test_surface_6_block_absent() -> None:
    """No 'Surface 6' generation block in sync_mirrors/core.py."""
    src = _CORE.read_text(encoding="utf-8")
    # The block has a distinguishing comment per current code style.
    assert "Surface 6" not in src, (
        "scripts/sync_mirrors/core.py still references 'Surface 6'. "
        "spec-128 D-128-07 deletes Surface 6 entirely (lang instructions "
        "generator). Remove the block + comment."
    )


def test_github_instructions_const_absent() -> None:
    """GITHUB_INSTRUCTIONS const removed."""
    src = _CORE.read_text(encoding="utf-8")
    assert not re.search(r"^GITHUB_INSTRUCTIONS\s*=", src, re.MULTILINE), (
        "GITHUB_INSTRUCTIONS const still defined in core.py. "
        "spec-128 deletes .github/instructions/ surface; remove the const."
    )


def test_contexts_languages_const_absent() -> None:
    """CONTEXTS_LANGUAGES const removed."""
    src = _CORE.read_text(encoding="utf-8")
    assert not re.search(r"^CONTEXTS_LANGUAGES\s*=", src, re.MULTILINE), (
        "CONTEXTS_LANGUAGES const still defined in core.py. "
        "spec-128 deletes contexts/languages/ surface; remove the const."
    )


def test_no_orphan_surface_for_instructions() -> None:
    """Orphan-detection surface tuple no longer references instructions glob."""
    src = _CORE.read_text(encoding="utf-8")
    # Pattern: (GITHUB_INSTRUCTIONS, "glob", "*.instructions.md")
    assert "*.instructions.md" not in src, (
        "scripts/sync_mirrors/core.py still references '*.instructions.md'. "
        "spec-128 deletes the .github/instructions/ surface entirely; remove "
        "the orphan-detection entry."
    )


def test_no_lang_instructions_generated_artifacts() -> None:
    """Generated artifacts under .github/instructions/<lang>.instructions.md absent."""
    instructions_dir = _REPO_ROOT / ".github" / "instructions"
    if not instructions_dir.is_dir():
        return  # Already deleted by Phase 5 — vacuous pass.
    lang_files = sorted(
        f
        for f in instructions_dir.glob("*.instructions.md")
        if f.stem not in {"sonarqube_mcp", "testing", "markdown"}
    )
    # Even the 3 standalone files (sonarqube_mcp, testing, markdown) are
    # being deleted per D-128-04, so the strict expectation is empty glob.
    assert lang_files == [], (
        f"spec-128 D-128-04 deletes all .github/instructions/*.instructions.md. "
        f"Still present: {[f.name for f in lang_files]}"
    )
