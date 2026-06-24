"""Tests for spec-111 T-2.5/T-2.6 + notebooklm-async-tier3 T-2.1 + spec-174 --
/ai-research Tier 2 web search.

Spec acceptance (spec-111):
    Tier 2 (web) implemented in ``tier2-web.md`` -- handler invokes a web
    search tool (raw web results) and a web fetch tool (specific URL when
    referenced) IN PARALLEL when Tier 1 yielded fewer than 5 high-quality
    hits OR the user query referenced an explicit URL. Domain filters
    ``--allowed-domains`` and ``--blocked-domains`` pass through to the
    search tool. Skip path: tier1 ≥5 hits without explicit URL.

Spec acceptance (spec-174 D-174-01..05):
    Tier 2 is a CONCURRENT FAN-OUT: every available provider (Tavily,
    Exa, built-in WebSearch) runs at once, and the results are merged and
    deduped by URL with the tie-break Tavily > Exa > built-in (D-174-03).
    There is NO first-available cascade and NO bounded fall-through
    (D-174-04 supersedes D-172-02). A provider that is absent, raises, or
    returns zero is recorded in ``degraded_sources``; it never suppresses
    the others. The skip heuristic and the public signature are unchanged
    (D-174-05).

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_tier2_helper.py`` mirrors the
algorithm 1:1; these tests exercise the helper.
"""

from __future__ import annotations

import threading
import time

import pytest

from tests.integration._ai_research_tier1_helper import Tier1Hit
from tests.integration._ai_research_tier2_helper import (
    Tier2Result,
    tier2_web,
)


def test_tier2_web_accepts_tavily_provider_params() -> None:
    """tier2_web must accept tavily_search/tavily_fetch + tavily_available (signature)."""
    import inspect

    from tests.integration._ai_research_tier2_helper import tier2_web as _fn

    params = inspect.signature(_fn).parameters
    for name in ("tavily_search", "tavily_fetch", "tavily_available"):
        assert name in params, f"tier2_web missing required Tavily param {name!r}"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _ConcurrencyTracker:
    """Tracks peak overlap of provider calls to prove parallelism deterministically.

    Each call increments an in-flight counter on entry and decrements on exit,
    recording the high-water mark under a lock. A peak ``>= 2`` proves at least
    two calls were in flight at the same instant -- a wall-clock-free signal that
    is immune to scheduler jitter (unlike a start-time delta bound). Recorders
    that share one tracker register their overlap into the same peak.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._in_flight = 0
        self.peak = 0

    def __enter__(self) -> _ConcurrencyTracker:
        with self._lock:
            self._in_flight += 1
            self.peak = max(self.peak, self._in_flight)
        return self

    def __exit__(self, *_exc: object) -> None:
        with self._lock:
            self._in_flight -= 1


class _RecordingSearch:
    """Records every search call with its kwargs (for filter assertions).

    Used for the Tavily, Exa, and built-in WebSearch providers alike -- the
    call shape is identical, only the injected callable differs. An optional
    shared ``_ConcurrencyTracker`` records call overlap for parallelism asserts.
    """

    def __init__(
        self, hits: list | None = None, tracker: _ConcurrencyTracker | None = None
    ) -> None:
        self.calls: list[dict] = []
        self.hits = hits or []
        self.start_times: list[float] = []
        self._tracker = tracker

    def __call__(self, query: str, **kwargs) -> list:
        self.start_times.append(time.perf_counter())
        self.calls.append({"query": query, **kwargs})
        if self._tracker is not None:
            with self._tracker:
                time.sleep(0.05)
        else:
            time.sleep(0.05)
        return list(self.hits)


class _RecordingFetch:
    """Records every fetch call with the URL it was given.

    Used for the Tavily, Exa, and built-in WebFetch providers alike. An optional
    shared ``_ConcurrencyTracker`` records call overlap for parallelism asserts.
    """

    def __init__(
        self, hits: list | None = None, tracker: _ConcurrencyTracker | None = None
    ) -> None:
        self.calls: list[str] = []
        self.hits = hits or []
        self.start_times: list[float] = []
        self._tracker = tracker

    def __call__(self, url: str, **_kwargs) -> list:
        self.start_times.append(time.perf_counter())
        self.calls.append(url)
        if self._tracker is not None:
            with self._tracker:
                time.sleep(0.05)
        else:
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
    """Thin wrapper to keep the keyword-only signature DRY in tests.

    The public ``tier2_web`` signature is unchanged under spec-174 (D-174-05);
    this wrapper still defaults ``tavily_available=False`` with no-op recorders
    so the Exa / built-in tests exercise the fan-out without per-call edits.
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


