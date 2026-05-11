"""Sections check — exact-string match on the five required level-2 headings.

spec-schema.md §"Required Sections": every spec.md must carry
``## Summary``, ``## Goals``, ``## Non-Goals``, ``## Decisions``, and
``## Risks`` as level-2 headings (exact string match on the heading
text). Optional sections (``## References``, ``## Open Questions``)
never trigger.
"""

from __future__ import annotations

import re
from pathlib import Path

from spec_lint.checks.frontmatter import CheckResult

REQUIRED_SECTIONS = (
    "Summary",
    "Goals",
    "Non-Goals",
    "Decisions",
    "Risks",
)

_HEADING_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def _extract_headings(text: str) -> set[str]:
    """Return the set of level-2 heading texts in ``text`` (raw match)."""
    return set(_HEADING_RE.findall(text))


def check_sections(spec_path: Path) -> list[CheckResult]:
    """Validate that every required level-2 heading is present.

    Emits one ``BLOCKER section_missing`` per missing section. Exact
    string match — ``## Goals!`` or ``##  Goals`` (two spaces) does
    not satisfy the contract.
    """
    text = spec_path.read_text(encoding="utf-8")
    headings = _extract_headings(text)

    results: list[CheckResult] = []
    for required in REQUIRED_SECTIONS:
        if required not in headings:
            results.append(
                CheckResult(
                    "section_missing",
                    "BLOCKER",
                    f"required section '## {required}' is missing or has malformed heading",
                )
            )
    return results
