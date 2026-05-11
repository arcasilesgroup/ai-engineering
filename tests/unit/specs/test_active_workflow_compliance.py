"""CI guard for active spec workflow contract — recalibrated per spec-131.

spec-131 D-131-04 / D-131-07 migrated the AI-behaviour articles
(including Article XIII — Active Spec Workflow Contract) out of
CONSTITUTION.md and into CANONICAL.md §11 Canonical Chain. The
chain itself was trimmed to four verbs:

    /ai-brainstorm -> /ai-plan -> /ai-build -> /ai-pr

This test asserts (after closure sweep recalibration):

1. CANONICAL.md (the canonical AI-behaviour mirror source) carries
   the four-verb chain prose so every IDE mirror inherits it.
2. Each lifecycle skill exists at its canonical path.
3. Each skill that touches `specs/` references the canonical
   resolver path `.ai-engineering/specs/spec.md` (not legacy
   `specs/spec.md`).

The Article XIII assertion is retired: the Article number lives in
git history and CHANGELOG; the runtime contract now lives in
CANONICAL.md §11.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_MD = PROJECT_ROOT / "src" / "ai_engineering" / "templates" / "project" / "CANONICAL.md"
SKILLS_ROOT = PROJECT_ROOT / ".claude" / "skills"

LIFECYCLE_SKILLS = (
    "ai-brainstorm",
    "ai-plan",
    "ai-build",  # spec-127 D-127-11: renamed from ai-dispatch
    "ai-autopilot",
    "ai-pr",
)

CANONICAL_SPEC_PATH = ".ai-engineering/specs/spec.md"

# spec-131 D-131-07 canonical chain trim — 4-verb form.
CANONICAL_CHAIN_FOUR_VERB = "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr"


def test_canonical_md_carries_four_verb_chain() -> None:
    """CANONICAL.md (D-131-04 source-of-truth) carries the trimmed chain.

    spec-131 closure (C1) replaces the legacy ``test_constitution_has_article_xiii``:
    the canonical chain prose moved out of CONSTITUTION.md when the
    AI-behaviour articles migrated to CANONICAL.md §11. The byte-equivalent
    mirrors (AGENTS.md / CLAUDE.md / GEMINI.md / copilot-instructions.md)
    are validated separately by ``test_canonical_docs_consistency``.
    """
    assert CANONICAL_MD.is_file(), (
        f"CANONICAL.md missing at {CANONICAL_MD}. spec-131 D-131-04 "
        "requires the canonical AI-behaviour payload to live at this path."
    )
    body = CANONICAL_MD.read_text(encoding="utf-8")
    assert CANONICAL_CHAIN_FOUR_VERB in body, (
        f"CANONICAL.md must carry the verbatim 4-verb chain "
        f"{CANONICAL_CHAIN_FOUR_VERB!r} per spec-131 D-131-07."
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
