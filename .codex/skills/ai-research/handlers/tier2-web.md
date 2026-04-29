# Handler: Tier 2 -- Web

## Purpose

Invoke `WebSearch` (raw web results) and `WebFetch` (specific URL when known) IN PARALLEL when Tier 1 produced fewer than 5 high-quality hits, or the user query referenced an explicit URL. Honors `--allowed-domains` and `--blocked-domains` flags as pass-through to the WebSearch tool.

Tier 2 is the bridge between curated MCP corpora (Tier 1) and the open web. It adds breadth and recency that Context7/MS Learn/`gh search` can miss, while still avoiding the cost and latency of NotebookLM persistent corpora (Tier 3).

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier2_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `tier1_hits` (list): Tier 1 results to use as the skip-heuristic input.
- `allowed_domains` (list[str]|None): forwarded as the `allowed_domains` parameter on the WebSearch call.
- `blocked_domains` (list[str]|None): forwarded as `blocked_domains` on the WebSearch call.
- `web_search`, `web_fetch` (callables): tool-shaped invocation handles. The helper accepts these as injected dependencies so tests can substitute mocks.

### Outputs

A `Tier2Result` containing:

- `hits` (list[dict]): merged, deduped results from WebSearch and WebFetch.
- `skipped` (bool): True when the skip heuristic short-circuited Tier 2.
- `degraded_sources` (list[str]): names of tools that raised exceptions.

### Step 1 -- Detect explicit URL in query

```python
import re
url_match = re.search(r"https?://\S+", query)
explicit_url = url_match.group(0) if url_match else None
```

### Step 2 -- Apply the skip heuristic

If `len(tier1_hits) >= 5` AND `explicit_url is None`, return `Tier2Result(hits=[], skipped=True, degraded_sources=[])` immediately. This is the dominant path for queries already well-covered by Tier 1.

### Step 3 -- Concurrent dispatch

When Tier 2 runs, schedule both tools on a `ThreadPoolExecutor`:

- WebSearch is ALWAYS invoked when Tier 2 runs. Pass `query` plus `allowed_domains` / `blocked_domains` only when those values are not None.
- WebFetch is invoked ONLY when `explicit_url` is set; it receives the URL.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures = {pool.submit(web_search, query, **filters): "web_search"}
    if explicit_url:
        futures[pool.submit(web_fetch, explicit_url)] = "web_fetch"
    for future in concurrent.futures.as_completed(futures):
        ...
```

### Step 4 -- Merge results

Collect hits from both tools, preserving the order they completed. The synthesizer in `synthesize-with-citations.md` is responsible for downstream citation assignment; Tier 2 only returns the merged list.

### Step 5 -- Return

`Tier2Result(hits=merged, skipped=False, degraded_sources=names_of_failed_tools)`.

## Sources Invoked

- `WebSearch` (Claude Code built-in) -- raw web results, with optional `allowed_domains` / `blocked_domains` pass-through.
- `WebFetch` (Claude Code built-in) -- single-URL fetch when the user query mentions a specific URL.

## Domain Filters

- `--allowed-domains a.com,b.com` is parsed to a Python list and forwarded as `allowed_domains` on the WebSearch call.
- `--blocked-domains x.com,y.com` is forwarded as `blocked_domains` on the WebSearch call.
- If a filter combination yields zero results, the synthesizer surfaces a warning suggesting the user remove or relax the filter (handler `synthesize-with-citations.md`).

## Resilience

On any per-tool failure (WebSearch unavailable, WebFetch redirect loop, etc.) record the tool name in `degraded_sources` and continue with whatever results the surviving tool returned. Phase 4 (T-4.9) wires the user-facing degraded-mode banner.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier2_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow.

## Status

Phase 2 (T-2.7) implementation. Resilience hardening and degraded-mode UI land in Phase 4 (T-4.9).
