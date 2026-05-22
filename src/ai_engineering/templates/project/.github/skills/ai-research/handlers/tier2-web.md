# Handler: Tier 2 -- Web

## Purpose

Invoke a web search (raw web results) and a web fetch (specific URL when known) IN PARALLEL when Tier 1 produced fewer than 5 high-quality hits, or the user query referenced an explicit URL. Honors `--allowed-domains` and `--blocked-domains` flags as pass-through to the search call.

Tier 2 is the bridge between curated MCP corpora (Tier 1) and the open web. It adds breadth and recency that Context7/MS Learn/`gh search` can miss, while still avoiding the cost and latency of NotebookLM persistent corpora (Tier 3).

## Web Provider: Exa Primary, Built-in Fallback

Per spec `notebooklm-async-tier3` (D6, D7, AC3), the Tier 2 web provider is selected by capability detection:

- **PRIMARY -- Exa.** When the Exa MCP tools are available, search uses `mcp__exa__web_search_exa` and single-URL fetch uses `mcp__exa__web_fetch_exa`.
- **FALLBACK -- built-in.** When Exa is unavailable, fall back to the Claude Code built-in `WebSearch` / `WebFetch`. The fallback records `"exa"` in `degraded_sources` so the synthesizer can surface that the preferred provider was skipped.

Fail-soft (D7): an absent Exa provider is skipped silently, recorded in `degraded_sources`, and never raises. The run proceeds on the fallback provider.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier2_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `tier1_hits` (list): Tier 1 results to use as the skip-heuristic input.
- `allowed_domains` (list[str]|None): forwarded as the `allowed_domains` parameter on the search call.
- `blocked_domains` (list[str]|None): forwarded as `blocked_domains` on the search call.
- `exa_search`, `exa_fetch` (callables): tool-shaped handles for `mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa` (the primary provider).
- `web_search`, `web_fetch` (callables): tool-shaped handles for the built-in `WebSearch` / `WebFetch` (the fallback provider).
- `exa_available` (bool): capability-detection result. When True, the Exa callables are used; when False, the built-in callables are used and `"exa"` is recorded in `degraded_sources`.

All four callables are injected as dependencies so tests can substitute mocks.

### Outputs

A `Tier2Result` containing:

- `hits` (list[dict]): merged, deduped results from the chosen search and fetch.
- `skipped` (bool): True when the skip heuristic short-circuited Tier 2.
- `degraded_sources` (list[str]): names of providers/tools that were absent (`"exa"` when Exa is unavailable) or that raised exceptions (the chosen tool's name).

### Step 1 -- Detect explicit URL in query

```python
import re
url_match = re.search(r"https?://\S+", query)
explicit_url = url_match.group(0) if url_match else None
```

### Step 2 -- Apply the skip heuristic

If `len(tier1_hits) >= 5` AND `explicit_url is None`, return `Tier2Result(hits=[], skipped=True, degraded_sources=[])` immediately. This is the dominant path for queries already well-covered by Tier 1. The skip runs before provider selection, so nothing is recorded as degraded.

### Step 3 -- Select the web provider (capability detection)

```python
if exa_available:
    search_fn, fetch_fn = exa_search, exa_fetch
    search_tool, fetch_tool = "mcp__exa__web_search_exa", "mcp__exa__web_fetch_exa"
else:
    search_fn, fetch_fn = web_search, web_fetch
    search_tool, fetch_tool = "web_search", "web_fetch"
    degraded.append("exa")  # D7: absent provider recorded, never raised
```

### Step 4 -- Concurrent dispatch

When Tier 2 runs, schedule both calls on a `ThreadPoolExecutor`:

- The search is ALWAYS invoked when Tier 2 runs. Pass `query` plus `allowed_domains` / `blocked_domains` only when those values are not None.
- The fetch is invoked ONLY when `explicit_url` is set; it receives the URL.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures = {pool.submit(search_fn, query, **filters): search_tool}
    if explicit_url:
        futures[pool.submit(fetch_fn, explicit_url)] = fetch_tool
    for future in concurrent.futures.as_completed(futures):
        ...
```

### Step 5 -- Merge results

Collect hits from both calls, preserving the order they completed. The synthesizer in `synthesize-with-citations.md` is responsible for downstream citation assignment; Tier 2 only returns the merged list.

### Step 6 -- Return

`Tier2Result(hits=merged, skipped=False, degraded_sources=degraded)`, where `degraded` already contains `"exa"` if the fallback was taken, plus the name of any chosen tool that raised.

## Sources Invoked

- `mcp__exa__web_search_exa` (Exa MCP, PRIMARY) -- raw web results, with optional `allowed_domains` / `blocked_domains` pass-through.
- `mcp__exa__web_fetch_exa` (Exa MCP, PRIMARY) -- single-URL fetch when the user query mentions a specific URL.
- `WebSearch` (Claude Code built-in, FALLBACK) -- used when Exa is unavailable.
- `WebFetch` (Claude Code built-in, FALLBACK) -- used when Exa is unavailable.

## Domain Filters

- `--allowed-domains a.com,b.com` is parsed to a Python list and forwarded as `allowed_domains` on the search call (Exa or built-in, whichever is selected).
- `--blocked-domains x.com,y.com` is forwarded as `blocked_domains` on the search call.
- If a filter combination yields zero results, the synthesizer surfaces a warning suggesting the user remove or relax the filter (handler `synthesize-with-citations.md`).

## Resilience

- **Absent provider (capability detection).** When `exa_available` is False, `"exa"` is appended to `degraded_sources`, the built-in provider is used, and the run continues (D7 fail-soft -- never raises).
- **Per-call failure.** On any per-tool failure (search unavailable, fetch redirect loop, etc.) record the chosen tool's name in `degraded_sources` and continue with whatever results the surviving call returned. The failure of one provider's call never falls through to the other provider -- selection is decided once, up front.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier2_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow. The `tier2_web` signature is:

```python
def tier2_web(
    query: str,
    *,
    tier1_hits: list,
    exa_search, exa_fetch,      # mcp__exa__web_search_exa / mcp__exa__web_fetch_exa (primary)
    web_search, web_fetch,      # built-in WebSearch / WebFetch (fallback)
    exa_available: bool,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> Tier2Result: ...
```

## Status

Exa wired as the primary Tier 2 web provider with built-in `WebSearch` / `WebFetch` fallback and capability detection (spec `notebooklm-async-tier3`, Phase 2, D6/D7/AC3). The skip heuristic, explicit-URL detection, domain-filter pass-through, parallel dispatch, and `Tier2Result(hits, skipped, degraded_sources)` shape are unchanged from the spec-111 Phase 2 implementation. The user-facing degraded-mode banner lands with the synthesize handler.
