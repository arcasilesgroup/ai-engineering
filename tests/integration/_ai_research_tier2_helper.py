"""Lockstep Python implementation of the Tier 2 algorithm documented in
``.claude/skills/ai-research/handlers/tier2-web.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Tier2Result` -- aggregated dataclass returned to the synthesizer.
* :func:`detect_explicit_url` -- regex scan for an http(s) URL in the query.
* :func:`tier2_web` -- fan out a web search + (optional) fetch across every
  available provider concurrently, then merge + dedup by URL.

Web provider fan-out (spec-174 D-174-01): the Tier 2 web layer runs EVERY
available provider CONCURRENTLY -- Tavily (``mcp__tavily__tavily_search`` /
``mcp__tavily__tavily_extract``), Exa (``mcp__exa__web_search_exa`` /
``mcp__exa__web_fetch_exa``), and the built-in WebSearch/WebFetch -- rather
than selecting only the first available. Each provider's search (and, when the
query references a URL, its single-URL fetch) is dispatched at once on an outer
executor, so the wall-clock is the slowest provider, not the sum. There is NO
first-available cascade and NO bounded fall-through: D-174-04 supersedes the
spec-172 D-172-02 fall-through, because running all providers IS the resilience.

Degraded recording (spec-174 D-174-04): an absent provider appends its marker
(``"tavily"``, then ``"exa"``; the built-in floor has no marker), and an
available provider whose search raises OR returns zero hits appends its
``search_tool`` name -- but it never suppresses the other providers. A degrade
is a fail-soft note, never a raise.

Merge + dedup by URL (spec-174 D-174-03): the per-provider hits are merged in
priority order Tavily -> Exa -> built-in; the first row seen for a given ``url``
wins, so on a duplicate URL the higher-priority provider's row is kept. Hits
without a ``url`` key carry no dedup key and are always kept.

All provider callables are injected by the caller; tests pass recording fakes.
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
# Tavily, Exa, and the built-in WebSearch/WebFetch all fan out concurrently;
# their MCP / short tool names are recorded when a provider raises or returns
# zero hits.
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
    """One capability-detected provider in the Tier 2 fan-out (priority order)."""

    available: bool
    search_fn: _SearchCallable
    fetch_fn: _FetchCallable
    search_tool: str
    fetch_tool: str
    # ``degraded_sources`` marker recorded when this provider is ABSENT (its
    # capability flag is False). The built-in floor has no marker (it is the
    # zero-config floor and is always available).
    absent_marker: str | None


def _run_provider(
    candidate: _Candidate,
    query: str,
    explicit_url: str | None,
    search_kwargs: dict,
) -> tuple[list[dict], bool, list[str]]:
    """Run one provider's search (+ optional fetch) concurrently.

    Returns ``(hits, search_failed, failed_tools)`` where ``search_failed`` is
    True when the search call raised OR returned zero hits (so the provider's
    ``search_tool`` is recorded in ``degraded_sources``) and ``failed_tools``
    lists the tool names of any call that raised. There is no fall-through: a
    failed provider simply contributes whatever survived and is recorded.
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
                # Empty search is a degrade signal (D-174-04) -- recorded, but
                # it does NOT suppress the other providers.
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
    """Fan out the web search (and optional fetch) across all available providers.

    Skip heuristic (D-174-05, unchanged): if ``len(tier1_hits) >= 5`` and the
    query has no explicit URL, return immediately with ``skipped=True`` (no
    provider runs, so nothing is degraded).

    Fan-out (D-174-01): build the candidates in priority order Tavily -> Exa ->
    built-in. Absent providers append their marker (``"tavily"``, then
    ``"exa"``) to ``degraded_sources`` (the built-in floor is always available
    and has no marker). EVERY available provider's search (and, when the query
    has an explicit URL, its fetch) runs CONCURRENTLY -- each ``_run_provider``
    call is fanned out across an outer ``ThreadPoolExecutor`` so wall-clock is
    the slowest provider, not the sum. There is no first-available selection and
    no bounded fall-through (D-174-04 supersedes D-172-02).

    Degraded (D-174-04): for each available provider whose search raised OR
    returned zero hits, record its ``search_tool``; plus any raised fetch tool.
    Markers are deduped preserving first-seen order. A degrade never suppresses
    the other providers.

    Merge + dedup by URL (D-174-03): iterate the provider hits in PRIORITY order
    (Tavily -> Exa -> built-in); add each hit whose ``url`` was not already seen
    (so Tavily wins a duplicate URL). Hits without a ``url`` key are always kept.

    Domain filters pass through to EVERY available provider's search call only
    when set.
    """
    explicit_url = detect_explicit_url(query)

    if len(tier1_hits) >= _SKIP_THRESHOLD and explicit_url is None:
        return Tier2Result(hits=[], skipped=True, degraded_sources=[])

    # Candidates in priority order -- Tavily, Exa, built-in (built-in is always
    # available). Priority drives both the fan-out iteration and the dedup
    # tie-break (Tavily > Exa > built-in).
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
    # Absent providers record their marker (capability degrade, fail-soft).
    for candidate in candidates:
        if not candidate.available and candidate.absent_marker is not None:
            degraded.append(candidate.absent_marker)

    available = [c for c in candidates if c.available]

    search_kwargs: dict = {}
    if allowed_domains is not None:
        search_kwargs["allowed_domains"] = list(allowed_domains)
    if blocked_domains is not None:
        search_kwargs["blocked_domains"] = list(blocked_domains)

    # Fan out: run every available provider concurrently on an outer executor.
    # Each provider keeps the priority-order index so the merge + dedup stays
    # deterministic regardless of completion order.
    provider_hits: list[list[dict]] = [[] for _ in available]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(available))) as pool:
        future_to_index = {
            pool.submit(_run_provider, candidate, query, explicit_url, dict(search_kwargs)): index
            for index, candidate in enumerate(available)
        }
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            candidate = available[index]
            hits, search_failed, failed_tools = future.result()
            provider_hits[index] = hits
            for tool in failed_tools:
                if tool not in degraded:
                    degraded.append(tool)
            if search_failed and candidate.search_tool not in degraded:
                degraded.append(candidate.search_tool)

    # Merge + dedup by URL in priority order (Tavily -> Exa -> built-in). The
    # first row seen for a given URL wins; url-less hits are always kept.
    merged: list[dict] = []
    seen_urls: set[str] = set()
    for hits in provider_hits:
        for hit in hits:
            url = hit.get("url")
            if url is None:
                merged.append(hit)
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(hit)

    return Tier2Result(hits=merged, skipped=False, degraded_sources=degraded)


__all__: Iterable[str] = (
    "Tier2Result",
    "detect_explicit_url",
    "tier2_web",
)
