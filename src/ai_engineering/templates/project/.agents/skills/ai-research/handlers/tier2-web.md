# Handler: Tier 2 -- Web

## Purpose

Invoke a web search (raw web results) and a web fetch (specific URL when known) IN PARALLEL when Tier 1 produced fewer than 5 high-quality hits, or the user query referenced an explicit URL. Honors `--allowed-domains` and `--blocked-domains` flags as pass-through to the search call.

Tier 2 is the bridge between curated MCP corpora (Tier 1) and the open web. It adds breadth and recency that Context7/MS Learn/`gh search` can miss, while still avoiding the cost and latency of NotebookLM persistent corpora (Tier 3).

## Web Provider: Concurrent Fan-out (Tavily ‖ Exa ‖ Built-in)

Per spec-174 (D-174-01..04, superseding the spec-172 D-172-02 fall-through), the Tier 2 web layer is a **concurrent fan-out**: when Tier 2 runs, EVERY available provider runs at once, and their results are merged and deduped by URL. There is no first-available selection. The three providers (in priority order, which drives only the dedup tie-break) are:

- **Tavily.** When the Tavily MCP tools are available, search uses `mcp__tavily__tavily_search` and single-URL fetch uses `mcp__tavily__tavily_extract`.
- **Exa.** When the Exa MCP tools are available, search uses `mcp__exa__web_search_exa` and single-URL fetch uses `mcp__exa__web_fetch_exa`.
- **Built-in.** The Claude Code built-in `WebSearch` / `WebFetch` are the zero-config floor; they are always available and always run.

Every **available** provider's search (and, when the query references an explicit URL, its single-URL fetch) is dispatched CONCURRENTLY, so the wall-clock is the slowest provider, not the sum. Running all providers IS the resilience — D-174-04 supersedes D-172-02, so there is NO bounded fall-through. Each ABSENT provider is recorded in `degraded_sources` (`"tavily"`, then `"exa"`; the built-in floor has no marker) so the synthesizer can surface that a provider was skipped. Fail-soft: an absent provider is skipped silently and never raises.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier2_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `tier1_hits` (list): Tier 1 results to use as the skip-heuristic input.
- `allowed_domains` (list[str]|None): forwarded as the `allowed_domains` parameter on the search call.
- `blocked_domains` (list[str]|None): forwarded as `blocked_domains` on the search call.
- `tavily_search`, `tavily_fetch` (callables): tool-shaped handles for `mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`. `tavily_extract` wraps a one-element URL array for single-URL fetch; the callable hides that shape.
- `tavily_available` (bool): capability-detection result for Tavily. When True, Tavily fans out with the others; when False, `"tavily"` is recorded in `degraded_sources` and Tavily is skipped.
- `exa_search`, `exa_fetch` (callables): tool-shaped handles for `mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`.
- `web_search`, `web_fetch` (callables): tool-shaped handles for the built-in `WebSearch` / `WebFetch` (the zero-config floor, always available).
- `exa_available` (bool): capability-detection result for Exa. When True, the Exa callables fan out with the others; when False, `"exa"` is recorded and Exa is skipped.

All six provider callables are injected as dependencies so tests can substitute mocks.

### Outputs

A `Tier2Result` containing:

- `hits` (list[dict]): merged, URL-deduped results fanned out across every available provider's search and fetch (tie-break Tavily > Exa > built-in).
- `skipped` (bool): True when the skip heuristic short-circuited Tier 2.
- `degraded_sources` (list[str]): markers of absent providers (`"tavily"`, then `"exa"`) plus the tool name of any available provider whose search raised or returned zero results.

### Step 1 -- Detect explicit URL in query

```python
import re
url_match = re.search(r"https?://\S+", query)
explicit_url = url_match.group(0) if url_match else None
```

### Step 2 -- Apply the skip heuristic

If `len(tier1_hits) >= 5` AND `explicit_url is None`, return `Tier2Result(hits=[], skipped=True, degraded_sources=[])` immediately. This is the dominant path for queries already well-covered by Tier 1. The skip runs before provider selection, so nothing is recorded as degraded.

### Step 3 -- Build the candidate fan-out (priority order)