def _tavily_hit() -> dict:
    return _stub_web_hit("https://tavily.example/a", "Tavily")


def _exa_hit() -> dict:
    return _stub_web_hit("https://exa.example/a", "Exa")


def _builtin_hit() -> dict:
    return _stub_web_hit("https://builtin.example/a", "Builtin")


# ---------------------------------------------------------------------------
# spec-174 D-174-01: every available provider runs concurrently (fan-out)
# ---------------------------------------------------------------------------


def test_all_available_providers_run_concurrently() -> None:
    """All three available providers' searches run once each (fan-out, D-174-01).

    Arrange: Tavily + Exa available (built-in is always available); three
    Tier 1 hits so Tier 2 runs; no explicit URL.

    Act: invoke ``tier2_web``.

    Assert: every available provider's search ran exactly once; the merged
    hits include each provider's distinct URL; nothing is degraded.
    """
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

    assert isinstance(result, Tier2Result)
    assert len(tavily_search.calls) == 1, "Tavily search must run under fan-out"
    assert len(exa_search.calls) == 1, "Exa search must run under fan-out"
    assert len(web_search.calls) == 1, "Built-in search must run under fan-out"
    assert result.degraded_sources == [], "All providers ran and returned hits"
    # Merged set across all providers (distinct URLs, priority order preserved).
    assert result.hits == [_tavily_hit(), _exa_hit(), _builtin_hit()]
    assert result.skipped is False


def test_fanout_runs_exa_and_builtin_when_tavily_absent() -> None:
    """Tavily absent → Exa + built-in both run; ``"tavily"`` recorded (D-174-01/04)."""
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

    assert tavily_search.calls == [], "Absent Tavily must NOT run"
    assert len(exa_search.calls) == 1, "Exa must run under fan-out when Tavily is absent"
    assert len(web_search.calls) == 1, "Built-in must also run under fan-out"
    assert "tavily" in result.degraded_sources, "Absent Tavily recorded (D-174-01)"
    assert result.hits == [_exa_hit(), _builtin_hit()]


def test_fanout_runs_only_builtin_when_tavily_and_exa_absent() -> None:
    """Tavily + Exa absent → only built-in runs; both markers recorded (D-174-01)."""
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

    assert len(web_search.calls) == 1, "Built-in must run when Tavily+Exa absent"
    assert tavily_search.calls == []
    assert exa_search.calls == []
    assert "tavily" in result.degraded_sources
    assert "exa" in result.degraded_sources
    assert result.hits == [_builtin_hit()]


def test_explicit_url_fetch_fans_out_across_available_providers() -> None:
    """With an explicit URL, every available provider's fetch runs (D-174-01)."""
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch([_stub_web_hit("https://fetched.tavily/x", "TF")])
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch([_stub_web_hit("https://fetched.exa/x", "EF")])
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch([_stub_web_hit("https://fetched.builtin/x", "BF")])

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

    # Each available provider's fetch receives the explicit URL.
    assert tavily_fetch.calls == ["https://example.org/article"]
    assert exa_fetch.calls == ["https://example.org/article"]
    assert web_fetch.calls == ["https://example.org/article"]
    # Each available provider's search also runs in parallel.
    assert len(tavily_search.calls) == 1
    assert len(exa_search.calls) == 1
    assert len(web_search.calls) == 1
    assert result.skipped is False


def test_no_degraded_when_all_providers_return_hits() -> None:
    """Every available provider returning hits leaves ``degraded_sources`` empty."""
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


# ---------------------------------------------------------------------------
# spec-174 D-174-03: merge + dedup by URL, tie-break Tavily > Exa > built-in
# ---------------------------------------------------------------------------


def test_dedup_keeps_tavily_row_on_shared_url() -> None:
    """When Tavily and Exa return the SAME url, the Tavily row is kept (D-174-03).

    Arrange: Tavily and Exa both return a hit with url ``https://shared/x``,
    distinguished by title; built-in returns a distinct url.

    Act: invoke ``tier2_web``.

    Assert: the merged hits contain exactly one row for the shared url and
    it is the Tavily row (higher priority wins the tie-break).
    """
    shared = "https://shared.example/x"
    tavily_row = _stub_web_hit(shared, "FromTavily")
    exa_row = _stub_web_hit(shared, "FromExa")
    tavily_search = _RecordingSearch([tavily_row])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([exa_row])
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

    shared_rows = [h for h in result.hits if h.get("url") == shared]
    assert len(shared_rows) == 1, f"Shared url must dedup to one row; got {shared_rows}"
    assert shared_rows[0] is tavily_row, "Tavily row wins the dedup tie-break (D-174-03)"
    assert exa_row not in result.hits, "Lower-priority Exa duplicate must be dropped"
    assert _builtin_hit() in result.hits, "Distinct built-in url is kept"


