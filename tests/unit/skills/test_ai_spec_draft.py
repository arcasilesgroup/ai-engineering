"""Structural contract for the `/ai-spec-draft` skill (spec-134 D-134-02).

`/ai-spec-draft` is the canonical producer of
``.ai-engineering/specs/drafts/<topic>-brief.md`` artifacts. The brief
shape is the 14-section template documented in the ``## Brief Shape``
section of ``.claude/skills/ai-spec-draft/SKILL.md``.

These tests assert the SKILL.md surface (the canonical source per the
skill-creator contract). Rendered-brief structural assertions live
elsewhere (`tests/unit/specs/test_brief_shape.py` — out of scope for
sub-001).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_MD = _REPO_ROOT / ".claude" / "skills" / "ai-spec-draft" / "SKILL.md"
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


@pytest.fixture(scope="module")
def skill_text() -> str:
    assert _SKILL_MD.is_file(), f"SKILL.md missing at {_SKILL_MD}"
    return _SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frontmatter(skill_text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.search(skill_text)
    assert match
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


@pytest.mark.unit
def test_skill_md_exists() -> None:
    assert _SKILL_MD.is_file()


@pytest.mark.unit
def test_frontmatter_required_fields(frontmatter: dict[str, str]) -> None:
    for field in ("name", "description", "effort", "model_tier", "argument-hint"):
        assert field in frontmatter, f"frontmatter missing {field!r}"


@pytest.mark.unit
def test_frontmatter_name(frontmatter: dict[str, str]) -> None:
    assert frontmatter.get("name") == "ai-spec-draft"


@pytest.mark.unit
def test_frontmatter_effort_mid(frontmatter: dict[str, str]) -> None:
    """Brief authoring involves synthesis judgment — mid tier."""
    assert frontmatter.get("effort") == "mid"


@pytest.mark.unit
def test_frontmatter_model_tier_sonnet(frontmatter: dict[str, str]) -> None:
    assert frontmatter.get("model_tier") == "sonnet"


@pytest.mark.unit
def test_workflow_cites_principle(skill_text: str) -> None:
    workflow_match = re.search(
        r"^[ \t]*##\s+Workflow\b[^\n]*\n(?P<body>.*?)(?=^[ \t]*##\s|\Z)",
        skill_text,
        re.MULTILINE | re.DOTALL,
    )
    assert workflow_match
    body = workflow_match.group("body")
    assert re.search(r"§?10\.[1-8](?!\d)", body), "## Workflow must cite a §10.x principle anchor"


@pytest.mark.unit
@pytest.mark.parametrize(
    "section",
    [
        "Vision",
        "Scope Boundary",
        "Diagnostic Snapshot",
        "Architecture",
        "Evidence Catalog",
        "Roadmap",
        "Definition of Done",
        "Quality Stamps",
        "Open Decisions",
        "Migration",
        "Risks",
        "References",
        "Glossary",
        "Acceptance",
    ],
)
def test_body_describes_14_sections(skill_text: str, section: str) -> None:
    """Body documents every canonical brief section so the operator knows the shape."""
    assert section in skill_text, f"SKILL.md must mention canonical section {section!r}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "marker",
    [
        ".ai-engineering/specs/drafts/",
        "file:line",
        "/ai-brainstorm",
        "/ai-explore",
        "/ai-research",
    ],
)
def test_body_documents_integration(skill_text: str, marker: str) -> None:
    """Body must document the upstream brief location, citation contract, and handoff."""
    assert marker in skill_text, f"SKILL.md must mention {marker!r}"


@pytest.mark.unit
def test_body_under_500_lines(skill_text: str) -> None:
    assert skill_text.count("\n") <= 500


@pytest.mark.unit
def test_body_ends_with_arguments(skill_text: str) -> None:
    assert skill_text.rstrip().endswith("$ARGUMENTS")


@pytest.mark.unit
def test_tags_mention_planning_and_research(skill_text: str) -> None:
    match = re.search(r"^tags:\s*\[(.*?)\]", skill_text, re.MULTILINE)
    assert match
    tags_text = match.group(1).lower()
    assert "planning" in tags_text
    assert "brief" in tags_text or "research" in tags_text


@pytest.mark.unit
def test_workflow_documents_minimum_citations(skill_text: str) -> None:
    """Brief contract requires ≥5 `file:line` citations — the skill must declare it."""
    assert "≥5" in skill_text or "at least 5" in skill_text.lower() or "5 file:line" in skill_text
