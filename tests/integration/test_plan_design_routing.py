"""Phase 2 GREEN: /ai-plan auto-routes UI specs through /ai-design (spec-106 G-2).

Asserts that the design-routing handler exists at
``.claude/skills/ai-plan/handlers/design-routing.md``, that the handler
contains the canonical sections (keyword allowlist, detection logic, routing
flow, override flag, plan integration, output behavior), that ``/ai-plan``
SKILL.md invokes the handler at the correct Process step, and that the
keyword-detection algorithm (mirrored as a tiny pure-Python function in this
test module) correctly routes UI fixtures, leaves non-UI fixtures untouched,
and honors the ``--skip-design`` override.

The handler is markdown (not Python) and is consumed by an LLM at planning
time. We therefore validate two surfaces:

1. **Contract**: the handler markdown contains every section the spec
   requires, the SKILL.md references the handler at the correct step.
2. **Behavior**: a Python mirror of the keyword-detection logic (sourced
   from the handler's documented algorithm) routes the fixtures the way
   the handler claims it will, including the ``--skip-design`` override.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DESIGN_ROUTING_HANDLER = (
    REPO_ROOT / ".claude" / "skills" / "ai-plan" / "handlers" / "design-routing.md"
)
PLAN_SKILL = REPO_ROOT / ".claude" / "skills" / "ai-plan" / "SKILL.md"
FIXTURE_UI = REPO_ROOT / "tests" / "fixtures" / "spec_with_ui_keywords.md"
FIXTURE_NON_UI = REPO_ROOT / "tests" / "fixtures" / "spec_without_ui_keywords.md"

# Canonical keyword allowlist mirrored from the handler. Kept as a tuple in
# the same order the handler documents so the Python mirror behaves the way
# the handler claims (deterministic, deduplicated, allowlist-ordered).
KEYWORD_ALLOWLIST = (
    "page",
    "component",
    "screen",
    "dashboard",
    "form",
    "modal",
    "design system",
    "color palette",
    "typography",
    "layout",
    "ui",
    "ux",
    "frontend",
    "react component",
    "vue component",
    "interface",
    "mobile screen",
    "responsive",
    "accessibility",
)


def _strip_frontmatter(text: str) -> str:
    """Strip leading YAML frontmatter (``---`` ... ``---``) from a spec body."""
    if not text.startswith("---"):
        return text
    closing = text.find("\n---", 3)
    if closing == -1:
        return text
    return text[closing + 4 :]


def _detect_route(spec_body: str, skip_design: bool = False) -> tuple[bool, list[str]]:
    """Mirror of the handler's documented detection algorithm.

    Returns ``(route_required, matched_keywords)``. The override
    short-circuits before any keyword scanning.
    """
    if skip_design:
        return (False, [])
    body = _strip_frontmatter(spec_body).lower()
    matched: list[str] = []
    for keyword in KEYWORD_ALLOWLIST:
        if keyword in body and keyword not in matched:
            matched.append(keyword)
    return (bool(matched), matched)


def test_design_routing_handler_exists() -> None:
    """Phase 2 must create the design-routing handler under ai-plan/handlers/."""
    assert DESIGN_ROUTING_HANDLER.exists(), (
        f"missing handler: {DESIGN_ROUTING_HANDLER}. spec-106 Phase 2 T-2.1 "
        f"must create the design-routing handler."
    )

    body = DESIGN_ROUTING_HANDLER.read_text(encoding="utf-8")
    # Required sections per handler contract
    required_sections = (
        "## Purpose",
        "## Keyword Allowlist",
        "## Detection Logic",
        "## Override Flag",
        "## Routing Flow",
        "## Plan Integration",
        "## Output Behavior",
        "## Consumers",
    )
    for section in required_sections:
        assert section in body, f"design-routing handler missing required section: {section!r}"

    # Override flag must be referenced explicitly
    assert "--skip-design" in body, "handler must document the --skip-design override flag"

    # Plan integration must reference the ## Design section emitted by /ai-plan
    assert "## Design" in body, (
        "handler must reference the '## Design' section emitted in plan.md when routing"
    )


def test_plan_skill_invokes_design_routing() -> None:
    """ai-plan/SKILL.md Process must invoke the design-routing handler.

    The Process section gains a step that names the handler explicitly so the
    LLM consumer reads it at planning time. The step must come BEFORE task
    decomposition so design intent is captured before the plan is written.
    """
    assert PLAN_SKILL.exists(), f"missing skill: {PLAN_SKILL}"
    text = PLAN_SKILL.read_text(encoding="utf-8")

    assert "handlers/design-routing.md" in text, (
        "ai-plan/SKILL.md must reference 'handlers/design-routing.md' to invoke "
        "design routing before task decomposition"
    )
    assert "--skip-design" in text, (
        "ai-plan/SKILL.md must document the --skip-design override so users can opt out"
    )
    # Step ordering: design routing must precede task decomposition.
    routing_idx = text.find("Design routing")
    decomp_idx = text.find("Decompose into tasks")
    assert routing_idx != -1, "ai-plan/SKILL.md missing 'Design routing' Process step"
    assert decomp_idx != -1, "ai-plan/SKILL.md missing 'Decompose into tasks' Process step"
    assert routing_idx < decomp_idx, (
        "Design routing step must precede task decomposition in ai-plan/SKILL.md"
    )


def test_ui_spec_routes_through_design() -> None:
    """A spec containing UI keywords must produce route_required=True.

    The fixture spec.md contains keywords like 'page', 'component', 'modal',
    'dashboard'. The handler's documented detection algorithm (mirrored in
    ``_detect_route``) must classify the fixture as routed and surface the
    matched keywords for the log line.
    """
    assert FIXTURE_UI.exists(), f"missing fixture: {FIXTURE_UI}"
    spec_body = FIXTURE_UI.read_text(encoding="utf-8")

    route_required, matched = _detect_route(spec_body)
    assert route_required is True, (
        f"UI fixture must trigger routing; matched keywords were: {matched!r}"
    )
    assert matched, "matched_keywords must be non-empty when route_required=True"
    # Sanity: at least one obviously-UI keyword from the fixture is detected.
    assert any(kw in matched for kw in ("dashboard", "component", "page", "modal")), (
        f"expected at least one core UI keyword in matched list, got: {matched!r}"
    )


def test_non_ui_spec_does_not_route() -> None:
    """A backend-only spec must produce route_required=False."""
    assert FIXTURE_NON_UI.exists(), f"missing fixture: {FIXTURE_NON_UI}"
    spec_body = FIXTURE_NON_UI.read_text(encoding="utf-8")

    route_required, matched = _detect_route(spec_body)
    assert route_required is False, (
        f"non-UI fixture must NOT trigger routing; matched keywords were: {matched!r}"
    )
    assert matched == [], f"matched_keywords must be empty for non-UI spec, got: {matched!r}"


def test_skip_design_flag_bypasses_routing() -> None:
    """--skip-design override must skip routing even when keywords match.

    When the user passes ``--skip-design``, ``/ai-plan`` MUST NOT invoke
    ``/ai-design`` even if UI keywords are present, and ``plan.md`` MUST NOT
    contain a ``## Design`` section. The handler short-circuits before the
    keyword scan, returning ``(False, [])``.
    """
    spec_body = FIXTURE_UI.read_text(encoding="utf-8")

    route_required, matched = _detect_route(spec_body, skip_design=True)
    assert route_required is False, (
        "--skip-design must force route_required=False regardless of keywords"
    )
    assert matched == [], (
        "--skip-design must short-circuit before keyword scan (matched must be empty)"
    )