def test_dedup_keeps_exa_over_builtin_on_shared_url() -> None:
    """Exa beats built-in on a shared url when Tavily is absent (D-174-03)."""
    shared = "https://shared.example/y"
    exa_row = _stub_web_hit(shared, "FromExa")
    builtin_row = _stub_web_hit(shared, "FromBuiltin")
    exa_search = _RecordingSearch([exa_row])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([builtin_row])
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

    shared_rows = [h for h in result.hits if h.get("url") == shared]
    assert len(shared_rows) == 1
    assert shared_rows[0] is exa_row, "Exa row wins over built-in on the shared url"


def test_dedup_keeps_hits_without_url() -> None:
    """Hits lacking a ``url`` key are always kept (no dedup key) (D-174-03)."""
    tavily_no_url = {"title": "NoUrlTavily", "snippet": "s", "source": "web"}
    exa_no_url = {"title": "NoUrlExa", "snippet": "s", "source": "web"}
    tavily_search = _RecordingSearch([tavily_no_url])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([exa_no_url])
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

    assert tavily_no_url in result.hits, "url-less Tavily hit kept"
    assert exa_no_url in result.hits, "url-less Exa hit kept (not deduped against Tavily)"
    assert _builtin_hit() in result.hits


# ---------------------------------------------------------------------------
# spec-174 D-174-04: a raising / empty provider degrades but never suppresses
# others (no fall-through)
# ---------------------------------------------------------------------------


def test_raising_provider_records_degraded_does_not_suppress_others() -> None:
    """A raising provider records its tool but the other providers still run (D-174-04).

    Arrange: Tavily search raises; Exa + built-in return hits (all available).

    Act: invoke ``tier2_web``.

    Assert: the Tavily search tool is in ``degraded_sources``; Exa and
    built-in both ran exactly once and their hits are merged in.
    """
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

    assert "mcp__tavily__tavily_search" in result.degraded_sources, (
        f"Raising Tavily search must record the tool; got {result.degraded_sources}"
    )
    assert len(exa_search.calls) == 1, "Exa still runs (no suppression)"
    assert len(web_search.calls) == 1, "Built-in still runs (no fall-through gating)"
    assert _exa_hit() in result.hits
    assert _builtin_hit() in result.hits


def test_empty_provider_records_degraded_does_not_suppress_others() -> None:
    """A provider that returns zero hits records its tool but others still run (D-174-04)."""
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

    assert "mcp__tavily__tavily_search" in result.degraded_sources, (
        f"Empty Tavily search must record the tool; got {result.degraded_sources}"
    )
    assert len(exa_search.calls) == 1
    assert len(web_search.calls) == 1
    assert result.hits == [_exa_hit(), _builtin_hit()]


def test_every_provider_empty_records_all_and_returns_no_hits() -> None:
    """Every provider empty → all tools recorded; no fall-through retry (D-174-04)."""
    tavily_search = _RecordingSearch([])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([])
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

    # Each ran exactly once -- no second pass / fall-through.
    assert len(tavily_search.calls) == 1
    assert len(exa_search.calls) == 1
    assert len(web_search.calls) == 1
    assert "mcp__tavily__tavily_search" in result.degraded_sources
    assert "mcp__exa__web_search_exa" in result.degraded_sources
    assert "web_search" in result.degraded_sources
    assert result.hits == []


def test_builtin_search_exception_records_tool_name_and_continues() -> None:
    """A built-in search failure records the tool name; surviving providers contribute.

    Tavily + Exa absent (only built-in available); the built-in raises. Its
    tool name is recorded and the run returns without raising.
    """
    exa_search = _RecordingSearch([_exa_hit()])
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

    # "tavily" + "exa" for the absent providers AND the built-in tool name
    # for the per-call failure.
    assert "tavily" in result.degraded_sources
    assert "exa" in result.degraded_sources
    assert "web_search" in result.degraded_sources, (
        f"Built-in search failure must record the tool name; got {result.degraded_sources}"
    )
    assert result.hits == []


