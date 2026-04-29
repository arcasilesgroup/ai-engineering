"""Lockstep Python implementation of the Tier 2 algorithm documented in
``.claude/skills/ai-research/handlers/tier2-web.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Tier2Result` -- aggregated dataclass returned to the synthesizer.
* :func:`detect_explicit_url` -- regex scan for an http(s) URL in the query.
* :func:`tier2_web` -- run WebSearch + (optional) WebFetch concurrently.

The WebSearch / WebFetch callables are injected by the caller; tests pass
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


def detect_explicit_url(query: str) -> str | None:
    """Return the first http(s) URL in the query, or ``None`` if absent."""
    match = _URL_RE.search(query)
    return match.group(0) if match else None


# --- Concurrent dispatch -----------------------------------------------------


_WebSearchCallable = Callable[..., list]
_WebFetchCallable = Callable[..., list]


def tier2_web(
    query: str,
    *,
    tier1_hits: list,
    web_search: _WebSearchCallable,
    web_fetch: _WebFetchCallable,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> Tier2Result:
    """Dispatch WebSearch (and optional WebFetch) per the Tier 2 algorithm.

    Skip heuristic: if ``len(tier1_hits) >= 5`` and the query has no
    explicit URL, return immediately with ``skipped=True``.

    Otherwise WebSearch is invoked; if the query has an explicit URL,
    WebFetch is invoked in parallel on that URL. Domain filters pass
    through to WebSearch only when set.
    """
    explicit_url = detect_explicit_url(query)

    if len(tier1_hits) >= _SKIP_THRESHOLD and explicit_url is None:
        return Tier2Result(hits=[], skipped=True, degraded_sources=[])

    web_search_kwargs: dict = {}
    if allowed_domains is not None:
        web_search_kwargs["allowed_domains"] = list(allowed_domains)
    if blocked_domains is not None:
        web_search_kwargs["blocked_domains"] = list(blocked_domains)

    plan: list[tuple[str, concurrent.futures.Future]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        plan.append(("web_search", pool.submit(web_search, query, **web_search_kwargs)))
        if explicit_url is not None:
            plan.append(("web_fetch", pool.submit(web_fetch, explicit_url)))

        merged: list[dict] = []
        degraded: list[str] = []
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
