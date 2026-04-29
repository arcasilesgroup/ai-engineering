"""Lockstep Python implementation of the Tier 1 algorithm documented in
``.claude/skills/ai-research/handlers/tier1-free-mcps.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Tier1Hit`     -- dataclass for a single MCP result.
* :class:`Tier1Result`  -- dataclass aggregating deduped hits + degraded list.
* :func:`classify_tags` -- query → MCP-applicability tag set.
* :func:`dedup_hits`    -- collapse duplicate URLs (web) and repo+path (code).
* :func:`tier1_free_mcps` -- run all applicable MCPs concurrently and merge.

The MCP callables are passed in by the caller so tests can inject mocks.
"""

from __future__ import annotations

import concurrent.futures
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse

# --- Result types ------------------------------------------------------------


@dataclass
class Tier1Hit:
    """A single Tier 1 result.

    Web/doc sources populate ``url``; code-search hits populate ``repo`` and
    ``path``. ``source`` records which MCP produced the hit (for
    citations/dedup tracing).
    """

    title: str
    url: str | None
    snippet: str
    source: str
    repo: str | None = None
    path: str | None = None


@dataclass
class Tier1Result:
    """Aggregated, deduped output of the Tier 1 dispatch."""

    hits: list[Tier1Hit] = field(default_factory=list)
    degraded_sources: list[str] = field(default_factory=list)


# --- Classifier --------------------------------------------------------------

_LIBRARY_RE = re.compile(
    r"\b("
    r"react|vue|angular|django|flask|fastapi|rails|express|nestjs|"
    r"next\.js|nextjs|nuxt|prisma|spring|laravel|tailwind|axios|"
    r"pandas|numpy|pytorch|tensorflow|"
    r"library|framework|sdk|cli"
    r")\b",
    re.IGNORECASE,
)

_MICROSOFT_RE = re.compile(
    r"\b("
    r"azure|microsoft|\.net|asp\.net|ef core|entity framework|"
    r"dotnet|powershell|teams"
    r")\b",
    re.IGNORECASE,
)

_CODE_PATTERN_RE = re.compile(
    r"\b("
    r"github|how do|how does|how to|"
    r"implementations? of|real[- ]world|"
    r"projects? (?:do|use|implement)|"
    r"patterns?|examples?"
    r")\b",
    re.IGNORECASE,
)

_COMPARATIVE_RE = re.compile(
    r"\b(vs|versus|compare|difference between|alternatives?)\b",
    re.IGNORECASE,
)

_URL_RE = re.compile(r"https?://\S+")


def classify_tags(query: str) -> dict:
    """Compute the applicability tag set described in ``classify-query.md``.

    The tags drive which Tier 1 MCPs the dispatcher invokes. Returns a dict
    with keys ``mentions_library``, ``mentions_microsoft``,
    ``mentions_code_pattern``, ``is_comparative``, and ``explicit_url``.
    """
    url_match = _URL_RE.search(query)
    return {
        "mentions_library": bool(_LIBRARY_RE.search(query)),
        "mentions_microsoft": bool(_MICROSOFT_RE.search(query)),
        "mentions_code_pattern": bool(_CODE_PATTERN_RE.search(query)),
        "is_comparative": bool(_COMPARATIVE_RE.search(query)),
        "explicit_url": url_match.group(0) if url_match else None,
    }


# --- Dedup -------------------------------------------------------------------


def _normalize_url(url: str) -> str:
    """Strip query string and fragment from a URL for dedup comparison."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def dedup_hits(hits: Iterable[Tier1Hit]) -> list[Tier1Hit]:
    """Remove duplicate hits.

    Two hits collide when:

    * Both have a ``url`` and the URL (minus query/fragment) matches, OR
    * Both have ``repo`` and ``path`` and the ``(repo, path)`` tuple matches.

    First occurrence wins (stable order).
    """
    seen_urls: set[str] = set()
    seen_paths: set[tuple[str, str]] = set()
    deduped: list[Tier1Hit] = []
    for hit in hits:
        if hit.url:
            key = _normalize_url(hit.url)
            if key in seen_urls:
                continue
            seen_urls.add(key)
            deduped.append(hit)
            continue
        if hit.repo and hit.path:
            key_pair = (hit.repo, hit.path)
            if key_pair in seen_paths:
                continue
            seen_paths.add(key_pair)
            deduped.append(hit)
            continue
        # Hit with no URL and no (repo, path) — pass through unchanged.
        deduped.append(hit)
    return deduped


# --- Concurrent dispatch -----------------------------------------------------


_MCPCallable = Callable[..., list[Tier1Hit]]


def tier1_free_mcps(
    query: str,
    *,
    context7: _MCPCallable,
    ms_learn: _MCPCallable,
    gh_search: _MCPCallable,
    tags: dict | None = None,
) -> Tier1Result:
    """Dispatch the three free MCPs concurrently and merge their results.

    Only MCPs whose corresponding classifier tag is True are invoked. Any
    callable that raises is caught and recorded in ``degraded_sources`` so
    the synthesizer can surface a degraded-mode warning. Hits across MCPs
    are merged then deduplicated.
    """
    if tags is None:
        tags = classify_tags(query)

    plan: list[tuple[str, _MCPCallable]] = []
    if tags.get("mentions_library"):
        plan.append(("context7", context7))
    if tags.get("mentions_microsoft"):
        plan.append(("ms_learn", ms_learn))
    if tags.get("mentions_code_pattern"):
        plan.append(("gh_search", gh_search))

    if not plan:
        return Tier1Result()

    all_hits: list[Tier1Hit] = []
    degraded: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plan)) as pool:
        future_to_name = {
            pool.submit(callable_, query, tags=tags): name for name, callable_ in plan
        }
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                hits = future.result()
            except Exception:
                # Resilience requirement: capture all per-MCP failures so the
                # synthesizer can surface degraded-mode warnings without
                # aborting the other futures.
                degraded.append(name)
                continue
            if hits:
                all_hits.extend(hits)

    return Tier1Result(hits=dedup_hits(all_hits), degraded_sources=degraded)


__all__: Iterable[str] = (
    "Tier1Hit",
    "Tier1Result",
    "classify_tags",
    "dedup_hits",
    "tier1_free_mcps",
)