def test_raising_provider_preserves_its_surviving_fetch_hit() -> None:
    """A provider whose search raises still contributes its surviving fetch hit."""
    explicit_hit = _stub_web_hit("https://example.org/article", "FetchedTavily")
    tavily_search = _RaisingSearch()
    tavily_fetch = _RecordingFetch([explicit_hit])
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

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
    assert _exa_hit() in result.hits, "Exa search hits merged in (no suppression)"
    assert "mcp__tavily__tavily_search" in result.degraded_sources


def test_mixed_raise_and_empty_both_recorded_survivor_hits_returned() -> None:
    """One provider RAISES, another returns ZERO -> both recorded; survivor wins (D-174-04).

    Arrange: Tavily search raises; Exa search returns an empty list; built-in
    returns a hit. All three are available, so all three fan out.

    Act: invoke ``tier2_web``.

    Assert: both the raising Tavily tool AND the empty Exa tool land in
    ``degraded_sources`` (a raise and an empty result are both degrade signals);
    the surviving built-in's hit is still returned; no provider is suppressed and
    nothing is retried (each search ran exactly once).
    """
    tavily_search = _RaisingSearch()
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([])  # available but returns zero hits
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

    # Both degrade signals recorded -- the raise and the empty result alike.
    assert "mcp__tavily__tavily_search" in result.degraded_sources, (
        f"Raising Tavily search must be recorded; got {result.degraded_sources}"
    )
    assert "mcp__exa__web_search_exa" in result.degraded_sources, (
        f"Empty Exa search must be recorded; got {result.degraded_sources}"
    )
    # No suppression: every available provider ran exactly once (no fall-through).
    assert len(tavily_search.calls) == 1
    assert len(exa_search.calls) == 1
    assert len(web_search.calls) == 1
    # The surviving built-in hit is returned; the empty/raised providers add none.
    assert result.hits == [_builtin_hit()], (
        f"Only the surviving built-in hit should remain; got {result.hits}"
    )


# ---------------------------------------------------------------------------
# Domain filters pass through to EVERY available provider (D-174-01)
# ---------------------------------------------------------------------------


def test_domain_filters_pass_through_to_every_available_provider() -> None:
    """``--allowed-domains`` / ``--blocked-domains`` reach every available provider."""
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

    for label, search in (("tavily", tavily_search), ("exa", exa_search), ("builtin", web_search)):
        assert search.calls[0].get("allowed_domains") == ["a.com", "b.com"], (
            f"{label} search missing allowed_domains pass-through: {search.calls[0]}"
        )
        assert search.calls[0].get("blocked_domains") == ["x.com"], (
            f"{label} search missing blocked_domains pass-through: {search.calls[0]}"
        )


def test_websearch_invoked_with_filters() -> None:
    """``--allowed-domains`` flag passes through to the available search tool.

    Arrange: a query with no explicit URL, three Tier 1 hits (so Tier 2
    runs), ``allowed_domains=["a.com", "b.com"]``, Exa available (Tavily
    absent).

    Act: invoke ``tier2_web``.

    Assert: the Exa search received exactly one call with
    ``allowed_domains == ["a.com", "b.com"]`` and no fetch ran.
    """
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
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
        f"Expected exactly one Exa search call when tier2 runs; got {len(exa_search.calls)}"
    )
    assert exa_search.calls[0].get("allowed_domains") == ["a.com", "b.com"], (
        f"Search was not invoked with the allowed_domains pass-through: {exa_search.calls[0]}"
    )
    # Fetch must NOT be called when no explicit URL is in the query.
    assert exa_fetch.calls == [], "Fetch should not run when query has no explicit URL"


