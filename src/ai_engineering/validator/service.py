"""Content integrity validation service for ai-engineering governance.

Implements programmatic validation of the 7 content-integrity categories:
1. File Existence — verify all internal path references resolve.
2. Mirror Sync — SHA-256 compare canonical vs template mirrors.
3. Counter Accuracy — skill/agent counts match across instruction files and product-contract.
4. Cross-Reference Integrity — bidirectional reference validation.
5. Instruction File Consistency — all 6 instruction files list identical skills/agents.
6. Manifest Coherence — ownership globs match filesystem, active spec valid.
7. Skill Frontmatter — required YAML metadata and requirement schema validity.
"""

from __future__ import annotations

# Re-export everything needed by tests and consumers for backward compatibility.
# Includes re module (used by integration tests that patch patterns).
import re  # noqa: F401
from collections.abc import Callable
from pathlib import Path

from ai_engineering.validator._shared import (
    _PATH_REF_PATTERN,  # noqa: F401 — re-exported for test patching
    FileCache,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _parse_counter,
)
from ai_engineering.validator.categories import (
    _check_counter_accuracy,
    _check_cross_references,
    _check_file_existence,
    _check_instruction_consistency,
    _check_manifest_coherence,
    _check_mirror_sync,
    _check_skill_frontmatter,
)
from ai_engineering.validator.categories.mirror_sync import (
    _check_claude_commands_mirror,
    _check_copilot_agents_mirror,
    _check_copilot_prompts_mirror,
)

__all__ = [
    "IntegrityCategory",
    "IntegrityCheckResult",
    "IntegrityReport",
    "IntegrityStatus",
    "_check_claude_commands_mirror",
    "_check_copilot_agents_mirror",
    "_check_copilot_prompts_mirror",
    "_check_counter_accuracy",
    "_check_cross_references",
    "_check_file_existence",
    "_check_instruction_consistency",
    "_check_manifest_coherence",
    "_check_mirror_sync",
    "_check_skill_frontmatter",
    "_parse_counter",
    "validate_content_integrity",
]


def validate_content_integrity(
    target: Path,
    *,
    categories: list[IntegrityCategory] | None = None,
) -> IntegrityReport:
    """Run content-integrity validation on a project.

    Validates governance content across 7 categories. If *categories* is
    provided, only the specified categories are checked.

    Args:
        target: Project root directory.
        categories: Optional list of categories to check. Defaults to all.

    Returns:
        IntegrityReport with results from all checked categories.
    """
    report = IntegrityReport()
    cache = FileCache()

    checkers: list[tuple[IntegrityCategory, Callable[..., None]]] = [
        (IntegrityCategory.FILE_EXISTENCE, lambda t, r: _check_file_existence(t, r, cache=cache)),
        (IntegrityCategory.MIRROR_SYNC, lambda t, r: _check_mirror_sync(t, r, cache=cache)),
        (IntegrityCategory.COUNTER_ACCURACY, _check_counter_accuracy),
        (
            IntegrityCategory.CROSS_REFERENCE,
            lambda t, r: _check_cross_references(t, r, cache=cache),
        ),
        (IntegrityCategory.INSTRUCTION_CONSISTENCY, _check_instruction_consistency),
        (IntegrityCategory.MANIFEST_COHERENCE, _check_manifest_coherence),
        (
            IntegrityCategory.SKILL_FRONTMATTER,
            lambda t, r: _check_skill_frontmatter(t, r, cache=cache),
        ),
    ]

    active_categories = set(categories) if categories else None

    for category, checker in checkers:
        if active_categories and category not in active_categories:
            continue
        checker(target, report)

    return report
