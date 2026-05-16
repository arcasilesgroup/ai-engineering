"""Structural contract for the `/ai-engineering-issue` skill (spec-134 D-134-02).

`/ai-engineering-issue` files upstream framework bugs against
``arcasilesgroup/ai-engineering``. It is dangerous if misused — it
publishes user-supplied context to a public repo — so the contract
demands:

* strict seven-vector redaction via ``_shared.redactor``,
* a mandatory human-confirmation gate before any ``gh issue create``,
* a sanitized archive copy under ``.ai-engineering/support/upstream-reports/``,
* refusal when ``gh auth status`` is not green.

The tests below pin every load-bearing marker in the SKILL.md body so
the skill body cannot drift away from the contract without a visible
test failure.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_MD = _REPO_ROOT / ".claude" / "skills" / "ai-engineering-issue" / "SKILL.md"
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


@pytest.fixture(scope="module")
def skill_text() -> str:
    assert _SKILL_MD.is_file(), f"SKILL.md missing at {_SKILL_MD}"
    return _SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frontmatter(skill_text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.search(skill_text)
    assert match, "SKILL.md must start with YAML frontmatter"
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
    assert frontmatter.get("name") == "ai-engineering-issue"


@pytest.mark.unit
def test_frontmatter_effort_mid(frontmatter: dict[str, str]) -> None:
    """Filing an upstream bug involves judgment (redaction review, body
    composition) — effort: mid per .ai-engineering/reference/model-dispatch-policy.md
    sonnet-tier rubric."""
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
    assert workflow_match, "SKILL.md must have ## Workflow section"
    body = workflow_match.group("body")
    assert re.search(r"§?10\.[1-8](?!\d)", body), "## Workflow must cite a §10.x principle"


@pytest.mark.unit
@pytest.mark.parametrize(
    "marker",
    [
        "redact",
        "strictness",
        "_shared.redactor",
        "arcasilesgroup/ai-engineering",
        "gh issue create",
        "gh auth status",
        "confirm",
        "human",
        ".ai-engineering/support/upstream-reports",
    ],
)
def test_body_documents_safety_contract(skill_text: str, marker: str) -> None:
    """Body must mention every load-bearing safety marker."""
    assert marker in skill_text, f"SKILL.md must mention {marker!r}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "vector",
    [
        "secret",
        "user-home",
        "email",
        "GitHub token",
        "username",
        "state.db",
        "private path",
    ],
)
def test_body_lists_seven_vectors(skill_text: str, vector: str) -> None:
    """Body must enumerate the seven redaction vectors so reviewers can audit."""
    lower = skill_text.lower()
    assert vector.lower() in lower, f"SKILL.md must enumerate vector {vector!r}"


@pytest.mark.unit
def test_body_under_500_lines(skill_text: str) -> None:
    assert skill_text.count("\n") <= 500, "skill body exceeds 500 lines (D-134-08)"


@pytest.mark.unit
def test_body_ends_with_arguments(skill_text: str) -> None:
    assert skill_text.rstrip().endswith("$ARGUMENTS")


@pytest.mark.unit
def test_tags_mention_redaction_and_upstream(skill_text: str) -> None:
    match = re.search(r"^tags:\s*\[(.*?)\]", skill_text, re.MULTILINE)
    assert match
    tags_text = match.group(1)
    assert "upstream" in tags_text
    assert "redaction" in tags_text or "security" in tags_text
