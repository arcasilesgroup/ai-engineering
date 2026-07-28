"""ai-plan template — spec-131 S3 (sub-003 T-3.7 RED).

Asserts that ``/ai-plan`` SKILL.md (and its active IDE mirrors) carry
the exhaustive patch-ready output template required by D-131-08:

* ``Principles applied:`` line per task in the output template.
* ``Patch (deterministic):`` heading or list item in the output
  template (the patch hunk surface).
* At least three distinct §10.x anchors cited as examples so the
  reader knows the citation pattern is plural (§10.3 / §10.5 / §10.7
  are the canonical exemplar trio).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


# spec-201 D-201-04: skill trees collapse to .claude and .agents only.
_AI_PLAN_MIRRORS = (
    _REPO_ROOT / ".claude" / "skills" / "ai-plan" / "SKILL.md",
    _REPO_ROOT / ".agents" / "skills" / "ai-plan" / "SKILL.md",
)


@pytest.mark.unit
@pytest.mark.parametrize("skill_md", _AI_PLAN_MIRRORS, ids=lambda p: p.parts[-3])
def test_principles_applied_line_present(skill_md: Path) -> None:
    """Output template carries a ``Principles applied:`` line per task."""
    assert skill_md.is_file(), f"missing mirror: {skill_md}"
    body = skill_md.read_text(encoding="utf-8")
    assert "Principles applied:" in body, (
        f"{skill_md} must mention 'Principles applied:' in the output template"
    )


@pytest.mark.unit
@pytest.mark.parametrize("skill_md", _AI_PLAN_MIRRORS, ids=lambda p: p.parts[-3])
def test_patch_deterministic_marker_present(skill_md: Path) -> None:
    """Output template carries a ``Patch (deterministic):`` marker."""
    assert skill_md.is_file(), f"missing mirror: {skill_md}"
    body = skill_md.read_text(encoding="utf-8")
    assert "Patch (deterministic):" in body, (
        f"{skill_md} must mention 'Patch (deterministic):' in the output template"
    )


@pytest.mark.unit
@pytest.mark.parametrize("skill_md", _AI_PLAN_MIRRORS, ids=lambda p: p.parts[-3])
def test_three_principle_anchors_cited(skill_md: Path) -> None:
    """At least three §10.x anchors appear in the template prose."""
    assert skill_md.is_file(), f"missing mirror: {skill_md}"
    body = skill_md.read_text(encoding="utf-8")
    found = {anchor for anchor in ("§10.3", "§10.5", "§10.7") if anchor in body}
    assert len(found) >= 3, (
        f"{skill_md} must cite at least §10.3, §10.5, §10.7 as exemplar anchors; "
        f"found {sorted(found)}"
    )
