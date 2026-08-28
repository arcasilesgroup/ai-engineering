"""The pages module's contract, proved where the renderer could quietly break it.

Specification 046 makes this file the only door a review page passes through, so the tests
here are not coverage for its functions but for its promises: nothing authored reaches the
browser as executable markup, an unknown block stays visible instead of vanishing, and the
budgets come from `contract` rather than from a number repeated in a string. Each test
names one way the renderer could report a page that lies.
"""

from __future__ import annotations

import json

import pytest

from ai_engineering import contract, pages


def _fence(payload: dict) -> str:
    return "```visual\n" + json.dumps(payload) + "\n```\n"


def test_an_unknown_block_stays_visible_instead_of_being_dropped():
    """The silent-coercion bug, refused at the renderer.

    A page that quietly loses a block reports a plan it never rendered. The unknown name
    must appear in the warning section, and its payload must not reach the body.
    """

    text = "Intro prose.\n\n" + _fence({"block": "gantt-chart", "rows": []})
    page = pages.render_document(text, kicker="test", title="A page", sub="", meta="")
    assert "gantt-chart" in page, "an unknown block vanished without a trace"
    assert "could not render everything" in page
    assert "<table" not in page.split("could not render everything")[1], (
        "an unknown block rendered into the body despite having no renderer"
    )


def test_malformed_json_in_a_fence_warns_and_renders_the_rest():
    text = 'Before.\n\n```visual\n{"block": "diagram", \n```\n\nAfter.\n'
    page = pages.render_document(text, kicker="t", title="A page", sub="", meta="")
    assert "not valid JSON" in page
    assert "Before." in page and "After." in page, "one bad block swallowed the document"


def test_a_wireframe_cannot_carry_script_or_an_external_reference():
    """The one block whose payload is markup is filtered, not trusted.

    A mockup is HTML, so the renderer accepts markup here — and this is the only place in
    the cycle where text authored by an agent reaches a browser as markup. An event
    handler, a script or a remote `src` must not survive the filter, or a review page
    becomes a way to run something on the reviewer's machine from a file on disk.
    """

    payload = {
        "block": "wireframe-before-after",
        "title": "Login",
        "before": {"html": "<div onclick=\"fetch('https://evil.test')\">old</div>"},
        "after": {
            "html": "<div><script>alert(1)</script><img src='https://evil.test/x.png'>"
            "<p style='color:red'>new</p><a href='javascript:alert(1)'>go</a></div>"
        },
    }
    page = pages.render_document(_fence(payload), kicker="t", title="A page", sub="", meta="")
    for forbidden in ("onclick", "evil.test", "<script", "javascript:"):
        assert forbidden not in page, f"a wireframe carried {forbidden} into the page"
    assert "color:red" in page, "the filter removed the inline style a mockup needs"


def test_narrative_text_cannot_escape_into_markup():
    page = pages.render_document(
        "A <script>alert(1)</script> claim and an <img src=x onerror=alert(1)> one.\n",
        kicker="t",
        title="A page",
        sub="",
        meta="",
    )
    assert "<script>" not in page
    assert "onerror=" not in page or "&lt;img" in page, "prose reached the page as markup"


def test_a_diff_excerpt_over_the_budget_refuses_the_page():
    """The budget is `contract`'s, and exceeding it is a refusal, not a truncation.

    A recap that silently cut an excerpt would report a change it did not show. The
    renderer has no licence to drop lines, so it declines the page instead.
    """

    over = "\n".join("+x" for _ in range(contract.RECAP_EXCERPT_LINES_MAX + 1))
    with pytest.raises(pages.PageError) as refused:
        pages.render_block({"block": "diff", "path": "a.py", "text": over})
    assert str(contract.RECAP_EXCERPT_LINES_MAX) in str(refused.value), (
        "the refusal quoted a number that is not the contract's"
    )


def test_a_title_over_the_budget_refuses_the_page():
    long = "x" * (contract.PAGE_TITLE_MAX + 1)
    with pytest.raises(pages.PageError):
        pages.render_page(kicker="t", title=long, sub="", meta="", body="", warnings=[])


def test_every_page_carries_no_external_reference_and_no_script():
    """The self-contained promise, checked on a page using every block.

    The renderer's whole argument is that a review page needs no network and no toolchain.
    One block that smuggled a remote asset would break the promise for every page that
    uses it, so the sweep covers the vocabulary rather than the samples above.
    """

    blocks = [
        {"block": "diagram", "title": "Flow", "steps": [{"label": "a", "note": "n"}, "b"]},
        {
            "block": "file-tree",
            "entries": [
                {"path": "src", "change": "M", "children": [{"path": "a.py", "change": "A"}]}
            ],
        },
        {
            "block": "decision-table",
            "headers": ["Option", "Cost"],
            "rows": [{"Option": "a", "Cost": "b"}],
        },
        {
            "block": "open-questions",
            "questions": [
                {
                    "title": "Which?",
                    "options": [{"label": "a", "detail": "d"}],
                    "recommendation": "a",
                }
            ],
        },
        {"block": "checklist", "items": [{"label": "done thing", "done": True}, "open thing"]},
        {
            "block": "wireframe-before-after",
            "before": {"html": "<p>old</p>"},
            "after": {"html": "<p>new</p>"},
        },
        {
            "block": "diff",
            "path": "a.py",
            "text": "@@ -1 +1 @@\n-old\n+new",
            "summary": "one line",
        },
        {"block": "narrative", "text": "A **paragraph** with `code`."},
    ]
    page = pages.render_document(
        "\n".join(_fence(b) for b in blocks), kicker="t", title="Every block", sub="", meta=""
    )
    assert "<script" not in page
    for scheme in ("http://", "https://", "//cdn"):
        assert scheme not in page, f"a page reached the network through {scheme}"
    assert "could not render everything" not in page, "a known block warned as unknown"


def test_the_fence_is_a_wall_for_the_block_extractor_too():
    """A `visual` fence nested in an ordinary fence is content, not a block.

    The plan's grammar is fenced inside fences, and the parser that lifts blocks out must
    agree with `spec.fence_spans` about where a fence ends, or a documented example would
    render as a live surface.
    """

    text = "```markdown\n" + _fence({"block": "diagram", "steps": ["ghost"]}) + "```\n"
    blocks, warnings = pages.visual_blocks(text)
    assert blocks == [] or warnings, "a documented example became a rendered surface"
