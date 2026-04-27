"""Phase 2 RED: design keyword allowlist for /ai-plan routing (spec-106 G-2).

Asserts the conservative keyword allowlist defined in D-106-02:

    page, component, screen, dashboard, form, modal,
    design system, color palette, typography, layout,
    ui, ux, frontend, react component, vue component,
    interface, mobile screen, responsive, accessibility

Plus negative cases (false-positive mitigation per R-2) and the
``--skip-design`` override behavior. Marked ``spec_106_red``: delivered GREEN
when Phase 2 lands the keyword allowlist file/loader and the override flag
plumbing.
"""

from __future__ import annotations

import pytest

EXPECTED_KEYWORDS = (
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


@pytest.mark.spec_106_red
def test_keyword_allowlist_contains_all_expected_terms() -> None:
    """The allowlist surface must export every keyword from D-106-02."""
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.1: design-routing handler must define a keyword "
        "allowlist matching D-106-02 (case-insensitive substring match)."
    )


@pytest.mark.spec_106_red
@pytest.mark.parametrize("keyword", EXPECTED_KEYWORDS)
def test_each_expected_keyword_triggers_routing(keyword: str) -> None:
    """A spec body containing each allowlisted keyword triggers routing."""
    raise NotImplementedError(
        f"spec-106 Phase 2 T-2.6: keyword '{keyword}' must trigger design routing."
    )


@pytest.mark.spec_106_red
@pytest.mark.parametrize(
    "non_ui_phrase",
    [
        # API design discussion in a backend service spec must NOT trigger
        # design routing even though the word 'design' appears.
        "discusses API design conventions for the auth service",
        # Database schema work referencing 'pages' (e.g., pagination) must
        # NOT trigger routing on the bare token 'page' inside a longer word.
        "database query pagination strategy across multiple pages",
        # Backend module work referencing 'interface' as in TypeScript types
        # must NOT trigger routing without UI context.
        "introduces a public TypeScript interface for the SDK client",
    ],
)
def test_non_ui_contexts_do_not_trigger_routing(non_ui_phrase: str) -> None:
    """False-positive mitigation per R-2: conservative keyword matching."""
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.6: non-UI phrases must NOT trigger design routing. "
        f"Phrase under test: {non_ui_phrase!r}."
    )


@pytest.mark.spec_106_red
def test_skip_design_flag_overrides_keyword_match() -> None:
    """--skip-design override bypasses routing even when keywords match."""
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.6: --skip-design forces no-route regardless of keywords."
    )


@pytest.mark.spec_106_red
def test_routing_decision_emits_explicit_log_line() -> None:
    """R-2 mitigation: the routing decision is logged so the user sees rationale."""
    raise NotImplementedError(
        "spec-106 Phase 2 T-2.1: design-routing handler emits a log line "
        "stating routing decision (matched keyword + decision)."
    )
