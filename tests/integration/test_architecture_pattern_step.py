"""Phase 3 GREEN: /ai-plan reads architecture-patterns.md + records pattern (spec-106 G-3).

These tests assert that the architecture-patterns context exists at
``.ai-engineering/contexts/architecture-patterns.md``, that ``/ai-plan``
SKILL.md adds a Process step that reads the context and records the chosen
pattern under a ``## Architecture`` section in ``plan.md``, and that the
SKILL.md change is mirrored across every IDE mirror so non-Claude IDEs see
the same Process step.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ARCH_PATTERNS_CONTEXT = REPO_ROOT / ".ai-engineering" / "contexts" / "architecture-patterns.md"
PLAN_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-plan" / "SKILL.md"

# Mirrored copies of the ai-plan SKILL.md propagated by `ai-eng sync`.
MIRROR_PLAN_SKILLS = (
    REPO_ROOT / ".github" / "skills" / "ai-plan" / "SKILL.md",
    REPO_ROOT / ".codex" / "skills" / "ai-plan" / "SKILL.md",
    REPO_ROOT / ".gemini" / "skills" / "ai-plan" / "SKILL.md",
)


def test_architecture_patterns_context_exists() -> None:
    """Phase 3 must create the architecture-patterns context file."""
    assert ARCH_PATTERNS_CONTEXT.exists(), (
        f"missing context: {ARCH_PATTERNS_CONTEXT}. spec-106 Phase 3 T-3.1 "
        f"must create the architecture-patterns.md context."
    )


def test_plan_skill_invokes_architecture_step() -> None:
    """ai-plan/SKILL.md Process must add an architecture-patterns step.

    The Process step must reference the architecture-patterns context file by
    path AND require recording the chosen pattern under a `## Architecture`
    section in plan.md. The step must precede task decomposition so downstream
    agents inherit the architectural intent.
    """
    assert PLAN_SKILL.exists(), f"missing skill: {PLAN_SKILL}"
    text = PLAN_SKILL.read_text(encoding="utf-8")

    # The Process step must reference the architecture-patterns context.
    assert "architecture-patterns.md" in text, (
        "ai-plan/SKILL.md must reference 'architecture-patterns.md' so the "
        "Process step explicitly tells the agent where to read patterns from."
    )

    # The step must require recording the pattern under a `## Architecture` section.
    assert "## Architecture" in text, (
        "ai-plan/SKILL.md must require recording the chosen pattern under a "
        "'## Architecture' section in plan.md so downstream agents can find it."
    )

    # Step ordering: architecture identification must precede task decomposition.
    arch_idx = text.find("Identify architecture pattern")
    decomp_idx = text.find("Decompose into tasks")
    assert arch_idx != -1, "ai-plan/SKILL.md missing 'Identify architecture pattern' Process step"
    assert decomp_idx != -1, "ai-plan/SKILL.md missing 'Decompose into tasks' Process step"
    assert arch_idx < decomp_idx, (
        "Architecture identification must precede task decomposition in "
        "ai-plan/SKILL.md so the chosen pattern informs the task breakdown."
    )


def test_plan_skill_handles_no_pattern_case() -> None:
    """SKILL.md must document the fallback when no canonical pattern fits."""
    text = PLAN_SKILL.read_text(encoding="utf-8")
    assert "ad-hoc" in text, (
        "ai-plan/SKILL.md must document the 'ad-hoc' fallback so the agent "
        "knows what to write under '## Architecture' when no pattern fits."
    )


def test_plan_skill_changes_mirrored_across_ides() -> None:
    """Every IDE mirror of ai-plan SKILL.md must contain the architecture step.

    `ai-eng sync` propagates SKILL.md edits to every IDE mirror. If the mirror
    is stale, non-Claude IDEs will not see the architecture step and behavior
    will diverge across IDEs. This asserts mirror parity for the new step.
    """
    canonical = PLAN_SKILL.read_text(encoding="utf-8")
    assert "architecture-patterns.md" in canonical, (
        "Pre-condition: canonical SKILL.md must reference the context first."
    )

    for mirror in MIRROR_PLAN_SKILLS:
        assert mirror.exists(), f"missing mirror SKILL.md: {mirror}"
        mirror_text = mirror.read_text(encoding="utf-8")
        assert "architecture-patterns.md" in mirror_text, (
            f"mirror {mirror} missing 'architecture-patterns.md' reference; "
            f"run `uv run ai-eng sync` to propagate the canonical SKILL.md."
        )
        assert "## Architecture" in mirror_text, (
            f"mirror {mirror} missing '## Architecture' section reference"
        )
        assert "Identify architecture pattern" in mirror_text, (
            f"mirror {mirror} missing 'Identify architecture pattern' step"
        )
