"""Lockstep Python implementation of the Tier 2 algorithm documented in
``.claude/skills/ai-research/handlers/tier2-web.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Tier2Result` -- aggregated dataclass returned to the synthesizer.
* :func:`detect_explicit_url` -- regex scan for an http(s) URL in the query.
* :func:`tier2_web` -- run a web search + (optional) fetch concurrently.

Web provider selection (spec-172 D-172-01): the Tier 2 web provider is a
capability-detected cascade -- Tavily (``mcp__tavily__tavily_search`` /
``mcp__tavily__tavily_extract``) is the PRIMARY provider, Exa
(``mcp__exa__web_search_exa`` / ``mcp__exa__web_fetch_exa``) is SECONDARY, and
the built-in WebSearch/WebFetch are the LAST resort. The first available
candidate is selected; every skipped higher-priority provider is recorded in
``degraded_sources`` (``"tavily"``, then ``"exa"``) -- a capability degrade,
never a raise (fail-soft).

One bounded fall-through (spec-172 D-172-02): if the SELECTED provider's
search RAISES or returns ZERO results, the failing tool is recorded in
``degraded_sources`` and the run falls through to the NEXT available provider
EXACTLY ONCE -- never a second time, even when the fall-through is also empty.
Surviving explicit-URL fetch hits from the primary are preserved across the
fall-through. All provider callables are injected by the caller; tests pass
recording fakes.
"""

from __future__ import annotations

import concurrent.futures
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

# --- Result types ------------------------------------------------------------


@dataclass
class Tier2Result:
    """Merged result of Tier 2 web invocation."""

    hits: list[dict] = field(default_factory=list)
    skipped: bool = False
    degraded_sources: list[str] = field(default_factory=list)


# --- Helpers -----------------------------------------------------------------

_URL_RE = re.compile(r"https?://\S+")

# Skip heuristic threshold -- Tier 2 short-circuits when Tier 1 already
# returned at least this many high-quality hits AND no explicit URL was
# referenced. Documented in ``tier2-web.md``.
_SKIP_THRESHOLD = 5

# Provider tool names recorded in ``degraded_sources`` on a per-call failure.
# Tavily is the primary provider, Exa the secondary (their MCP tool names); the
# built-in WebSearch / WebFetch are the last resort (their short names).
_TAVILY_SEARCH_TOOL = "mcp__tavily__tavily_search"
# Single-URL fetch maps to Tavily's ``tavily_extract`` (which wraps a
# one-element URL array); the injected callable hides that shape.
_TAVILY_FETCH_TOOL = "mcp__tavily__tavily_extract"
_EXA_SEARCH_TOOL = "mcp__exa__web_search_exa"
_EXA_FETCH_TOOL = "mcp__exa__web_fetch_exa"
_BUILTIN_SEARCH_TOOL = "web_search"
_BUILTIN_FETCH_TOOL = "web_fetch"


def detect_explicit_url(query: str) -> str | None:
    """Return the first http(s) URL in the query, or ``None`` if absent."""
    match = _URL_RE.search(query)
    return match.group(0) if match else None


# --- Concurrent dispatch -----------------------------------------------------


_SearchCallable = Callable[..., list]
_FetchCallable = Callable[..., list]


@dataclass(frozen=True)
class _Candidate:
    """A capability-detected provider in the Tier 2 cascade."""

    available: bool
    search_fn: _SearchCallable
    fetch_fn: _FetchCallable
    search_tool: str
    fetch_tool: str
    # ``degraded_sources`` marker recorded when this provider is skipped
    # because a higher-priority one was selected. The built-in last resort has
    # no marker (it is the zero-config floor and is always available).
    absent_marker: str | None


