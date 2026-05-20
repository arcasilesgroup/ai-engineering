"""Regression: ``.claude/skills/ai-autopilot/handlers/phase-quality.md`` has
single-round, fail-loud semantics with one bounded remediation pass.

The handler MUST NOT carry any legacy multi-round language. The trim removes the
``round<3`` / ``round = 3`` / ``max 3 rounds`` / ``Round 2`` / ``Round 3``
language and keeps the loop body to one initial assessment, at most one
bounded quality-remediation pass, and one terminal final reassessment.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HANDLER = REPO_ROOT / ".claude" / "skills" / "ai-autopilot" / "handlers" / "phase-quality.md"

# Regex matches any of the legacy multi-round markers.
MULTI_ROUND_RE = re.compile(
    r"round\s*<\s*3"
    r"|round\s*=\s*3"
    r"|max\s*3\s*rounds"
    r"|Round\s*[23]"
    r"|retry\s+more\s+than\s+3\s+rounds",
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def handler_text() -> str:
    if not HANDLER.exists():
        pytest.skip(f"Handler not found at {HANDLER}")
    return HANDLER.read_text()


def test_no_multi_round_language(handler_text: str) -> None:
    matches = MULTI_ROUND_RE.findall(handler_text)
    assert not matches, (
        "phase-quality.md must not reference legacy multi-round retries "
        f"(spec-131 D-131-05 / spec-145 bounded pass); matches: {matches}"
    )


def test_contains_single_round_contract(handler_text: str) -> None:
    assert "single round, fail-loud" in handler_text.lower(), (
        "phase-quality.md must declare the single-round, fail-loud contract."
    )
