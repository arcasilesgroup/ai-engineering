"""Phase 3 GREEN: architecture-patterns curated list contract (spec-106 G-3).

Asserts the curated patterns context at
``.ai-engineering/contexts/architecture-patterns.md`` lists the canonical
patterns from D-106-03 and that each entry includes the required subsections
(``**Description**``, ``**When to use**``, ``**When NOT to use**``,
``**Example**``) so /ai-plan consumers can reason about applicability
deterministically.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH_PATTERNS_CONTEXT = REPO_ROOT / ".ai-engineering" / "contexts" / "architecture-patterns.md"

MIN_PATTERN_COUNT = 10
MIN_DESCRIPTION_WORDS = 30
MIN_WHEN_BULLETS = 2
MIN_EXAMPLE_WORDS = 20

# Canonical patterns required by D-106-03. All must appear as h2 headings.
CANONICAL_PATTERNS = (
    "Layered Architecture",
    "Hexagonal Architecture",
    "CQRS",
    "Event Sourcing",
    "Ports and Adapters",
    "Clean Architecture",
    "Pipes and Filters",
    "Repository",
    "Unit of Work",
    "Microservices",
    "Modular Monolith",
)


def _read_context() -> str:
    """Load the architecture-patterns context body."""
    return ARCH_PATTERNS_CONTEXT.read_text(encoding="utf-8")


def _split_into_pattern_sections(body: str) -> dict[str, str]:
    """Split the markdown body into a mapping of pattern name -> section text.

    Each h2 heading (``## Pattern Name``) starts a section. The section text
    runs until the next h2 heading or end-of-file. The intro paragraphs
    before the first h2 are not part of any pattern.
    """
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    for line in body.splitlines():
        h2_match = re.match(r"^## (?!#)(.+)$", line)
        if h2_match:
            if current_name is not None:
                sections[current_name] = "\n".join(current_lines)
            current_name = h2_match.group(1).strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        sections[current_name] = "\n".join(current_lines)
    return sections


def test_context_file_exists() -> None:
    """Pre-condition: architecture-patterns.md must exist for schema checks."""
    assert ARCH_PATTERNS_CONTEXT.exists(), (
        f"missing context: {ARCH_PATTERNS_CONTEXT}. spec-106 Phase 3 T-3.1 "
        f"must create the architecture-patterns.md context."
    )


def test_at_least_ten_pattern_headings() -> None:
    """The context must list at least 10 patterns as second-level headings."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    assert len(sections) >= MIN_PATTERN_COUNT, (
        f"architecture-patterns.md must list at least {MIN_PATTERN_COUNT} "
        f"patterns; found {len(sections)}: {sorted(sections)!r}"
    )


def test_all_canonical_patterns_present() -> None:
    """All 11 canonical patterns from D-106-03 must appear as h2 headings."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    missing = [name for name in CANONICAL_PATTERNS if name not in sections]
    assert not missing, (
        f"architecture-patterns.md is missing canonical patterns: {missing!r}. "
        f"D-106-03 requires all of: {list(CANONICAL_PATTERNS)!r}."
    )


def test_each_pattern_has_description_subsection() -> None:
    """Every pattern must include a `**Description**` subsection."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        assert "**Description**" in text, (
            f"pattern {name!r} missing required '**Description**' subsection"
        )


def test_each_pattern_has_when_to_use_subsection() -> None:
    """Every pattern must include a `**When to use**` subsection."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        assert "**When to use**" in text, (
            f"pattern {name!r} missing required '**When to use**' subsection"
        )


def test_each_pattern_has_when_not_to_use_subsection() -> None:
    """Every pattern must include a `**When NOT to use**` subsection."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        assert "**When NOT to use**" in text, (
            f"pattern {name!r} missing required '**When NOT to use**' subsection"
        )


def test_each_pattern_has_example_subsection() -> None:
    """Every pattern must include a `**Example**` subsection."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        assert "**Example**" in text, f"pattern {name!r} missing required '**Example**' subsection"


def test_description_meets_minimum_word_count() -> None:
    """The description for every pattern must contain at least MIN_DESCRIPTION_WORDS words."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        # Description runs from `**Description**:` to the next `**` heading.
        match = re.search(r"\*\*Description\*\*:(.+?)(?=\n\*\*|\Z)", text, re.DOTALL)
        assert match is not None, f"pattern {name!r} description not parseable"
        description_text = match.group(1).strip()
        word_count = len(description_text.split())
        assert word_count >= MIN_DESCRIPTION_WORDS, (
            f"pattern {name!r} description has {word_count} words; "
            f"minimum is {MIN_DESCRIPTION_WORDS} so consumers have enough context."
        )


def test_when_to_use_has_minimum_bullets() -> None:
    """The `When to use` list for every pattern must have at least MIN_WHEN_BULLETS bullets."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        match = re.search(r"\*\*When to use\*\*:(.+?)(?=\n\*\*|\Z)", text, re.DOTALL)
        assert match is not None, f"pattern {name!r} 'When to use' block not parseable"
        block = match.group(1)
        bullets = [line for line in block.splitlines() if line.strip().startswith("-")]
        assert len(bullets) >= MIN_WHEN_BULLETS, (
            f"pattern {name!r} 'When to use' has {len(bullets)} bullets; "
            f"minimum is {MIN_WHEN_BULLETS}."
        )


def test_when_not_to_use_has_minimum_bullets() -> None:
    """The `When NOT to use` list for every pattern must have at least MIN_WHEN_BULLETS bullets."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        match = re.search(r"\*\*When NOT to use\*\*:(.+?)(?=\n\*\*|\Z)", text, re.DOTALL)
        assert match is not None, f"pattern {name!r} 'When NOT to use' block not parseable"
        block = match.group(1)
        bullets = [line for line in block.splitlines() if line.strip().startswith("-")]
        assert len(bullets) >= MIN_WHEN_BULLETS, (
            f"pattern {name!r} 'When NOT to use' has {len(bullets)} bullets; "
            f"minimum is {MIN_WHEN_BULLETS}."
        )


def test_example_meets_minimum_word_count() -> None:
    """The example for every pattern must contain at least MIN_EXAMPLE_WORDS words."""
    body = _read_context()
    sections = _split_into_pattern_sections(body)
    for name, text in sections.items():
        match = re.search(r"\*\*Example\*\*:(.+?)(?=\n\*\*|\Z)", text, re.DOTALL)
        assert match is not None, f"pattern {name!r} example not parseable"
        example_text = match.group(1).strip()
        word_count = len(example_text.split())
        assert word_count >= MIN_EXAMPLE_WORDS, (
            f"pattern {name!r} example has {word_count} words; "
            f"minimum is {MIN_EXAMPLE_WORDS} so the example is concrete."
        )