Build the candidates in priority order Tavily → Exa → built-in as named `_Candidate` records (not bare tuples), so the fan-out reads fields by name. Priority drives only the dedup tie-break (Step 5), NOT selection — every available provider runs. Each ABSENT candidate appends its marker to `degraded` (a capability degrade, fail-soft). The built-in is always available and has no marker.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class _Candidate:
    available: bool
    search_fn: callable
    fetch_fn: callable
    search_tool: str
    fetch_tool: str
    absent_marker: str | None  # None for the always-available built-in floor

candidates = [
    _Candidate(tavily_available, tavily_search, tavily_fetch,
               "mcp__tavily__tavily_search", "mcp__tavily__tavily_extract", "tavily"),
    _Candidate(exa_available, exa_search, exa_fetch,
               "mcp__exa__web_search_exa", "mcp__exa__web_fetch_exa", "exa"),
    _Candidate(True, web_search, web_fetch, "web_search", "web_fetch", None),  # always available
]
for candidate in candidates:
    if not candidate.available and candidate.absent_marker is not None:
        degraded.append(candidate.absent_marker)  # D-174-01: absent recorded, never raised
available = [c for c in candidates if c.available]  # priority order preserved
```

### Step 4 -- Concurrent fan-out of every available provider (D-174-01)

When Tier 2 runs, fan out EVERY available provider concurrently on an outer `ThreadPoolExecutor` (one task per provider). Inside each provider task, schedule its own search (+ optional fetch) on an inner executor:

- The search is ALWAYS invoked for every available provider. Pass `query` plus `allowed_domains` / `blocked_domains` only when those values are not None.
- The fetch is invoked ONLY when `explicit_url` is set; it receives the URL.

Running all providers IS the resilience — there is NO bounded fall-through (D-174-04 supersedes D-172-02). For each available provider whose search RAISES or returns ZERO hits, record its `search_tool` in `degraded` (plus any raised fetch tool); a degrade never suppresses the other providers. The wall-clock is the slowest provider, not the sum.

Each provider task runs `run_provider`: it schedules the provider's search (always) and its fetch (only when `explicit_url` is set) on an inner executor, then drains them with `as_completed`. A search that RAISES or returns ZERO hits sets `search_failed`; any call that raises appends its tool name to `failed_tools`. There is no fall-through inside the task either — it returns whatever survived.

```python
def run_provider(candidate, query, explicit_url, search_kwargs):
    plan = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        search_future = pool.submit(candidate.search_fn, query, **search_kwargs)
        plan.append((candidate.search_tool, search_future))
        if explicit_url is not None:
            plan.append((candidate.fetch_tool, pool.submit(candidate.fetch_fn, explicit_url)))

        hits, search_failed, failed_tools = [], False, []
        future_to_name = {future: name for name, future in plan}
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                returned = future.result()
            except Exception:
                failed_tools.append(name)        # record the raised tool, keep survivors
                if future is search_future:
                    search_failed = True
                continue
            if future is search_future and not returned:
                search_failed = True             # empty search is a degrade signal
            if returned:
                hits.extend(returned)
    return hits, search_failed, failed_tools

# Build the shared search kwargs once; pass domain filters only when set.
search_kwargs = {}
if allowed_domains is not None:
    search_kwargs["allowed_domains"] = list(allowed_domains)
if blocked_domains is not None:
    search_kwargs["blocked_domains"] = list(blocked_domains)

provider_hits = [[] for _ in available]
with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(available))) as outer:
    future_to_index = {
        outer.submit(run_provider, candidate, query, explicit_url, dict(search_kwargs)): index
        for index, candidate in enumerate(available)
    }  # run_provider fans search ‖ fetch
    for future in concurrent.futures.as_completed(future_to_index):
        index = future_to_index[future]
        candidate = available[index]             # re-derive the candidate for THIS future
        hits, search_failed, failed_tools = future.result()
        provider_hits[index] = hits              # keyed by priority index
        for tool in failed_tools:
            if tool not in degraded:
                degraded.append(tool)
        if search_failed and candidate.search_tool not in degraded:
            degraded.append(candidate.search_tool)  # raise OR empty, recorded, no fall-through
