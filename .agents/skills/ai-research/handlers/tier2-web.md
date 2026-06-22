# Handler: Tier 2 -- Web

## Purpose

Invoke a web search (raw web results) and a web fetch (specific URL when known) IN PARALLEL when Tier 1 produced fewer than 5 high-quality hits, or the user query referenced an explicit URL. Honors `--allowed-domains` and `--blocked-domains` flags as pass-through to the search call.

Tier 2 is the bridge between curated MCP corpora (Tier 1) and the open web. It adds breadth and recency that Context7/MS Learn/`gh search` can miss, while still avoiding the cost and latency of NotebookLM persistent corpora (Tier 3).

## Web Provider: Tavily Primary, Exa Secondary, Built-in Fallback

Per spec-172 (D-172-01, D-172-02), the Tier 2 web provider is a capability-detected cascade. The first available of three providers is selected, in priority order:

- **PRIMARY -- Tavily.** When the Tavily MCP tools are available, search uses `mcp__tavily__tavily_search` and single-URL fetch uses `mcp__tavily__tavily_extract`.
- **SECONDARY -- Exa.** When Tavily is unavailable, search uses `mcp__exa__web_search_exa` and single-URL fetch uses `mcp__exa__web_fetch_exa`.
- **FALLBACK -- built-in.** When neither Tavily nor Exa is available, fall back to the Claude Code built-in `WebSearch` / `WebFetch` (the zero-config last resort, always available).

Each absent higher-priority provider is recorded in `degraded_sources` (`"tavily"`, then `"exa"`) so the synthesizer can surface that a preferred provider was skipped. Fail-soft (D-172-01): an absent provider is skipped silently, recorded, and never raises. The run proceeds on the next available provider.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier2_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `tier1_hits` (list): Tier 1 results to use as the skip-heuristic input.
- `allowed_domains` (list[str]|None): forwarded as the `allowed_domains` parameter on the search call.
- `blocked_domains` (list[str]|None): forwarded as `blocked_domains` on the search call.
- `tavily_search`, `tavily_fetch` (callables): tool-shaped handles for `mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract` (the primary provider). `tavily_extract` wraps a one-element URL array for single-URL fetch; the callable hides that shape.
- `tavily_available` (bool): capability-detection result for Tavily. When True, Tavily is the primary provider; when False, `"tavily"` is recorded in `degraded_sources` and selection falls to Exa.
- `exa_search`, `exa_fetch` (callables): tool-shaped handles for `mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa` (the secondary provider).
- `web_search`, `web_fetch` (callables): tool-shaped handles for the built-in `WebSearch` / `WebFetch` (the last-resort provider, always available).
- `exa_available` (bool): capability-detection result for Exa. When True (and Tavily absent), the Exa callables are used; when False, `"exa"` is recorded and selection falls to the built-in.

All six provider callables are injected as dependencies so tests can substitute mocks.

### Outputs

A `Tier2Result` containing:

- `hits` (list[dict]): merged, deduped results from the chosen search and fetch.
- `skipped` (bool): True when the skip heuristic short-circuited Tier 2.
- `degraded_sources` (list[str]): markers of absent higher-priority providers (`"tavily"`, then `"exa"`) plus the tool name of any selected provider whose search raised or returned zero results (triggering the bounded fall-through).

### Step 1 -- Detect explicit URL in query

```python
import re
url_match = re.search(r"https?://\S+", query)
explicit_url = url_match.group(0) if url_match else None
```

### Step 2 -- Apply the skip heuristic

If `len(tier1_hits) >= 5` AND `explicit_url is None`, return `Tier2Result(hits=[], skipped=True, degraded_sources=[])` immediately. This is the dominant path for queries already well-covered by Tier 1. The skip runs before provider selection, so nothing is recorded as degraded.

### Step 3 -- Select the web provider (ordered capability cascade)

Build the candidates in priority order Tavily → Exa → built-in. The first available candidate is the PRIMARY; the next available one is the bounded fall-through target (Step 4). Each skipped higher-priority candidate appends its marker to `degraded` (a capability degrade, not the fall-through). The built-in is always available and has no marker.

```python
candidates = [
    (tavily_available, tavily_search, tavily_fetch,
     "mcp__tavily__tavily_search", "mcp__tavily__tavily_extract", "tavily"),
    (exa_available, exa_search, exa_fetch,
     "mcp__exa__web_search_exa", "mcp__exa__web_fetch_exa", "exa"),
    (True, web_search, web_fetch, "web_search", "web_fetch", None),  # always available
]
for available, *_rest, marker in candidates:
    if available:
        break
    if marker is not None:
        degraded.append(marker)  # D-172-01: absent provider recorded, never raised
available = [c for c in candidates if c[0]]
primary, fallback = available[0], (available[1] if len(available) > 1 else None)
```

### Step 4 -- Concurrent dispatch (primary) + one bounded fall-through

When Tier 2 runs, schedule the PRIMARY provider's calls on a `ThreadPoolExecutor`:

- The search is ALWAYS invoked when Tier 2 runs. Pass `query` plus `allowed_domains` / `blocked_domains` only when those values are not None.
- The fetch is invoked ONLY when `explicit_url` is set; it receives the URL.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures = {pool.submit(primary.search_fn, query, **filters): primary.search_tool}
    if explicit_url:
        futures[pool.submit(primary.fetch_fn, explicit_url)] = primary.fetch_tool
    for future in concurrent.futures.as_completed(futures):
        ...  # record raised tools in degraded; merge surviving hits
