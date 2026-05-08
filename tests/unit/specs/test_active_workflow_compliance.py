"""CI guard for spec-123 T-7.4 + Article XIII: active spec workflow contract.

Article XIII codifies the single canonical spec lifecycle:

    /ai-brainstorm -> /ai-plan -> /ai-build | /ai-autopilot -> /ai-pr
    (post spec-127 D-127-11 — `/ai-dispatch` renamed to `/ai-build`).

This test asserts:

1. CONSTITUTION.md contains the Article XIII title.
2. Each lifecycle skill exists at its canonical path.
3. Each skill that touches `specs/` references the canonical resolver
   path `.ai-engineering/specs/spec.md` (not legacy `specs/spec.md`).

The test is intentionally narrow: it only verifies the surface contract
(article exists + skills exist + canonical path used). Workflow semantics
are enforced by the skill bodies themselves.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONSTITUTION = PROJECT_ROOT / "CONSTITUTION.md"
SKILLS_ROOT = PROJECT_ROOT / ".claude" / "skills"

LIFECYCLE_SKILLS = (
    "ai-brainstorm",
    "ai-plan",
    "ai-build",  # spec-127 D-127-11: renamed from ai-dispatch
    "ai-autopilot",
    "ai-pr",
)

CANONICAL_SPEC_PATH = ".ai-engineering/specs/spec.md"


def test_constitution_has_article_xiii() -> None:
    assert CONSTITUTION.is_file(), (
        f"CONSTITUTION.md missing at {CONSTITUTION}. Article XIII must live "
        "at the repo root per Article V (single source of truth)."
    )
    body = CONSTITUTION.read_text(encoding="utf-8")
    assert "Active Spec Workflow Contract" in body, (
        "CONSTITUTION.md must contain the substring 'Active Spec Workflow "
        "Contract' (Article XIII title) per spec-123 D-123-07."
    )
    assert "Article XIII" in body, (
        "Article XIII heading missing from CONSTITUTION.md. The article "
        "title alone is insufficient -- the article number must also appear."
    )


def test_lifecycle_skills_exist() -> None:
    missing: list[str] = []
    for skill in LIFECYCLE_SKILLS:
        path = SKILLS_ROOT / skill / "SKILL.md"
        if not path.is_file():
            missing.append(str(path.relative_to(PROJECT_ROOT)))
    assert not missing, (
        "Lifecycle skill(s) missing per Article XIII: "
        f"{missing}. The canonical flow /ai-brainstorm -> /ai-plan -> "
        "/ai-build | /ai-autopilot -> /ai-pr requires all five surfaces."
    )


def test_lifecycle_skills_reference_canonical_spec_path() -> None:
    """Each lifecycle skill must read/write the canonical resolver path.

    Legacy `specs/spec.md` (without the `.ai-engineering/` prefix) is
    forbidden by Article XIII because it bypasses the resolver and can
    accidentally read non-canonical work-plane state.
    """
    offenders: list[str] = []
    for skill in LIFECYCLE_SKILLS:
        path = SKILLS_ROOT / skill / "SKILL.md"
        if not path.is_file():
            continue  # covered by test_lifecycle_skills_exist
        body = path.read_text(encoding="utf-8")
        if CANONICAL_SPEC_PATH not in body:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert not offenders, (
        f"Lifecycle skill(s) do not reference the canonical path "
        f"`{CANONICAL_SPEC_PATH}`: {offenders}. "
        "Per Article XIII, every skill that touches specs/ must use the "
        "resolver-canonical path (not bare `specs/spec.md`)."
    )


def test_brainstorm_and_plan_reference_canonical_surface() -> None:
    """`/ai-brainstorm` and `/ai-plan` write to the 3-file canonical surface.

    Both skills must explicitly reference at least one of the three canonical
    files (`spec.md`, `plan.md`, `_history.md`) to be Article XIII compliant.
    """
    canonical_files = ("spec.md", "plan.md", "_history.md")
    for skill in ("ai-brainstorm", "ai-plan"):
        body = (SKILLS_ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
        hits = [name for name in canonical_files if name in body]
        assert hits, (
            f"/{skill} does not reference any of the canonical files "
            f"{canonical_files}. Per Article XIII the skill must operate on "
            "the 3-file surface."
        )
