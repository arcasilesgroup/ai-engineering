"""Tests for ``pr_body_compose.py`` (brief §17)."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / ".ai-engineering" / "scripts"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pr_body_compose  # noqa: E402


def _write_spec(tmp_path: Path, frontmatter_yaml: str) -> Path:
    spec = tmp_path / "spec.md"
    spec.write_text(f"---\n{frontmatter_yaml}\n---\n\n# Spec body\n", encoding="utf-8")
    return spec


def _write_plan(tmp_path: Path, lines: list[str]) -> Path:
    plan = tmp_path / "plan.md"
    plan.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return plan


@pytest.mark.unit
def test_all_sections_present(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        textwrap.dedent(
            """\
            id: 127
            title: Excellence Refactor
            summary:
              - Adopts hexagonal layout
              - Introduces conformance rubric
            refs:
              user_stories: ["AB#101"]
              tasks: ["AB#102"]
            """
        ).strip(),
    )
    plan = _write_plan(
        tmp_path,
        [
            "- [x] Done: kickoff",
            "- [ ] Wire skill_lint --check",
            "- [ ] Add rubric tests",
        ],
    )
    body = pr_body_compose.compose_body(spec_path=spec, plan_path=plan)
    assert "## Summary" in body
    assert "## Test Plan" in body
    assert "## Work Items" in body
    assert "## Checklist" in body


@pytest.mark.unit
def test_summary_uses_frontmatter_bullets(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        textwrap.dedent(
            """\
            id: 127
            title: Refactor
            summary:
              - Bullet A
              - Bullet B
            """
        ).strip(),
    )
    plan = _write_plan(tmp_path, ["- [ ] task one"])
    body = pr_body_compose.compose_body(spec_path=spec, plan_path=plan)
    assert "- Bullet A" in body
    assert "- Bullet B" in body


@pytest.mark.unit
def test_test_plan_lists_unchecked_tasks(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path, "id: 1\ntitle: Test")
    plan = _write_plan(
        tmp_path,
        [
            "- [x] already done",
            "- [ ] still open one",
            "- [ ] still open two",
        ],
    )
    body = pr_body_compose.compose_body(spec_path=spec, plan_path=plan)
    assert "still open one" in body
    assert "still open two" in body
    assert "already done" not in body  # checked tasks excluded


@pytest.mark.unit
def test_work_items_renders_closes(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        textwrap.dedent(
            """\
            id: 127
            title: T
            refs:
              tasks: ["AB#102", "AB#103"]
              issues: ["#45"]
              features: ["AB#100"]
            """
        ).strip(),
    )
    plan = _write_plan(tmp_path, ["- [ ] x"])
    body = pr_body_compose.compose_body(spec_path=spec, plan_path=plan)
    assert "Closes AB#102" in body
    assert "Closes AB#103" in body
    assert "Closes #45" in body
    # Features must NEVER be auto-closed.
    assert "Related: AB#100" in body
    assert "Closes AB#100" not in body


@pytest.mark.unit
def test_bullets_prompt_overrides_frontmatter(tmp_path: Path) -> None:
    spec = _write_spec(
        tmp_path,
        textwrap.dedent(
            """\
            id: 1
            title: T
            summary:
              - From frontmatter
            """
        ).strip(),
    )
    plan = _write_plan(tmp_path, ["- [ ] x"])
    body = pr_body_compose.compose_body(
        spec_path=spec,
        plan_path=plan,
        bullets_prompt="- LLM-supplied bullet",
    )
    assert "- LLM-supplied bullet" in body
    assert "From frontmatter" not in body
