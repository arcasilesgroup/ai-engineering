"""Architecture: persistence doctrine landed and cited (spec-138 M2).

Asserts the SSOT-PD doctrine document exists, carries the canonical
section headers, and the project-identity surfaces (CONSTITUTION.md +
CLAUDE.md §0) cite it correctly. Drift fails CI.

Why this test exists: the silent dual-write failure mode closed by
spec-138 M1 could only land if the framework had a written rule that
"every datum has exactly one canonical store". The rule lives in
`docs/persistence-doctrine.md` and is referenced from the project's
identity contract (CONSTITUTION.md §13) and the cross-IDE bootstrap
(CLAUDE.md §0). This test pins all three citations so a future
operator cannot silently delete the doctrine without breaking the
identity contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCTRINE = _REPO_ROOT / "docs" / "persistence-doctrine.md"
_CONSTITUTION = _REPO_ROOT / "CONSTITUTION.md"
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"


# The five canonical section headers authored in spec-138 M2.T1.
# Test asserts on the *literal* heading text the doctrine file ships
# with so renaming a section is a deliberate, reviewable edit.
_REQUIRED_HEADERS = (
    "## The SSOT-PD rule",
    "## The four tiers",
    "## Derived caches",
    "## Strict rules",
    "## Operator surface — what changes for you",
    "## Glossary",
)


@pytest.mark.unit
def test_persistence_doctrine_file_exists() -> None:
    """`docs/persistence-doctrine.md` MUST be present at the canonical path."""
    assert _DOCTRINE.exists(), (
        f"Persistence doctrine missing at {_DOCTRINE.relative_to(_REPO_ROOT)}. "
        "spec-138 M2.T1 ships this file — re-author or restore from git history."
    )
    assert _DOCTRINE.stat().st_size > 0, "Doctrine file is empty"


@pytest.mark.unit
@pytest.mark.parametrize("header", _REQUIRED_HEADERS)
def test_persistence_doctrine_has_required_section(header: str) -> None:
    """Every canonical section header MUST be present in the doctrine."""
    text = _DOCTRINE.read_text(encoding="utf-8")
    assert header in text, (
        f"Persistence doctrine missing required section header: {header!r}. "
        "spec-138 M2.T1 fixes the section structure; renaming requires an ADR."
    )


@pytest.mark.unit
def test_constitution_cites_persistence_doctrine() -> None:
    """CONSTITUTION.md MUST carry the SSOT-PD hard rule citing the doctrine."""
    text = _CONSTITUTION.read_text(encoding="utf-8")
    assert "Single Source of Truth Per Datum" in text, (
        "CONSTITUTION.md missing the SSOT-PD hard rule. "
        "spec-138 M2.T2 adds it under the Prohibitions list."
    )
    assert "docs/persistence-doctrine.md" in text, (
        "CONSTITUTION.md missing the docs/persistence-doctrine.md citation. "
        "The hard rule MUST link the doctrine for navigability."
    )


@pytest.mark.unit
def test_claude_md_bootstrap_points_at_doctrine() -> None:
    """CLAUDE.md §0 Bootstrap MUST point at the persistence doctrine."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    # Find the §0 Bootstrap section bounds.
    bootstrap_marker = "## 0. Bootstrap"
    assert bootstrap_marker in text, "CLAUDE.md missing §0 Bootstrap section"
    bootstrap_start = text.index(bootstrap_marker)
    # Next section header marks the end of §0.
    next_section_idx = text.index("\n## ", bootstrap_start + len(bootstrap_marker))
    bootstrap_block = text[bootstrap_start:next_section_idx]
    assert "docs/persistence-doctrine.md" in bootstrap_block, (
        "CLAUDE.md §0 Bootstrap missing pointer to docs/persistence-doctrine.md. "
        "spec-138 M2.T3 replaces the broken state.db.decisions query "
        "instruction with a doctrine pointer."
    )


@pytest.mark.unit
def test_claude_md_carries_ssot_pd_hard_rule() -> None:
    """CLAUDE.md §13 Hard Rules MUST include the SSOT-PD rule."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    assert "Single Source of Truth Per Datum" in text, (
        "CLAUDE.md missing the SSOT-PD hard rule under §13. "
        "Mirror sync from CANONICAL.md is required after spec-138 M2.T2."
    )