def test_websearch_invoked_with_blocked_filter() -> None:
    """Symmetric: ``--blocked-domains`` flag also passes through.

    Verified on the built-in path (Tavily + Exa absent) to prove pass-through
    is provider-agnostic.
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


def test_no_domain_kwargs_forwarded_when_filters_omitted() -> None:
    """With no domain filter set, the search call OMITS the domain kwargs entirely.

    Regression guard: the search must be invoked WITHOUT an ``allowed_domains``
    (or ``blocked_domains``) keyword when the caller passes neither. A helper that
    forwarded ``allowed_domains=None`` instead of omitting the kwarg would fail
    this test, since the recorded call kwargs would carry the key with a ``None``
    value rather than no key at all.

    Verified across every available provider (Tavily, Exa, built-in) to prove the
    omission is provider-agnostic.
    """
    tavily_search = _RecordingSearch([_tavily_hit()])
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()])
    web_fetch = _RecordingFetch()

    _call_tier2(
        "best practices for retries",
        tier1_hits=_make_tier1_hits(3),
        # allowed_domains / blocked_domains intentionally omitted (both default None).
        tavily_search=tavily_search,
        tavily_fetch=tavily_fetch,
        tavily_available=True,
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    for label, search in (("tavily", tavily_search), ("exa", exa_search), ("builtin", web_search)):
        call_kwargs = search.calls[0]
        assert "allowed_domains" not in call_kwargs, (
            f"{label} search must OMIT allowed_domains when no filter is set "
            f"(must not forward None); got {call_kwargs}"
        )
        assert "blocked_domains" not in call_kwargs, (
            f"{label} search must OMIT blocked_domains when no filter is set "
            f"(must not forward None); got {call_kwargs}"
        )


# ---------------------------------------------------------------------------
# T-2.6: skip when Tier 1 already yielded ≥5 hits and no explicit URL (D-174-05)
# ---------------------------------------------------------------------------


def test_tier2_skipped_when_tier1_yields_5_plus_hits() -> None:
    """Tier 2 MUST short-circuit when Tier 1 returned ≥5 hits without explicit URL.

    Arrange: 5 Tier 1 hits, no explicit URL in the query, no domain filters.

    Act: invoke ``tier2_web``.

    Assert: no provider was called, and the result flags ``skipped=True``.
    The skip runs before fan-out, so nothing is recorded in
    ``degraded_sources``.
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
        "Skip path short-circuits before fan-out; nothing is degraded"
    )


# ---------------------------------------------------------------------------
# Edge cases that pin down the skip heuristic
# ---------------------------------------------------------------------------


def test_tier2_runs_when_tier1_below_threshold() -> None:
    """≤4 Tier 1 hits with no explicit URL still triggers Tier 2."""
    exa_search = _RecordingSearch([_stub_web_hit()])
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_stub_web_hit("https://builtin.example/b")])
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
    web_search = _RecordingSearch([_stub_web_hit("https://builtin.example/c")])
    web_fetch = _RecordingFetch([_stub_web_hit("https://builtin.example/d")])

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
    """A provider's search and fetch overlap in flight (parallel, D-174-01).

    Verified on the Exa path (Tavily absent, Exa available). Rather than asserting
    a brittle start-time delta, both Exa calls share one ``_ConcurrencyTracker``;
    a recorded peak of >= 2 proves the search and the fetch were in flight at the
    same instant -- if they ran sequentially the peak would be 1.
    """
    tracker = _ConcurrencyTracker()
    exa_search = _RecordingSearch([_stub_web_hit()], tracker=tracker)
    exa_fetch = _RecordingFetch([_stub_web_hit()], tracker=tracker)
    web_search = _RecordingSearch([_stub_web_hit("https://builtin.example/e")])
    web_fetch = _RecordingFetch([_stub_web_hit("https://builtin.example/f")])

    _call_tier2(
        "describe https://example.org/article",
        tier1_hits=_make_tier1_hits(2),
        exa_search=exa_search,
        exa_fetch=exa_fetch,
        web_search=web_search,
        web_fetch=web_fetch,
        exa_available=True,
    )

    assert exa_search.calls, "Exa search must run"
    assert exa_fetch.calls, "Exa fetch must run (explicit URL present)"
    assert tracker.peak >= 2, (
        "Expected the Exa search and fetch to overlap in flight (parallel); "
        f"observed peak concurrency {tracker.peak}"
    )


def test_providers_fan_out_in_parallel() -> None:
    """Available providers' searches overlap in flight (parallel fan-out, D-174-01).

    Each recording search sleeps 50ms; under a sequential cascade only one would
    ever be in flight (peak 1). All three searches share one
    ``_ConcurrencyTracker``; a recorded peak of >= 2 proves at least two providers
    overlapped -- a wall-clock-free signal robust to scheduler jitter.
    """
    tracker = _ConcurrencyTracker()
    tavily_search = _RecordingSearch([_tavily_hit()], tracker=tracker)
    tavily_fetch = _RecordingFetch()
    exa_search = _RecordingSearch([_exa_hit()], tracker=tracker)
    exa_fetch = _RecordingFetch()
    web_search = _RecordingSearch([_builtin_hit()], tracker=tracker)
    web_fetch = _RecordingFetch()

    _call_tier2(
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

    assert len(tavily_search.calls) == 1
    assert len(exa_search.calls) == 1
    assert len(web_search.calls) == 1
    assert tracker.peak >= 2, (
        "Expected at least two providers' searches to overlap in flight (parallel "
        f"fan-out); observed peak concurrency {tracker.peak}"
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
