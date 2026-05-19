"""Regression: ``/ai-branch-cleanup`` SKILL.md documents the ``_history.md`` rotation
step (spec-131 D-131-05 acceptance criterion).

The actual rotation lives in ``.ai-engineering/scripts/spec_lifecycle.py
mark_shipped``; this skill is a verification-only documentation surface
that points operators at the entry point. The canonical SKILL.md plus the
three IDE mirrors are all checked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CLEANUP_SKILL_FILES = (
    REPO_ROOT / ".claude" / "skills" / "ai-branch-cleanup" / "SKILL.md",
    REPO_ROOT / ".github" / "skills" / "ai-branch-cleanup" / "SKILL.md",
    REPO_ROOT / ".codex" / "skills" / "ai-branch-cleanup" / "SKILL.md",
    REPO_ROOT / ".gemini" / "skills" / "ai-branch-cleanup" / "SKILL.md",
)

REQUIRED_SUBSTRINGS = (
    "_history.md",
    "spec_lifecycle.py mark_shipped",
)


@pytest.mark.parametrize(
    "path", CLEANUP_SKILL_FILES, ids=[str(p.relative_to(REPO_ROOT)) for p in CLEANUP_SKILL_FILES]
)
def test_cleanup_skill_documents_history_rotation(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"SKILL.md not found at {path}")
    text = path.read_text()
    for substring in REQUIRED_SUBSTRINGS:
        assert substring in text, (
            f"{path.relative_to(REPO_ROOT)} must mention '{substring}' "
            "(spec-131 D-131-05 acceptance: explicit _history.md rotation step)."
        )


@pytest.mark.parametrize(
    "path", CLEANUP_SKILL_FILES, ids=[str(p.relative_to(REPO_ROOT)) for p in CLEANUP_SKILL_FILES]
)
def test_cleanup_skill_has_spec_consolidation_heading(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"SKILL.md not found at {path}")
    text = path.read_text()
    # Phase heading is permissive: either explicit phase id or a heading
    # mentioning "spec consolidation".
    assert "Spec consolidation" in text, (
        f"{path.relative_to(REPO_ROOT)} must contain a 'Spec consolidation' "
        "heading or row that documents the _history.md rotation."
    )
