"""RED-phase tests for spec-111 T-2.5/T-2.6 -- /ai-research Tier 2 web search.

Spec acceptance:
    Tier 2 (web) implemented in ``tier2-web.md`` -- handler invokes
    ``WebSearch`` (raw web results) and ``WebFetch`` (specific URL when
    referenced) IN PARALLEL when Tier 1 yielded fewer than 5 high-quality
    hits OR the user query referenced an explicit URL. Domain filters
    ``--allowed-domains`` and ``--blocked-domains`` pass through to the
    WebSearch tool. Skip path: tier1 ≥5 hits without explicit URL.

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_tier2_helper.py`` mirrors the
algorithm 1:1; these tests exercise the helper.

Status: RED until T-2.7 lands the helper module + handler logic.
"""

from __future__ import annotations

import time

import pytest

from tests.integration._ai_research_tier1_helper import Tier1Hit
from tests.integration._ai_research_tier2_helper import (
    Tier2Result,
    tier2_web,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _RecordingWebSearch:
    """Records every WebSearch call with its kwargs (for filter assertions)."""

    def __init__(self, hits: list | None = None) -> None:
        self.calls: list[dict] = []
        self.hits = hits or []
        self.start_times: list[float] = []

    def __call__(self, query: str, **kwargs) -> list:
        self.start_times.append(time.perf_counter())
        self.calls.append({"query": query, **kwargs})
        time.sleep(0.05)
        return list(self.hits)


class _RecordingWebFetch:
    """Records every WebFetch call with the URL it was given."""

    def __init__(self, hits: list | None = None) -> None:
        self.calls: list[str] = []
        self.hits = hits or []
        self.start_times: list[float] = []

    def __call__(self, url: str, **_kwargs) -> list:
        self.start_times.append(time.perf_counter())
        self.calls.append(url)
        time.sleep(0.05)
        return list(self.hits)


def _stub_web_hit(url: str = "https://example.com/a", title: str = "Stub") -> dict:
    return {"title": title, "url": url, "snippet": "stub snippet", "source": "web"}


def _make_tier1_hits(n: int) -> list[Tier1Hit]:
    """Generate ``n`` distinct Tier 1 hits."""
    return [
        Tier1Hit(
            title=f"hit-{i}",
            url=f"https://docs.example.com/page-{i}",
            snippet=f"snippet-{i}",
            source="context7",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# T-2.5: domain filters pass-through
# ---------------------------------------------------------------------------


def test_websearch_invoked_with_filters() -> None:
    """``--allowed-domains`` flag must pass through to WebSearch tool call.

    Arrange: a query with no explicit URL, three Tier 1 hits (so Tier 2
    runs), and ``allowed_domains=["a.com", "b.com"]``.

    Act: invoke ``tier2_web``.

    Assert: WebSearch received exactly one call with
    ``allowed_domains == ["a.com", "b.com"]``.
    """
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch()

    result = tier2_web(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        allowed_domains=["a.com", "b.com"],
        web_search=web_search,
        web_fetch=web_fetch,
    )

    assert isinstance(result, Tier2Result)
    assert len(web_search.calls) == 1, (
        f"Expected exactly one WebSearch call when tier2 runs; got {len(web_search.calls)}"
    )
    assert web_search.calls[0].get("allowed_domains") == ["a.com", "b.com"], (
        f"WebSearch was not invoked with the allowed_domains pass-through: {web_search.calls[0]}"
    )
    # WebFetch must NOT be called when no explicit URL is in the query.
    assert web_fetch.calls == [], "WebFetch should not run when query has no explicit URL"


def test_websearch_invoked_with_blocked_filter() -> None:
    """Symmetric: ``--blocked-domains`` flag also passes through."""
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch()

    tier2_web(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        blocked_domains=["x.com"],
        web_search=web_search,
        web_fetch=web_fetch,
    )

    assert web_search.calls[0].get("blocked_domains") == ["x.com"]


# ---------------------------------------------------------------------------
# T-2.6: skip when Tier 1 already yielded ≥5 hits and no explicit URL
# ---------------------------------------------------------------------------


def test_tier2_skipped_when_tier1_yields_5_plus_hits() -> None:
    """Tier 2 MUST short-circuit when Tier 1 returned ≥5 hits without explicit URL.

    Arrange: 5 Tier 1 hits, no explicit URL in the query, no domain filters.

    Act: invoke ``tier2_web``.

    Assert: neither WebSearch nor WebFetch was called, and the result
    flags ``skipped=True``.
    """
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch()

    result = tier2_web(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(5),
        web_search=web_search,
        web_fetch=web_fetch,
    )

    assert result.skipped is True, "Tier 2 must skip when tier1_hits ≥ 5 and no explicit URL"
    assert web_search.calls == [], "WebSearch must not be invoked when Tier 2 is skipped"
    assert web_fetch.calls == [], "WebFetch must not be invoked when Tier 2 is skipped"
    assert result.hits == []


# ---------------------------------------------------------------------------
# Edge cases that pin down the skip heuristic
# ---------------------------------------------------------------------------


def test_tier2_runs_when_tier1_below_threshold() -> None:
    """≤4 Tier 1 hits with no explicit URL still triggers Tier 2."""
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch()

    result = tier2_web(
        "obscure topic with no canonical docs",
        tier1_hits=_make_tier1_hits(4),
        web_search=web_search,
        web_fetch=web_fetch,
    )

    assert result.skipped is False
    assert len(web_search.calls) == 1


def test_tier2_runs_when_explicit_url_even_with_5_tier1_hits() -> None:
    """Explicit URL in query forces Tier 2 even when Tier 1 already had ≥5 hits."""
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch([_stub_web_hit()])

    result = tier2_web(
        "what does https://example.org/article say about retries",
        tier1_hits=_make_tier1_hits(5),
        web_search=web_search,
        web_fetch=web_fetch,
    )

    assert result.skipped is False
    # WebFetch is called with the explicit URL.
    assert web_fetch.calls == ["https://example.org/article"]
    # WebSearch also runs in parallel.
    assert len(web_search.calls) == 1


def test_tier2_websearch_and_webfetch_run_in_parallel() -> None:
    """When both WebSearch and WebFetch run, their starts are within 100ms."""
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch([_stub_web_hit()])

    tier2_web(
        "describe https://example.org/article",
        tier1_hits=_make_tier1_hits(2),
        web_search=web_search,
        web_fetch=web_fetch,
    )

    starts = [web_search.start_times[0], web_fetch.start_times[0]]
    delta_ms = (max(starts) - min(starts)) * 1000.0
    assert delta_ms < 100.0, (
        f"Expected WebSearch and WebFetch to start within 100ms (parallel); got {delta_ms:.1f}ms"
    )


@pytest.mark.parametrize(
    "tier1_count,expected_skipped",
    [
        (0, False),
        (3, False),
        (4, False),
        (5, True),
        (10, True),
    ],
)
def test_skip_threshold_boundary(tier1_count: int, expected_skipped: bool) -> None:
    """The skip boundary is exactly 5 (≥5 skips when no URL)."""
    web_search = _RecordingWebSearch([_stub_web_hit()])
    web_fetch = _RecordingWebFetch()

    result = tier2_web(
        "neutral query",
        tier1_hits=_make_tier1_hits(tier1_count),
        web_search=web_search,
        web_fetch=web_fetch,
    )
    assert result.skipped is expected_skipped, (
        f"With tier1_count={tier1_count} expected skipped={expected_skipped}, got {result.skipped}"
    )
