"""Tests for ``_should_skip_reference_path`` source-repo skip rule
(spec-132 D-132-09).

SKILL.md files contain LLM implementation notes that reference paths
like ``src/ai_engineering/governance/opa_runner.py``. These paths never
ship to consumers, so the validator was emitting false-positive
"broken reference" findings on every fresh install. The fix:
``_should_skip_reference_path`` early-returns ``True`` when the
reference path starts with ``src/ai_engineering/`` AND the origin is a
SKILL.md file (Claude / Copilot / Codex / Gemini skill descriptors).
"""

from __future__ import annotations

import pytest

from ai_engineering.validator.categories.file_existence import _should_skip_reference_path


@pytest.mark.parametrize(
    "origin",
    [
        ".claude/skills/ai-governance/SKILL.md",
        ".github/skills/ai-governance/SKILL.md",
        ".codex/skills/ai-governance/SKILL.md",
        ".gemini/skills/ai-governance/SKILL.md",
    ],
)
def test_src_ai_engineering_skipped_when_origin_is_skill_md(origin: str) -> None:
    """spec-132 D-132-09: source-repo refs from SKILL.md are LLM notes."""
    assert (
        _should_skip_reference_path("src/ai_engineering/governance/opa_runner.py", origin=origin)
        is True
    )


def test_src_ai_engineering_not_skipped_when_origin_unknown() -> None:
    """Without an origin argument, the legacy behaviour holds.

    Pre-existing callers in the validator still pass no ``origin``;
    those refs are evaluated against the filesystem like before. The
    safety net protects regressions for consumer-facing surfaces.
    """
    assert _should_skip_reference_path("src/ai_engineering/governance/opa_runner.py") is False


def test_templates_paths_unchanged_with_origin() -> None:
    """spec-132 D-132-09: only ``src/ai_engineering/`` prefix is special.

    A reference under ``src/ai_engineering/templates/...`` still resolves
    via normal filesystem checks regardless of origin.
    """
    assert (
        _should_skip_reference_path(
            "templates/project/CONSTITUTION.md",
            origin=".claude/skills/ai-build/SKILL.md",
        )
        is False
    )


def test_legacy_skips_still_work_with_origin() -> None:
    """spec-132 D-132-09: pre-existing skip rules still apply with origin set."""
    # Angle-bracket placeholder
    assert (
        _should_skip_reference_path(
            "<placeholder>/foo.md", origin=".claude/skills/ai-build/SKILL.md"
        )
        is True
    )
    # Dollar variable
    assert (
        _should_skip_reference_path("$HOME/.local/bin", origin=".claude/skills/ai-build/SKILL.md")
        is True
    )