def _run_provider(
    candidate: _Candidate,
    query: str,
    explicit_url: str | None,
    search_kwargs: dict,
) -> tuple[list[dict], bool, list[str]]:
    """Run one provider's search (+ optional fetch) concurrently.

    Returns ``(hits, search_failed, failed_tools)`` where ``search_failed`` is
    True when the search call raised OR returned zero hits (the D-172-02
    fall-through trigger) and ``failed_tools`` lists the tool names of any
    call that raised (recorded in ``degraded_sources``).
    """
    plan: list[tuple[str, concurrent.futures.Future]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        search_future = pool.submit(candidate.search_fn, query, **search_kwargs)
        plan.append((candidate.search_tool, search_future))
        if explicit_url is not None:
            plan.append((candidate.fetch_tool, pool.submit(candidate.fetch_fn, explicit_url)))

        hits: list[dict] = []
        search_failed = False
        failed_tools: list[str] = []
        future_to_name = {future: name for name, future in plan}
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                returned = future.result()
            except Exception:
                # Record the failed tool so the synthesizer can surface a
                # degraded-mode warning; keep any surviving call's results.
                failed_tools.append(name)
                if future is search_future:
                    search_failed = True
                continue
            if future is search_future and not returned:
                # Empty search is a fall-through trigger (D-172-02).
                search_failed = True
            if returned:
                hits.extend(returned)
    return hits, search_failed, failed_tools


def tier2_web(
    query: str,
    *,
    tier1_hits: list,
    tavily_search: _SearchCallable,
    tavily_fetch: _FetchCallable,
    tavily_available: bool,
    exa_search: _SearchCallable,
    exa_fetch: _FetchCallable,
    web_search: _SearchCallable,
    web_fetch: _FetchCallable,
    exa_available: bool,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> Tier2Result:
    """Dispatch the chosen web search (and optional fetch) per the Tier 2 algorithm.

    Skip heuristic: if ``len(tier1_hits) >= 5`` and the query has no
    explicit URL, return immediately with ``skipped=True`` (no provider is
    selected, so nothing is degraded).

    Provider selection (D-172-01): a capability-detected cascade -- Tavily
    primary, Exa secondary, built-in last resort. The first available
    candidate is the primary; each skipped higher-priority candidate appends
    its marker (``"tavily"``, then ``"exa"``) to ``degraded_sources`` (the
    built-in floor is always available and has no marker).

    Bounded fall-through (D-172-02): if the selected provider's search raises
    OR returns zero hits, the failing tool is recorded and the run falls
    through to the NEXT available provider EXACTLY ONCE -- never a second
    time. Surviving explicit-URL fetch hits from the primary are preserved.

    When a provider runs, the search is always invoked; if the query has an
    explicit URL, the fetch is invoked in parallel on that URL. Domain
    filters pass through to the search call only when set.
    """
    explicit_url = detect_explicit_url(query)

    if len(tier1_hits) >= _SKIP_THRESHOLD and explicit_url is None:
        return Tier2Result(hits=[], skipped=True, degraded_sources=[])

    # Ordered cascade -- Tavily, Exa, built-in (built-in is always available).
    candidates = [
        _Candidate(
            available=tavily_available,
            search_fn=tavily_search,
            fetch_fn=tavily_fetch,
            search_tool=_TAVILY_SEARCH_TOOL,
            fetch_tool=_TAVILY_FETCH_TOOL,
            absent_marker="tavily",
        ),
        _Candidate(
            available=exa_available,
            search_fn=exa_search,
            fetch_fn=exa_fetch,
            search_tool=_EXA_SEARCH_TOOL,
            fetch_tool=_EXA_FETCH_TOOL,
            absent_marker="exa",
        ),
        _Candidate(
            available=True,
            search_fn=web_search,
            fetch_fn=web_fetch,
            search_tool=_BUILTIN_SEARCH_TOOL,
            fetch_tool=_BUILTIN_FETCH_TOOL,
            absent_marker=None,
        ),
    ]

    degraded: list[str] = []
    # Walk the cascade: skipped higher-priority providers record their marker
    # (capability degrade, NOT the fall-through). The first available
    # candidate is the primary; the next available one is the bounded
    # fall-through target.
    available = [c for c in candidates if c.available]
    for skipped in candidates:
        if skipped.available:
            break
        if skipped.absent_marker is not None:
            degraded.append(skipped.absent_marker)

    primary = available[0]
    fallback = available[1] if len(available) > 1 else None

    search_kwargs: dict = {}
    if allowed_domains is not None:
        search_kwargs["allowed_domains"] = list(allowed_domains)
    if blocked_domains is not None:
        search_kwargs["blocked_domains"] = list(blocked_domains)

    hits, search_failed, failed_tools = _run_provider(primary, query, explicit_url, search_kwargs)
    degraded.extend(failed_tools)

    if search_failed:
        # Record the primary's search tool as degraded (covers the empty-result
        # case; a raise is already captured in ``failed_tools``).
        if primary.search_tool not in degraded:
            degraded.append(primary.search_tool)
        # Single bounded fall-through -- run the next available provider's
        # search once and merge its hits. NO loop: even an empty fall-through
        # does not trigger a further one (D-172-02). Surviving primary
        # explicit-URL fetch hits in ``hits`` are preserved (we merge).
        if fallback is not None:
            fb_kwargs = dict(search_kwargs)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(fallback.search_fn, query, **fb_kwargs)
                try:
                    fb_hits = future.result()
                except Exception:
                    degraded.append(fallback.search_tool)
                    fb_hits = []
            if fb_hits:
                hits.extend(fb_hits)
            elif fallback.search_tool not in degraded:
                # An empty (or raised) fall-through search records its tool
                # too -- but does NOT trigger a further fall-through (bounded
                # = exactly one, D-172-02).
                degraded.append(fallback.search_tool)

    return Tier2Result(hits=hits, skipped=False, degraded_sources=degraded)


__all__: Iterable[str] = (
    "Tier2Result",
    "detect_explicit_url",
    "tier2_web",
)
