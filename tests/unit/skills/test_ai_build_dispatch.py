"""ai-build dispatch routing — spec-131 S3 / spec-189 (D-189-04).

Asserts that ``/ai-build`` SKILL.md (and its active IDE mirrors) declare
the cheap/mid/high dispatch routing required by D-131-08. Per spec-189
(D-189-04) ``effort`` is the sole dispatch axis:

* ``effort=cheap`` mentioned in the mechanical (patch-present) branch.
* ``effort=mid`` mentioned in the judgment branch.
* ``effort=high`` mentioned in the deep-architecture override branch.
* The decision matrix names the operator opt-in flag (``--max-effort``)
  and the ``Patch (deterministic):`` plan-side marker so the chain
  between ``/ai-plan`` and ``/ai-build`` is documented end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


# spec-201 D-201-04: skill trees collapse to .claude and .agents only.
_AI_BUILD_MIRRORS = (
    _REPO_ROOT / ".claude" / "skills" / "ai-build" / "SKILL.md",
    _REPO_ROOT / ".agents" / "skills" / "ai-build" / "SKILL.md",
)


_REQUIRED_MARKERS = (
    "effort=cheap",
    "effort=mid",
    "effort=high",
    "Patch (deterministic)",
    "--max-effort",
)


@pytest.mark.unit
@pytest.mark.parametrize("skill_md", _AI_BUILD_MIRRORS, ids=lambda p: p.parts[-3])
@pytest.mark.parametrize("marker", _REQUIRED_MARKERS)
def test_dispatch_marker_present(skill_md: Path, marker: str) -> None:
    """SKILL.md mentions every dispatch marker in the routing block."""
    assert skill_md.is_file(), f"missing mirror: {skill_md}"
    body = skill_md.read_text(encoding="utf-8")
    assert marker in body, f"{skill_md} must mention {marker!r} in the dispatch routing block"


@pytest.mark.unit
@pytest.mark.parametrize("skill_md", _AI_BUILD_MIRRORS, ids=lambda p: p.parts[-3])
def test_effort_levels_named(skill_md: Path) -> None:
    """SKILL.md names the effort vocabulary (cheap / mid / high)."""
    assert skill_md.is_file(), f"missing mirror: {skill_md}"
    body = skill_md.read_text(encoding="utf-8")
    for effort in ("effort=cheap", "effort=mid", "effort=high"):
        assert effort in body, f"{skill_md} missing dispatch effort {effort!r}"


@pytest.mark.unit
@pytest.mark.parametrize("skill_md", _AI_BUILD_MIRRORS, ids=lambda p: p.parts[-3])
def test_skill_remains_within_length_cap(skill_md: Path) -> None:
    """SKILL.md stays within the 120-line ceiling (spec-127 layout)."""
    assert skill_md.is_file(), f"missing mirror: {skill_md}"
    line_count = skill_md.read_text(encoding="utf-8").count("\n")
    # 120 cap + 10% tolerance per pair_aware.LENGTH_TOLERANCE.
    assert line_count <= 132, (
        f"{skill_md} has {line_count} lines; must stay within 132 (cap 120 + 10%)"
    )
