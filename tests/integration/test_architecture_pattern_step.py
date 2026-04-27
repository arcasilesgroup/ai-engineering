"""Phase 3 RED: /ai-plan reads architecture-patterns.md + records pattern (spec-106 G-3).

These tests assert the architecture-patterns context exists at
``.ai-engineering/contexts/architecture-patterns.md``, that ``/ai-plan``
SKILL.md adds a Process step that reads the context and records the chosen
pattern under a ``## Architecture`` section in ``plan.md``.

Marked ``spec_106_red``: excluded from the default CI run until Phase 3
delivers the GREEN context file, the SKILL.md wiring, and an explicit
``## Architecture`` section pattern in plan.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

ARCH_PATTERNS_CONTEXT = REPO_ROOT / ".ai-engineering" / "contexts" / "architecture-patterns.md"
PLAN_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-plan" / "SKILL.md"


@pytest.mark.spec_106_red
def test_architecture_patterns_context_exists() -> None:
    """Phase 3 must create the architecture-patterns context file."""
    # Deferred import per spec-106 RED contract.
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.1: architecture-patterns context not yet created. "
        "Expected file: .ai-engineering/contexts/architecture-patterns.md"
    )


@pytest.mark.spec_106_red
def test_plan_skill_invokes_architecture_step() -> None:
    """ai-plan/SKILL.md Process must add an architecture-patterns step."""
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.2: /ai-plan SKILL.md must add a Process step "
        "that reads architecture-patterns.md and records the chosen pattern "
        "in plan.md under '## Architecture' before task decomposition."
    )


@pytest.mark.spec_106_red
def test_plan_md_records_architecture_section() -> None:
    """A planned spec must produce a plan.md with a ## Architecture section.

    After /ai-plan runs against a fixture spec, the generated plan.md must
    include a '## Architecture' section identifying the chosen pattern with
    a brief justification (or 'ad-hoc' explanation if no pattern fits).
    """
    raise NotImplementedError(
        "spec-106 Phase 3 T-3.6: plan.md from /ai-plan must include "
        "'## Architecture' section with non-empty pattern reference."
    )
