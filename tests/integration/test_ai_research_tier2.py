"""Tests for spec-111 T-2.5/T-2.6 + notebooklm-async-tier3 T-2.1 --
/ai-research Tier 2 web search.

Spec acceptance (spec-111):
    Tier 2 (web) implemented in ``tier2-web.md`` -- handler invokes a web
    search tool (raw web results) and a web fetch tool (specific URL when
    referenced) IN PARALLEL when Tier 1 yielded fewer than 5 high-quality
    hits OR the user query referenced an explicit URL. Domain filters
    ``--allowed-domains`` and ``--blocked-domains`` pass through to the
    search tool. Skip path: tier1 ≥5 hits without explicit URL.

Spec acceptance (notebooklm-async-tier3 D6/D7, AC3):
    Exa (``mcp__exa__web_search_exa`` / ``mcp__exa__web_fetch_exa``) is the
    PRIMARY Tier 2 web provider. The built-in WebSearch/WebFetch are the
    FALLBACK when Exa is unavailable (capability detection). When Exa is
    absent, ``"exa"`` is recorded in ``degraded_sources`` (fail-soft: skipped
    silently, recorded, never raised).

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_tier2_helper.py`` mirrors the
algorithm 1:1; these tests exercise the helper.
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


class _RecordingSearch:
    """Records every search call with its kwargs (for filter assertions).

    Used for both the Exa search provider and the built-in WebSearch
    fallback -- the call shape is identical, only the injected callable
    differs.
    """

    def __init__(self, hits: list | None = None) -> None:
        self.calls: list[dict] = []
        self.hits = hits or []
        self.start_times: list[float] = []

    def __call__(self, query: str, **kwargs) -> list:
        self.start_times.append(time.perf_counter())
        self.calls.append({"query": query, **kwargs})
        time.sleep(0.05)
        return list(self.hits)


class _RecordingFetch:
    """Records every fetch call with the URL it was given.

    Used for both the Exa fetch provider and the built-in WebFetch
    fallback.
    """

    def __init__(self, hits: list | None = None) -> None:
        self.calls: list[str] = []
        self.hits = hits or []
        self.start_times: list[float] = []

    def __call__(self, url: str, **_kwargs) -> list:
        self.start_times.append(time.perf_counter())
        self.calls.append(url)
        time.sleep(0.05)
        return list(self.hits)


class _RaisingSearch:
    """A search callable that always raises (per-call failure path)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, query: str, **kwargs) -> list:
        self.calls.append({"query": query, **kwargs})
        raise RuntimeError("search provider unavailable")


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


