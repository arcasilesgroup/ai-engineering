"""Phase 3 RED: architecture-patterns curated list contract (spec-106 G-3).

Asserts the curated patterns context at
``.ai-engineering/contexts/architecture-patterns.md`` lists at least 10
patterns and each pattern entry includes the canonical subsections
(``**When to use**`` and ``**When NOT to use**``) so /ai-plan consumers can
reason about applicability deterministically.

Marked ``spec_106_red``: excluded from the default CI run until Phase 3
lands the curated list and the per-pattern subsection schema.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH_PATTERNS_CONTEXT = REPO_ROOT / ".ai-engineering" / "contexts" / "architecture-patterns.md"

MIN_PATTERN_COUNT = 10


@pytest.mark.spec_106_red
def test_context_file_exists() -> None:
    """Pre-condition: architecture-patterns.md must exist for schema checks."""
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.1: architecture-patterns.md must exist "
        "at .ai-engineering/contexts/architecture-patterns.md."
    )


@pytest.mark.spec_106_red
def test_at_least_ten_pattern_headings() -> None:
    """The context must list >=10 patterns as second-level headings."""
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.5: architecture-patterns.md must list at least "
        f"{MIN_PATTERN_COUNT} patterns (one '## Pattern Name' heading each)."
    )


@pytest.mark.spec_106_red
def test_each_pattern_has_when_to_use_subsection() -> None:
    """Every pattern must include a '**When to use**' subsection."""
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.5: each pattern in architecture-patterns.md "
        "must include a '**When to use**' bullet list so consumers can "
        "reason about applicability."
    )


@pytest.mark.spec_106_red
def test_each_pattern_has_when_not_to_use_subsection() -> None:
    """Every pattern must include a '**When NOT to use**' subsection."""
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.5: each pattern in architecture-patterns.md "
        "must include a '**When NOT to use**' bullet list so consumers can "
        "reject inapplicable patterns explicitly."
    )
