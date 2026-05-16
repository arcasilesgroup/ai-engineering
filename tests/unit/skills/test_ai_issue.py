"""Structural contract for the `/ai-issue` skill (spec-134 D-134-02).

`/ai-issue` is a thin work-item creation skill that delegates routing
to the manifest's ``work_items.provider``. The tests here pin the
SKILL.md surface — they do not exercise a Python module because the
skill body is the canonical source (skill-creator contract). We assert:

* SKILL.md exists at ``.claude/skills/ai-issue/SKILL.md``.
* Frontmatter declares ``name``, ``description``, ``effort: cheap``,
  ``model_tier: haiku``, ``argument-hint``, ``tags``.
* ``## Workflow`` cites a §10.x engineering anchor.
* Body documents both GitHub and Azure DevOps provider paths.
* Body documents the ``--dry-run`` mode and authentication preconditions.
* Body refuses when manifest ``work_items`` is missing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_MD = _REPO_ROOT / ".claude" / "skills" / "ai-issue" / "SKILL.md"
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


@pytest.fixture(scope="module")
def skill_text() -> str:
    assert _SKILL_MD.is_file(), f"SKILL.md missing at {_SKILL_MD}"
    return _SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frontmatter(skill_text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.search(skill_text)
    assert match, "SKILL.md must start with a YAML frontmatter block"
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


@pytest.mark.unit
def test_skill_md_exists() -> None:
    assert _SKILL_MD.is_file()


@pytest.mark.unit
def test_frontmatter_required_fields(frontmatter: dict[str, str]) -> None:
    """Frontmatter carries the skill-authoring contract fields (D-134-08)."""
    for field in ("name", "description", "effort", "model_tier", "argument-hint"):
        assert field in frontmatter, f"frontmatter missing required field {field!r}"


@pytest.mark.unit
def test_frontmatter_effort_cheap(frontmatter: dict[str, str]) -> None:
    """`/ai-issue` is a thin deterministic wrapper — effort: cheap."""
    assert frontmatter.get("effort") == "cheap"


@pytest.mark.unit
def test_frontmatter_model_tier_haiku(frontmatter: dict[str, str]) -> None:
    """Cheap effort routes to haiku per .ai-engineering/reference/model-dispatch-policy.md."""
    assert frontmatter.get("model_tier") == "haiku"


@pytest.mark.unit
def test_frontmatter_name(frontmatter: dict[str, str]) -> None:
    assert frontmatter.get("name") == "ai-issue"


@pytest.mark.unit
def test_workflow_cites_principle(skill_text: str) -> None:
    """`## Workflow` must cite at least one §10.x engineering anchor."""
    workflow_match = re.search(
        r"^[ \t]*##\s+Workflow\b[^\n]*\n(?P<body>.*?)(?=^[ \t]*##\s|\Z)",
        skill_text,
        re.MULTILINE | re.DOTALL,
    )
    assert workflow_match, "SKILL.md must contain a ## Workflow section"
    assert re.search(r"§?10\.[1-8](?!\d)", workflow_match.group("body")), (
        "## Workflow must cite at least one §10.x principle (D-131-04)"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "marker",
    [
        "work_items",
        "github",
        "azure_devops",
        "gh issue create",
        "az boards work-item create",
        "--dry-run",
        "gh auth status",
    ],
)
def test_body_documents_provider_routing(skill_text: str, marker: str) -> None:
    """Body must document both provider paths plus dry-run + auth preflight."""
    assert marker in skill_text, f"SKILL.md body must mention {marker!r}"


@pytest.mark.unit
def test_body_documents_refusal_on_missing_config(skill_text: str) -> None:
    """Body documents the refusal path when manifest work_items is missing."""
    lower = skill_text.lower()
    assert "missing" in lower and "work_items" in skill_text


@pytest.mark.unit
def test_body_under_500_lines(skill_text: str) -> None:
    """Skill-authoring contract: body must stay ≤500 lines (D-134-08)."""
    assert skill_text.count("\n") <= 500, "SKILL.md must stay within 500 lines"


@pytest.mark.unit
def test_tags_list(skill_text: str) -> None:
    """Tags list must mention work-items routing concept."""
    match = re.search(r"^tags:\s*\[(.*?)\]", skill_text, re.MULTILINE)
    assert match, "frontmatter must declare a `tags:` list"
    tags_text = match.group(1)
    assert "work-items" in tags_text or "work_items" in tags_text


@pytest.mark.unit
def test_body_ends_with_arguments_placeholder(skill_text: str) -> None:
    """All skills terminate with `$ARGUMENTS` so the chat shell can substitute."""
    assert skill_text.rstrip().endswith("$ARGUMENTS"), (
        "SKILL.md must end with the $ARGUMENTS placeholder"
    )