search_failed = (primary search raised) or (primary search returned 0 hits)
if search_failed and fallback is not None:
    degraded.append(primary.search_tool)        # record once
    fb_hits = fallback.search_fn(query, **filters)  # run EXACTLY once
    hits.extend(fb_hits)                         # preserve surviving primary fetch hits
    if not fb_hits:
        degraded.append(fallback.search_tool)   # empty fall-through recorded, no further fall-through
```

### Step 5 -- Merge results

Collect hits from the primary calls and (if the bounded fall-through ran) the fall-through search, preserving completion order. Surviving explicit-URL fetch hits from the primary are kept across the fall-through. The synthesizer in `synthesize-with-citations.md` handles downstream citation assignment; Tier 2 only returns the merged list.

### Step 6 -- Return

`Tier2Result(hits=merged, skipped=False, degraded_sources=degraded)`, where `degraded` already contains the markers of any absent higher-priority provider (`"tavily"`, `"exa"`) plus the tool name of any selected provider whose search raised or returned zero results.

## Sources Invoked

- `mcp__tavily__tavily_search` (Tavily MCP, PRIMARY) -- raw web results, with optional `allowed_domains` / `blocked_domains` pass-through.
- `mcp__tavily__tavily_extract` (Tavily MCP, PRIMARY) -- single-URL fetch when the user query mentions a specific URL (wraps a one-element URL array).
- `mcp__exa__web_search_exa` (Exa MCP, SECONDARY) -- used when Tavily is unavailable.
- `mcp__exa__web_fetch_exa` (Exa MCP, SECONDARY) -- single-URL fetch when Tavily is unavailable.
- `WebSearch` (Claude Code built-in, FALLBACK) -- used when neither Tavily nor Exa is available.
- `WebFetch` (Claude Code built-in, FALLBACK) -- used when neither Tavily nor Exa is available.

## Domain Filters

- `--allowed-domains a.com,b.com` is parsed to a Python list and forwarded as `allowed_domains` on the search call (whichever provider is selected -- Tavily, Exa, or built-in).
- `--blocked-domains x.com,y.com` is forwarded as `blocked_domains` on the search call.
- If a filter combination yields zero results, the synthesizer surfaces a warning suggesting the user remove or relax the filter (handler `synthesize-with-citations.md`).

## Resilience

- **Absent provider (capability detection).** Each absent higher-priority provider appends its marker (`"tavily"`, then `"exa"`) to `degraded_sources`; the next available provider is selected and the run continues (D-172-01 fail-soft -- never raises).
- **One bounded fall-through (D-172-02, supersedes the former no-fall-through rule).** If the selected provider's search RAISES or returns ZERO results, record it in `degraded_sources` and fall through to the NEXT available provider EXACTLY ONCE. A second empty/raising result does NOT trigger a further fall-through. Surviving explicit-URL fetch hits from the primary are preserved across the fall-through.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier2_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow. The `tier2_web` signature is:

```python
def tier2_web(
    query: str,
    *,
    tier1_hits: list,
    tavily_search, tavily_fetch,  # mcp__tavily__tavily_search / mcp__tavily__tavily_extract (primary)
    tavily_available: bool,
    exa_search, exa_fetch,        # mcp__exa__web_search_exa / mcp__exa__web_fetch_exa (secondary)
    web_search, web_fetch,        # built-in WebSearch / WebFetch (fallback)
    exa_available: bool,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> Tier2Result: ...
```

## Operator Setup -- Tavily MCP

Tavily is wired but not connected automatically; the operator registers the MCP server once per repo (no API key is ever committed -- §13 secrets):

1. **Register the server** (canonical name `tavily`, HTTP transport). The repo ships an `.mcp.json` at its root with the server entry; the key is read from the `TAVILY_API_KEY` environment variable. The CLI equivalent is:

   ```bash
   claude mcp add --transport http tavily https://mcp.tavily.com/mcp/ \
     --header "Authorization: Bearer $TAVILY_API_KEY"
   ```

2. **Export the key in the operator shell** -- `export TAVILY_API_KEY=...`. It is resolved from the environment at connect time and never written to a committed file.
3. **Verify** -- `claude mcp list` shows `tavily` connected, and the tools resolve as `mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`.
4. **Fail-soft** -- an absent or unregistered Tavily MCP is fail-soft: the cascade records `"tavily"` in `degraded_sources` and falls through to Exa, then the built-in. No installer-template `.mcp.json` is shipped (a key cannot be committed; D-172-04 scopes registration to the operator).

## Status

Tavily wired as the PRIMARY Tier 2 web provider (`mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`), with Exa SECONDARY and the built-in `WebSearch` / `WebFetch` LAST, selected by an ordered capability cascade with one bounded fall-through on raise-or-empty (spec-172, D-172-01..04). The skip heuristic, explicit-URL detection, domain-filter pass-through, parallel dispatch, and `Tier2Result(hits, skipped, degraded_sources)` shape are unchanged from the prior implementation. The user-facing degraded-mode banner lands with the synthesize handler.
