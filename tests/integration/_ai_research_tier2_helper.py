"""Lockstep Python implementation of the Tier 2 algorithm documented in
``.claude/skills/ai-research/handlers/tier2-web.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Tier2Result` -- aggregated dataclass returned to the synthesizer.
* :func:`detect_explicit_url` -- regex scan for an http(s) URL in the query.
* :func:`tier2_web` -- run a web search + (optional) fetch concurrently.

Web provider selection (notebooklm-async-tier3 D6/D7): Exa
(``mcp__exa__web_search_exa`` / ``mcp__exa__web_fetch_exa``) is the PRIMARY
provider. The built-in WebSearch/WebFetch are the FALLBACK used when Exa is
unavailable; in that case ``"exa"`` is recorded in ``degraded_sources``
(fail-soft: absent provider skipped silently, recorded, never raised). All
four callables are injected by the caller; tests pass recording fakes.
"""

from __future__ import annotations

import concurrent.futures
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from tests.integration._ai_research_capability import is_available

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
# Exa is the primary provider (its MCP tool names); the built-in WebSearch /
# WebFetch are the fallback (their short names).
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


def tier2_web(
    query: str,
    *,
    tier1_hits: list,
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

    Provider selection (D6): when ``exa_available`` is True, Exa is the
    primary provider (``exa_search`` / ``exa_fetch``). When it is False, fall
    back to the built-in ``web_search`` / ``web_fetch`` and record ``"exa"``
    in ``degraded_sources`` (D7 fail-soft -- absent provider skipped
    silently, recorded, never raised).

    When Tier 2 runs, the search is always invoked; if the query has an
    explicit URL, the fetch is invoked in parallel on that URL. Domain
    filters pass through to the search call only when set. A per-call
    exception in the chosen provider records that tool's name in
    ``degraded_sources`` and continues (never re-raised).
    """
    explicit_url = detect_explicit_url(query)

    if len(tier1_hits) >= _SKIP_THRESHOLD and explicit_url is None:
        return Tier2Result(hits=[], skipped=True, degraded_sources=[])

    # Provider selection -- Exa primary, built-in fallback (D6/D7). The
    # caller's ``exa_available`` boolean is routed through the shared
    # capability guard so absence has identical semantics across every tier
    # (notebooklm-async-tier3 D7; the boolean is wrapped as a trivial probe).
    degraded: list[str] = []
    if is_available(lambda: exa_available):
        search_fn: _SearchCallable = exa_search
        fetch_fn: _FetchCallable = exa_fetch
        search_tool = _EXA_SEARCH_TOOL
        fetch_tool = _EXA_FETCH_TOOL
    else:
        search_fn = web_search
        fetch_fn = web_fetch
        search_tool = _BUILTIN_SEARCH_TOOL
        fetch_tool = _BUILTIN_FETCH_TOOL
        # Absent provider is recorded but never raises (D7).
        degraded.append("exa")

    search_kwargs: dict = {}
    if allowed_domains is not None:
        search_kwargs["allowed_domains"] = list(allowed_domains)
    if blocked_domains is not None:
        search_kwargs["blocked_domains"] = list(blocked_domains)

    plan: list[tuple[str, concurrent.futures.Future]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        plan.append((search_tool, pool.submit(search_fn, query, **search_kwargs)))
        if explicit_url is not None:
            plan.append((fetch_tool, pool.submit(fetch_fn, explicit_url)))

        merged: list[dict] = []
        # Iterate by completion order so partial successes are preserved.
        future_to_name = {future: name for name, future in plan}
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                hits = future.result()
            except Exception:
                # Resilience requirement: record the failed tool so the
                # synthesizer can surface a degraded-mode warning, but keep
                # any results from the surviving tool.
                degraded.append(name)
                continue
            if hits:
                merged.extend(hits)

    return Tier2Result(hits=merged, skipped=False, degraded_sources=degraded)


__all__: Iterable[str] = (
    "Tier2Result",
    "detect_explicit_url",
    "tier2_web",
)
