"""Non-Goals check — fails when ``## Non-Goals`` is empty.

spec-schema.md validation rule §3: "Non-Goals must contain at least
one item." A whitespace-only or placeholder-only section counts as
empty; both numbered (``1. **No X.**``) and bulleted (``- No X.``)
shapes are accepted.
"""

from __future__ import annotations

import re
from pathlib import Path

from spec_lint.checks.decisions import _slice_section
from spec_lint.checks.frontmatter import CheckResult

# Either ``- foo`` or ``1. foo`` is accepted as a list item. The trailing
# ``\S`` guard rejects empty markers and whitespace-only bodies.
_ITEM_RE = re.compile(r"^(?:\d+\.|\-)\s+\S")


def check_non_goals(spec_path: Path) -> list[CheckResult]:
    """Validate that ``## Non-Goals`` contains at least one list item.

    Emits a single ``BLOCKER non_goals_empty`` when no list item is
    present in the section body.
    """
    text = spec_path.read_text(encoding="utf-8")
    block = _slice_section(text, "Non-Goals")
    if not block:
        # No section — sections.py is responsible for surfacing that
        # blocker. non_goals.py stays quiet.
        return []

    for line in block:
        if _ITEM_RE.match(line):
            return []

    return [
        CheckResult(
            "non_goals_empty",
            "BLOCKER",
            "## Non-Goals section must contain at least one list item (bulleted or numbered)",
        )
    ]
