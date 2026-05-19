"""spec-139 M4 — agent description must match canonical quality-loop contract.

The canonical contract at `.claude/skills/ai-autopilot/handlers/phase-quality.md:3`
mandates a single fail-loud quality loop with at most one bounded remediation
pass (spec-131 D-131-05 / spec-145). An agent description that says
"verify+guard+review x3" can be misread by an LLM as license to run 3 rounds,
fanning out to 3 * 16 = 48 agent invocations — exactly the class of regression
that produced the macOS kernel-panic incident documented in
`.ai-engineering/specs/drafts/framework-performance-hardening-brief.md`.

This test forbids the stale strings from reappearing in any mirror surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Every active runtime + mirror surface scanned (Surface Axiom A1).
SURFACES = [
    REPO_ROOT / ".claude",
    REPO_ROOT / ".codex",
    REPO_ROOT / ".gemini",
    REPO_ROOT / ".github",
    REPO_ROOT / ".opencode",
    REPO_ROOT / ".cursor",
    REPO_ROOT / "src" / "ai_engineering" / "templates" / "project",
]

# Patterns that contradict the canonical bounded single-loop contract.
# The U+00D7 MULTIPLICATION SIGN is constructed via ``chr(0x00D7)`` to
# keep the source ASCII-clean (avoiding ruff RUF001 on the ambiguous
# character) while still matching the same code-point at runtime.
_TIMES = chr(0x00D7)
FORBIDDEN_PATTERNS = (
    "verify+guard+review x3",
    f"verify+guard+review {_TIMES}3",
    "review x3",
    f"review {_TIMES}3",
    "3 rounds of verify",
    "three rounds of verify",
)


def _scan_md_files(roots: list[Path]) -> list[Path]:
    """Collect every .md/.mdc file under the surface roots that exists."""
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".mdc"}:
                found.append(path)
    return found


@pytest.mark.parametrize("pattern", FORBIDDEN_PATTERNS)
def test_no_x3_pattern_in_any_surface(pattern: str) -> None:
    """spec-139 M4 / D-139-10 hard rename — no stale 'x3' / multi-round claim."""
    hits: list[str] = []
    for md in _scan_md_files(SURFACES):
        try:
            content = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if pattern in content:
            hits.append(str(md.relative_to(REPO_ROOT)))
    assert not hits, (
        f"Forbidden multi-round pattern {pattern!r} found in: {hits}. "
        "The canonical contract at .claude/skills/ai-autopilot/handlers/phase-quality.md "
        "mandates a single fail-loud loop with at most one bounded remediation pass."
    )
