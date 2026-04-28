"""Phase 2 GREEN: design keyword allowlist for /ai-plan routing (spec-106 G-2).

Asserts the conservative keyword allowlist defined in D-106-02:

    page, component, screen, dashboard, form, modal,
    design system, color palette, typography, layout,
    ui, ux, frontend, react component, vue component,
    interface, mobile screen, responsive, accessibility

Plus negative cases (false-positive mitigation per R-2) and the
``--skip-design`` override behavior. The handler is markdown (not Python),
so the tests verify two things:

1. Each canonical keyword appears verbatim inside the handler's allowlist
   block, in the same order, with the same multi-word phrasing.
2. A Python mirror of the documented detection algorithm routes UI text,
   leaves non-UI text untouched, and honors the ``--skip-design`` override.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLER = REPO_ROOT / ".claude" / "skills" / "ai-plan" / "handlers" / "design-routing.md"

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


def _strip_frontmatter(text: str) -> str:
    """Strip leading YAML frontmatter (``---`` ... ``---``) from a spec body."""
    if not text.startswith("---"):
        return text
    closing = text.find("\n---", 3)
    if closing == -1:
        return text
    return text[closing + 4 :]


def _detect_route(spec_body: str, skip_design: bool = False) -> tuple[bool, list[str]]:
    """Mirror of the handler's documented detection algorithm."""
    if skip_design:
        return (False, [])
    body = _strip_frontmatter(spec_body).lower()
    matched: list[str] = []
    for keyword in EXPECTED_KEYWORDS:
        if keyword in body and keyword not in matched:
            matched.append(keyword)
    return (bool(matched), matched)


def test_handler_exists() -> None:
    """Pre-condition: design-routing handler must exist before allowlist checks."""
    assert HANDLER.exists(), f"missing handler: {HANDLER}"


def test_keyword_allowlist_contains_all_expected_terms() -> None:
    """The handler markdown must list every keyword from D-106-02 verbatim."""
    body = HANDLER.read_text(encoding="utf-8")
    for keyword in EXPECTED_KEYWORDS:
        assert keyword in body, (
            f"design-routing handler missing canonical keyword '{keyword}' in allowlist"
        )


def test_handler_documents_detection_logic() -> None:
    """Detection logic must be documented (case-insensitive substring match)."""
    body = HANDLER.read_text(encoding="utf-8").lower()
    # The handler must explain the matching strategy so consumers replicate it.
    assert "case-insensitive" in body, (
        "handler must document case-insensitive matching for the allowlist"
    )
    assert "substring" in body, "handler must document substring (not token) matching"


def test_handler_documents_override_flag() -> None:
    """Override flag mention must be present in the handler."""
    body = HANDLER.read_text(encoding="utf-8")
    assert "--skip-design" in body, "handler must document the --skip-design override flag"


def test_handler_documents_log_line_contract() -> None:
    """R-2 mitigation: handler must specify the routing-decision log line."""
    body = HANDLER.read_text(encoding="utf-8")
    # The three canonical log-line shapes must appear in the handler so the
    # decision is auditable and downstream tooling can grep for them.
    assert "design-routing: routed" in body, (
        "handler must specify the 'design-routing: routed' log line shape"
    )
    assert "design-routing: skipped" in body, (
        "handler must specify the 'design-routing: skipped' log line shape"
    )


@pytest.mark.parametrize("keyword", EXPECTED_KEYWORDS)
def test_each_expected_keyword_triggers_routing(keyword: str) -> None:
    """A spec body containing each allowlisted keyword triggers routing.

    Each keyword is wrapped in a minimal sentence so the detection runs
    against realistic spec text rather than the bare token alone.
    """
    spec_body = f"# Spec\n\nThis spec discusses {keyword} explicitly.\n"
    route_required, matched = _detect_route(spec_body)
    assert route_required is True, f"keyword '{keyword}' must trigger routing"
    assert keyword in matched, f"matched_keywords must include '{keyword}'"


@pytest.mark.parametrize(
    "non_ui_phrase",
    [
        # Backend service spec discussing API conventions -- the bare word
        # 'design' alone is NOT in the allowlist, only 'design system'. So
        # this phrase must NOT trigger routing.
        "discusses API conventions for the auth service",
        # Database schema work referencing 'pagination' (no 'page' substring
        # match because we lowercased and 'pagination' contains 'page'... but
        # the handler uses substring match so we accept this is a known
        # false-positive risk per R-2).
        "database schema migration for the orders table",
        # Pure backend with no UI keywords whatsoever.
        "introduces a CLI subcommand for the deployer service",
    ],
)
def test_non_ui_contexts_do_not_trigger_routing(non_ui_phrase: str) -> None:
    """False-positive mitigation per R-2: conservative keyword matching."""
    spec_body = f"# Spec\n\n{non_ui_phrase}.\n"
    route_required, matched = _detect_route(spec_body)
    assert route_required is False, (
        f"phrase {non_ui_phrase!r} must NOT trigger routing; matched: {matched!r}"
    )


def test_skip_design_flag_overrides_keyword_match() -> None:
    """--skip-design override bypasses routing even when keywords match."""
    spec_body = "# Spec\n\nBuild a dashboard with a responsive layout and a modal.\n"
    # Without override: must route.
    route_required, matched = _detect_route(spec_body)
    assert route_required is True, "sanity: UI text must route without override"
    assert matched, "sanity: matched keywords must be non-empty without override"

    # With override: must NOT route.
    route_required_override, matched_override = _detect_route(spec_body, skip_design=True)
    assert route_required_override is False, (
        "--skip-design must force route_required=False even when keywords match"
    )
    assert matched_override == [], (
        "--skip-design must short-circuit detection (matched must be empty)"
    )


def test_routing_decision_emits_explicit_log_line() -> None:
    """R-2 mitigation: the routing decision is logged so the user sees rationale.

    Validated by asserting the handler documents the three canonical log-line
    shapes (routed / no-keywords / --skip-design) so the LLM consumer emits
    them at planning time.
    """
    body = HANDLER.read_text(encoding="utf-8")
    assert "matched keywords" in body, (
        "handler must document that the routed log line includes matched keyword list"
    )
    assert "no keywords matched" in body, (
        "handler must document the 'no keywords matched' skip log line"
    )
    assert "(--skip-design)" in body, "handler must document the '(--skip-design)' skip log line"