def _call_tier2(
    query: str,
    *,
    tier1_hits: list[Tier1Hit],
    exa_search: _RecordingSearch,
    exa_fetch: _RecordingFetch,
    web_search: _RecordingSearch,
    web_fetch: _RecordingFetch,
    exa_available: bool,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> Tier2Result:
    """Thin wrapper to keep the new keyword-only signature DRY in tests."""
    return tier2_web(
        query,
        tier1_hits=tier1_hits,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=exa_available,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )


# ---------------------------------------------------------------------------
# notebooklm-async-tier3 T-2.1: Exa primary / built-in fallback (D6, D7, AC3)
# ---------------------------------------------------------------------------


def test_exa_used_as_primary_when_available() -> None:
    """When Exa is available, Exa search runs and the built-in does NOT.

    Arrange: a query with no explicit URL, three Tier 1 hits (so Tier 2
    runs), ``exa_available=True``.

    Act: invoke ``tier2_web``.

    Assert: ``exa_search`` was called once; built-in ``web_search`` was not
    called; ``"exa"`` is NOT in ``degraded_sources``.
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert isinstance(result, Tier2Result)
    assert len(exa_search.calls) == 1, (
        f"Exa search must be the primary provider; got {len(exa_search.calls)} calls"
    )
    assert web_search.calls == [], "Built-in WebSearch must NOT run when Exa is available"
    assert "exa" not in result.degraded_sources
    assert result.skipped is False
    assert result.hits == [_stub_web_hit()]


def test_exa_fetch_used_for_explicit_url_when_available() -> None:
    """With an explicit URL and Exa available, ``exa_fetch`` handles the URL."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch([_stub_web_hit()])
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch([_stub_web_hit()])

    result = _call_tier2(
        "what does https://example.org/article say about retries",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert exa_fetch.calls == ["https://example.org/article"]
    assert web_fetch.calls == [], "Built-in WebFetch must not run when Exa is available"
    assert len(exa_search.calls) == 1
    assert result.skipped is False


def test_fallback_to_builtin_when_exa_unavailable() -> None:
    """When Exa is unavailable, fall back to built-in WebSearch/WebFetch.

    Arrange: ``exa_available=False``, three Tier 1 hits (so Tier 2 runs).

    Act: invoke ``tier2_web``.

    Assert: built-in ``web_search`` ran once; Exa search did NOT run; and
    ``"exa"`` is recorded in ``degraded_sources`` (D7 fail-soft).
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=False,
    )

    assert exa_search.calls == [], "Exa must NOT be called when unavailable"
    assert len(web_search.calls) == 1, (
        "Built-in WebSearch must run as the fallback when Exa is unavailable"
    )
    assert "exa" in result.degraded_sources, (
        "Absent Exa provider must be recorded in degraded_sources (D7)"
    )
    assert result.skipped is False
    assert result.hits == [_stub_web_hit()]


def test_fallback_fetch_to_builtin_when_exa_unavailable() -> None:
    """With an explicit URL and Exa absent, built-in WebFetch handles the URL."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch([_stub_web_hit()])
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch([_stub_web_hit()])

    result = _call_tier2(
        "describe https://example.org/article",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=False,
    )

    assert exa_fetch.calls == [], "Exa fetch must NOT run when Exa is unavailable"
    assert web_fetch.calls == ["https://example.org/article"]
    assert "exa" in result.degraded_sources


def test_exa_available_does_not_record_degraded() -> None:
    """When Exa is available and succeeds, ``degraded_sources`` stays empty."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch()
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "neutral query",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert result.degraded_sources == []


def test_exa_search_exception_records_tool_name_and_continues() -> None:
    """A per-call Exa search failure records the Exa tool name and never raises.

    The chosen provider's search call raises; the result must carry the
    failing tool's name in ``degraded_sources`` and still return (no
    re-raise). The surviving fetch (if any) is preserved.
    """
    exa_search = _RaisingSearch()
    exa_fetch = _RecordingFetch([_stub_web_hit("https://example.org/article")])
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch([_stub_web_hit()])

    result = _call_tier2(
        "explain https://example.org/article",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert "mcp__exa__web_search_exa" in result.degraded_sources, (
        f"Exa search failure must record the tool name; got {result.degraded_sources}"
    )
    # Surviving Exa fetch result is preserved.
    assert result.hits == [_stub_web_hit("https://example.org/article")]
    # Built-in fallback must NOT be invoked just because the Exa call failed.
    assert web_search.calls == []


def test_builtin_search_exception_records_tool_name_and_continues() -> None:
    """A per-call built-in search failure (fallback path) records the tool name."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RaisingSearch()
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "neutral query",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=False,
    )

    # "exa" recorded for the absent provider AND the built-in tool name for
    # the per-call failure.
    assert "exa" in result.degraded_sources
    assert "web_search" in result.degraded_sources, (
        f"Built-in search failure must record the tool name; got {result.degraded_sources}"
    )
    assert result.hits == []


# ---------------------------------------------------------------------------
# T-2.5: domain filters pass-through (ported to the Exa-primary signature)
# ---------------------------------------------------------------------------


