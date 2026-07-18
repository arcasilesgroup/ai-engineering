"""spec-187 W4 (T-42, D-187-06): reciprocal skill Integration cross-refs.

A one-way ``## Integration`` cross-reference is a wiring defect: readers of the
un-referenced skill never learn about the relationship. The ai-schema /
ai-security pair was one-way (ai-schema named /ai-security for injection review,
but ai-security never named /ai-schema). This test pins the reciprocity so the
canonical rewrite cannot silently drop one side again.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"


def _integration_section(skill: str) -> str:
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    marker = "## Integration"
    start = text.index(marker) + len(marker)
    rest = text[start:]
    # Up to the next top-level heading (or end of file).
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def test_schema_security_reciprocal() -> None:
    schema_integration = _integration_section("ai-schema")
    security_integration = _integration_section("ai-security")
    assert "/ai-security" in schema_integration, (
        "ai-schema '## Integration' must reference /ai-security"
    )
    assert "/ai-schema" in security_integration, (
        "ai-security '## Integration' must reciprocally reference /ai-schema"
    )