```

### Step 5 -- Merge + dedup by URL (D-174-03)

Merge the per-provider hits in PRIORITY order (Tavily → Exa → built-in). Dedup by the **exact `url` string** (no URL normalization — compared verbatim). Add each hit whose `url` was not already seen; the first row seen for a URL wins, so on a duplicate URL the higher-priority provider's row is kept (**Tavily > Exa > built-in**). Hits without a `url` key carry no dedup key and are always kept. The synthesizer in `synthesize-with-citations.md` handles downstream citation assignment; Tier 2 only returns the merged, deduped list.

```python
merged, seen = [], set()
for hits_i in provider_hits:           # priority order
    for hit in hits_i:
        url = hit.get("url")
        if url is None:
            merged.append(hit)         # url-less hits always kept
        elif url not in seen:
            seen.add(url)
            merged.append(hit)         # first (highest-priority) row wins
```

### Step 6 -- Return

`Tier2Result(hits=merged, skipped=False, degraded_sources=degraded)`, where `merged` is the URL-deduped fan-out across all available providers and `degraded` contains the markers of any absent provider (`"tavily"`, `"exa"`) plus the tool name of any available provider whose search raised or returned zero results.

## Sources Invoked

Every available provider's search (+ optional fetch) runs concurrently; priority drives only the dedup tie-break.

- `mcp__tavily__tavily_search` (Tavily MCP) -- raw web results, with optional `allowed_domains` / `blocked_domains` pass-through.
- `mcp__tavily__tavily_extract` (Tavily MCP) -- single-URL fetch when the user query mentions a specific URL (wraps a one-element URL array).
- `mcp__exa__web_search_exa` (Exa MCP) -- raw web results, fans out alongside Tavily and the built-in.
- `mcp__exa__web_fetch_exa` (Exa MCP) -- single-URL fetch alongside the others.
- `WebSearch` (Claude Code built-in) -- the zero-config floor; always runs.
- `WebFetch` (Claude Code built-in) -- single-URL fetch on the built-in floor.

## Domain Filters

- `--allowed-domains a.com,b.com` is parsed to a Python list and forwarded as `allowed_domains` on the search call of EVERY available provider (Tavily, Exa, and built-in).
- `--blocked-domains x.com,y.com` is forwarded as `blocked_domains` on every available provider's search call.
- If a filter combination yields zero results, the synthesizer surfaces a warning suggesting the user remove or relax the filter (handler `synthesize-with-citations.md`).

## Resilience

- **Absent provider (capability detection).** Each absent provider appends its marker (`"tavily"`, then `"exa"`) to `degraded_sources` and is skipped; the available providers fan out and the run continues (fail-soft -- never raises).
- **Fan-out is the resilience (D-174-04, supersedes the D-172-02 bounded fall-through).** Every available provider runs concurrently, so there is NO fall-through. An available provider whose search RAISES or returns ZERO results records its `search_tool` in `degraded_sources` but never suppresses the others; its surviving explicit-URL fetch hit (if any) is still merged in. Even when every provider is empty, each runs exactly once — no second pass.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier2_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow. The `tier2_web` signature is:

```python
def tier2_web(
    query: str,
    *,
    tier1_hits: list,
    tavily_search, tavily_fetch,  # mcp__tavily__tavily_search / mcp__tavily__tavily_extract
    tavily_available: bool,
    exa_search, exa_fetch,        # mcp__exa__web_search_exa / mcp__exa__web_fetch_exa
    web_search, web_fetch,        # built-in WebSearch / WebFetch (always-available floor)
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
4. **Fail-soft** -- an absent or unregistered Tavily MCP is fail-soft: the fan-out records `"tavily"` in `degraded_sources` and skips Tavily; Exa and the built-in still run. No installer-template `.mcp.json` is shipped (a key cannot be committed; D-172-04 scopes registration to the operator).

## Status

Tier 2 web runs a concurrent fan-out of every available provider — Tavily (`mcp__tavily__tavily_search` / `mcp__tavily__tavily_extract`), Exa (`mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa`), and the built-in `WebSearch` / `WebFetch` — merged and deduped by URL with the tie-break Tavily > Exa > built-in (spec-174, D-174-01..05; D-174-04 supersedes the spec-172 D-172-02 bounded fall-through). The skip heuristic, explicit-URL detection, domain-filter pass-through, parallel dispatch, and `Tier2Result(hits, skipped, degraded_sources)` shape are unchanged from the prior implementation. The user-facing degraded-mode banner lands with the synthesize handler.