def test_websearch_invoked_with_filters() -> None:
    """``--allowed-domains`` flag must pass through to the chosen search tool.

    Arrange: a query with no explicit URL, three Tier 1 hits (so Tier 2
    runs), ``allowed_domains=["a.com", "b.com"]``, Exa available.

    Act: invoke ``tier2_web``.

    Assert: the Exa search received exactly one call with
    ``allowed_domains == ["a.com", "b.com"]``.
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        allowed_domains=["a.com", "b.com"],
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert isinstance(result, Tier2Result)
    assert len(exa_search.calls) == 1, (
        f"Expected exactly one search call when tier2 runs; got {len(exa_search.calls)}"
    )
    assert exa_search.calls[0].get("allowed_domains") == ["a.com", "b.com"], (
        f"Search was not invoked with the allowed_domains pass-through: {exa_search.calls[0]}"
    )
    # Fetch must NOT be called when no explicit URL is in the query.
    assert exa_fetch.calls == [], "Fetch should not run when query has no explicit URL"


def test_websearch_invoked_with_blocked_filter() -> None:
    """Symmetric: ``--blocked-domains`` flag also passes through.

    Verified on the fallback (built-in) path to prove pass-through is
    provider-agnostic.
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        blocked_domains=["x.com"],
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=False,
    )

    assert web_search.calls[0].get("blocked_domains") == ["x.com"]


# ---------------------------------------------------------------------------
# T-2.6: skip when Tier 1 already yielded ≥5 hits and no explicit URL
# ---------------------------------------------------------------------------


def test_tier2_skipped_when_tier1_yields_5_plus_hits() -> None:
    """Tier 2 MUST short-circuit when Tier 1 returned ≥5 hits without explicit URL.

    Arrange: 5 Tier 1 hits, no explicit URL in the query, no domain filters.

    Act: invoke ``tier2_web``.

    Assert: no provider was called, and the result flags ``skipped=True``.
    Skip path runs before any provider selection, so ``"exa"`` is NOT
    recorded in ``degraded_sources``.
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(5),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=False,
    )

    assert result.skipped is True, "Tier 2 must skip when tier1_hits ≥ 5 and no explicit URL"
    assert exa_search.calls == [], "Exa must not be invoked when Tier 2 is skipped"
    assert web_search.calls == [], "WebSearch must not be invoked when Tier 2 is skipped"
    assert exa_fetch.calls == [], "Exa fetch must not be invoked when Tier 2 is skipped"
    assert web_fetch.calls == [], "WebFetch must not be invoked when Tier 2 is skipped"
    assert result.hits == []
    assert result.degraded_sources == [], (
        "Skip path short-circuits before provider selection; nothing is degraded"
    )


# ---------------------------------------------------------------------------
# Edge cases that pin down the skip heuristic
# ---------------------------------------------------------------------------


def test_tier2_runs_when_tier1_below_threshold() -> None:
    """≤4 Tier 1 hits with no explicit URL still triggers Tier 2."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "obscure topic with no canonical docs",
        tier1_hits=_make_tier1_hits(4),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert result.skipped is False
    assert len(exa_search.calls) == 1


def test_tier2_runs_when_explicit_url_even_with_5_tier1_hits() -> None:
    """Explicit URL in query forces Tier 2 even when Tier 1 already had ≥5 hits."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch([_stub_web_hit()])
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch([_stub_web_hit()])

    result = _call_tier2(
        "what does https://example.org/article say about retries",
        tier1_hits=_make_tier1_hits(5),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert result.skipped is False
    # Exa fetch is called with the explicit URL.
    assert exa_fetch.calls == ["https://example.org/article"]
    # Exa search also runs in parallel.
    assert len(exa_search.calls) == 1


def test_tier2_websearch_and_webfetch_run_in_parallel() -> None:
    """When both search and fetch run, their starts are within 100ms.

    Verified on the Exa (primary) path.
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch([_stub_web_hit()])
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch([_stub_web_hit()])

    _call_tier2(
        "describe https://example.org/article",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    starts = [exa_search.start_times[0], exa_fetch.start_times[0]]
    delta_ms = (max(starts) - min(starts)) * 1000.0
    assert delta_ms < 100.0, (
        f"Expected search and fetch to start within 100ms (parallel); got {delta_ms:.1f}ms"
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
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "neutral query",
        tier1_hits=_make_tier1_hits(tier1_count),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )
    assert result.skipped is expected_skipped, (
        f"With tier1_count={tier1_count} expected skipped={expected_skipped}, got {result.skipped}"
    )
