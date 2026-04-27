"""Phase 2 RED: /ai-plan auto-routes UI specs through /ai-design (spec-106 G-2).

These tests assert the design-routing handler exists at
``.claude/skills/ai-plan/handlers/design-routing.md``, that ``/ai-plan``
invokes it when the spec body contains UI keywords, and that the resulting
``plan.md`` contains a ``## Design`` section linking the design-intent
artifact emitted by ``/ai-design``.

Marked ``spec_106_red``: excluded from the default CI run until Phase 2
delivers the GREEN handler, the ``/ai-plan`` routing wiring, and the
``--skip-design`` override.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DESIGN_ROUTING_HANDLER = (
    REPO_ROOT / ".claude" / "skills" / "ai-plan" / "handlers" / "design-routing.md"
)
PLAN_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-plan" / "SKILL.md"


@pytest.mark.spec_106_red
def test_design_routing_handler_exists() -> None:
    """Phase 2 must create the design-routing handler under ai-plan/handlers/."""
    # Deferred imports + assertions follow Phase 2 GREEN delivery.
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.1: design-routing handler not yet created. "
        "Expected file: .claude/skills/ai-plan/handlers/design-routing.md"
    )


@pytest.mark.spec_106_red
def test_plan_skill_invokes_design_routing() -> None:
    """ai-plan/SKILL.md Process must invoke design-routing handler."""
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.2: /ai-plan SKILL.md must add a Process step "
        "that reads the design-routing handler before task decomposition."
    )


@pytest.mark.spec_106_red
def test_ui_spec_routes_through_design() -> None:
    """A spec containing UI keywords must produce a plan.md with ## Design.

    Fixture spec.md will contain keywords like 'page', 'component', 'modal',
    'dashboard'. After /ai-plan runs (or its handler is simulated), the
    generated plan.md must include a '## Design' section linking the
    design-intent artifact produced by /ai-design.
    """
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.5: UI-keyword fixture spec.md routes through "
        "/ai-design and plan.md gains a '## Design' section."
    )


@pytest.mark.spec_106_red
def test_skip_design_flag_bypasses_routing() -> None:
    """--skip-design override must skip the design-routing step entirely.

    When the user passes --skip-design, /ai-plan must NOT invoke /ai-design
    even if UI keywords are present, and plan.md must NOT contain a
    ## Design section.
    """
    raise NotImplementedError("spec-106 Phase 2 T-2.5: --skip-design override bypasses routing.")
