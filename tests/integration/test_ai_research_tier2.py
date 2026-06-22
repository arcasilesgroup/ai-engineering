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


def test_tier2_web_accepts_tavily_provider_params() -> None:
    """RED: tier2_web must accept tavily_search/tavily_fetch + tavily_available (D-172-01)."""
    import inspect

    from tests.integration._ai_research_tier2_helper import tier2_web as _fn

    params = inspect.signature(_fn).parameters
    for name in ("tavily_search", "tavily_fetch", "tavily_available"):
        assert name in params, f"tier2_web missing required Tavily param {name!r}"


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
    tavily_search: _RecordingSearch | None = None,
    tavily_fetch: _RecordingFetch | None = None,
    tavily_available: bool = False,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> Tier2Result:
    """Thin wrapper to keep the new keyword-only signature DRY in tests.

    Tavily is the primary Tier-2 provider (D-172-01). It defaults to
    ``tavily_available=False`` with no-op recorders so the legacy Exa /
    built-in tests exercise the same cascade without per-call edits.
    """
    return tier2_web(
        query,
        tier1_hits=tier1_hits,
        tavily_search=tavily_search if tavily_search is not None else _RecordingSearch(),
        tavily_fetch=tavily_fetch if tavily_fetch is not None else _RecordingFetch(),
        tavily_available=tavily_available,
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
    """When the primary is available and succeeds, ``degraded_sources`` stays empty.

    Under the cascade default (D-172-01) Tavily is the primary; with
    ``tavily_available=True`` it succeeds, so the empty-list invariant still
    means "primary succeeded with nothing skipped".
    """
    tavily_search = _RecordingSearch([_stub_web_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch()
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "neutral query",
        tier1_hits=_make_tier1_hits(2),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert result.degraded_sources == []


def test_exa_search_exception_records_tool_name_and_continues() -> None:
    """A per-call Exa search failure records the Exa tool name and never raises.

    The selected provider's search call raises; the result must carry the
    failing tool's name in ``degraded_sources`` and still return (no
    re-raise). Under D-172-02 the raise triggers ONE bounded fall-through to
    the next available provider, but the surviving Exa fetch is preserved.

    Exa is the selected provider here (``tavily_available`` defaults False,
    so Tavily is skipped and recorded; ``exa_available=True``).
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
    # Surviving Exa fetch result is preserved across the bounded fall-through.
    assert _stub_web_hit("https://example.org/article") in result.hits
    # D-172-02: the raise falls through to the built-in EXACTLY once.
    assert len(web_search.calls) == 1


def test_builtin_search_exception_records_tool_name_and_continues() -> None:
    """A per-call built-in search failure records the tool name (terminal fallback).

    The built-in is the LAST candidate in the cascade (Tavily/Exa both
    unavailable). Its raise has no further provider to fall through to, so
    the tool name is recorded and the run returns whatever survived.
    """
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
# spec-172 WS-A T-2: 3-provider cascade (Tavily primary → Exa → built-in)
# ---------------------------------------------------------------------------


def _tavily_hit() -> dict:
    return _stub_web_hit("https://tavily.example/a", "Tavily")


def _exa_hit() -> dict:
    return _stub_web_hit("https://exa.example/a", "Exa")


def _builtin_hit() -> dict:
    return _stub_web_hit("https://builtin.example/a", "Builtin")


def test_tavily_used_as_primary_when_available() -> None:
    """When Tavily is available it is the primary; Exa/built-in do NOT run (D-172-01)."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert len(tavily_search.calls) == 1, "Tavily must be the primary provider"
    assert exa_search.calls == [], "Exa must NOT run when Tavily succeeds"
    assert web_search.calls == [], "Built-in must NOT run when Tavily succeeds"
    assert "tavily" not in result.degraded_sources
    assert result.hits == [_tavily_hit()]


def test_tavily_fetch_used_for_explicit_url() -> None:
    """With an explicit URL + Tavily available, ``tavily_fetch`` handles the URL."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch([_tavily_hit()])
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch([_exa_hit()])
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch([_builtin_hit()])

    result = _call_tier2(
        "what does https://example.org/article say about retries",
        tier1_hits=_make_tier1_hits(2),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert tavily_fetch.calls == ["https://example.org/article"]
    assert exa_fetch.calls == [], "Exa fetch must not run when Tavily is primary"
    assert web_fetch.calls == [], "Built-in fetch must not run when Tavily is primary"
    assert result.skipped is False


def test_falls_to_exa_when_tavily_unavailable() -> None:
    """Tavily absent → Exa is the selected provider; ``"tavily"`` recorded (D-172-01)."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=False,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert len(exa_search.calls) == 1, "Exa must run when Tavily is unavailable"
    assert tavily_search.calls == [], "Tavily must NOT run when unavailable"
    assert "tavily" in result.degraded_sources
    assert "exa" not in result.degraded_sources
    assert result.hits == [_exa_hit()]


def test_falls_to_builtin_when_tavily_and_exa_unavailable() -> None:
    """Tavily + Exa absent → built-in selected; both markers recorded (D-172-01)."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=False,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=False,
    )

    assert len(web_search.calls) == 1, "Built-in must run when Tavily+Exa unavailable"
    assert tavily_search.calls == []
    assert exa_search.calls == []
    assert "tavily" in result.degraded_sources
    assert "exa" in result.degraded_sources
    assert result.hits == [_builtin_hit()]


def test_tavily_available_does_not_record_degraded() -> None:
    """Tavily success records nothing in ``degraded_sources`` (D-172-01)."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "neutral query",
        tier1_hits=_make_tier1_hits(2),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert result.degraded_sources == []


def test_tavily_domain_filters_pass_through_to_selected_provider() -> None:
    """Domain filters pass through to the SELECTED provider (Tavily when primary)."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        allowed_domains=["a.com", "b.com"],
        blocked_domains=["x.com"],
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert tavily_search.calls[0].get("allowed_domains") == ["a.com", "b.com"]
    assert tavily_search.calls[0].get("blocked_domains") == ["x.com"]
    assert exa_search.calls == []


# ---------------------------------------------------------------------------
# spec-172 WS-A T-3: ONE bounded fall-through on raise-OR-empty (D-172-02)
# ---------------------------------------------------------------------------


def test_tavily_raise_falls_through_to_exa_once() -> None:
    """Tavily search raises → fall through to Exa EXACTLY once; built-in untouched."""
    tavily_search = _RaisingSearch()
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert len(exa_search.calls) == 1, "Exa runs once as the bounded fall-through"
    assert web_search.calls == [], "No second fall-through to built-in (bounded = one)"
    assert "mcp__tavily__tavily_search" in result.degraded_sources, (
        f"Tavily raise must record the tool name; got {result.degraded_sources}"
    )
    assert result.hits == [_exa_hit()]


def test_tavily_empty_falls_through_to_exa_once() -> None:
    """Tavily returns 0 results → fall through to Exa once; Tavily marker recorded."""
    tavily_search = _RecordingSearch([])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert len(exa_search.calls) == 1
    assert web_search.calls == []
    assert "mcp__tavily__tavily_search" in result.degraded_sources
    assert result.hits == [_exa_hit()]


def test_exa_empty_falls_through_to_builtin_once_when_tavily_absent() -> None:
    """Tavily absent, Exa empty → fall through to built-in once; both markers present."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=False,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert len(web_search.calls) == 1, "Built-in runs once as the bounded fall-through"
    assert "tavily" in result.degraded_sources, "Absent Tavily recorded"
    assert "mcp__exa__web_search_exa" in result.degraded_sources, "Empty Exa recorded"
    assert result.hits == [_builtin_hit()]


def test_second_provider_empty_does_NOT_fall_through_again() -> None:
    """Tavily empty → Exa empty → built-in NOT called (bounded = exactly one)."""
    tavily_search = _RecordingSearch([])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    result = _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert len(exa_search.calls) == 1, "Exa runs once as the single fall-through"
    assert web_search.calls == [], "Second empty does NOT trigger a further fall-through"
    assert result.hits == []
    assert "mcp__tavily__tavily_search" in result.degraded_sources
    assert "mcp__exa__web_search_exa" in result.degraded_sources


def test_fall_through_preserves_explicit_url_fetch() -> None:
    """Tavily search raises but its fetch returned the explicit-URL hit → preserved.

    The surviving Tavily fetch hit is kept AND Exa search runs once as the
    bounded fall-through (D-172-02).
    """
    explicit_hit = _stub_web_hit("https://example.org/article", "FetchedTavily")
    tavily_search = _RaisingSearch()
    tavily_fetch = _RecordingFetch([explicit_hit])
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch([_exa_hit()])
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch([_builtin_hit()])

    result = _call_tier2(
        "explain https://example.org/article",
        tier1_hits=_make_tier1_hits(2),
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert explicit_hit in result.hits, "Surviving Tavily fetch hit must be preserved"
    assert _exa_hit() in result.hits, "Exa fall-through search hits are merged in"
    assert len(exa_search.calls) == 1, "Exa search runs once as the fall-through"
    assert "mcp__tavily__tavily_search" in result.degraded_sources


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
