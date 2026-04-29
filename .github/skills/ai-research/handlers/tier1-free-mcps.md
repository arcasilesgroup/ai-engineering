# Handler: Tier 1 -- Free MCPs (Parallel)

## Purpose

Invoke the three free, already-connected sources IN PARALLEL: Context7 (library docs), Microsoft Learn (Azure/.NET docs), and `gh search code/repos` (real-world code patterns). Dedup results by URL or `repo+path`.

Tier 1 is the first external-source tier and the workhorse of the skill: most queries are answered here without needing Tier 2 (web) or Tier 3 (NotebookLM). The classifier in `classify-query.md` decides which subset of MCPs apply; this handler dispatches them concurrently and merges the results.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier1_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `tags` (object, optional): pre-computed tag set from `classify-query.md`. When omitted, the classifier is invoked here.
- `context7`, `ms_learn`, `gh_search` (callables): MCP-shaped invocation handles. The helper module accepts these as injected dependencies so tests can substitute mocks.

### Outputs

A `Tier1Result` containing:

- `hits` (list of `Tier1Hit`): deduplicated results across all invoked MCPs.
- `degraded_sources` (list[str]): names of MCPs that raised exceptions during invocation. The synthesizer uses this list to surface a visible degraded-mode warning.

`Tier1Hit` shape: `{title: str, url: str|None, snippet: str, source: str, repo: str|None, path: str|None}`. `url` is set for web/doc sources; `repo` and `path` are set for code-search hits.

### Step 1 -- Classify the query

Build the tag set the way `classify-query.md` describes. The minimal heuristic:

- `mentions_library = bool(re.search(r"\b(react|vue|angular|django|flask|fastapi|rails|express|nestjs|next\.js|nextjs|nuxt|prisma|spring|laravel|tailwind|axios|pandas|numpy|pytorch|tensorflow|library|framework|sdk|cli)\b", query.lower()))`
- `mentions_microsoft = bool(re.search(r"\b(azure|microsoft|\.net|asp\.net|ef core|entity framework|dotnet|powershell|teams)\b", query.lower()))`
- `mentions_code_pattern = bool(re.search(r"\b(github|how do|how does|how to|implementations? of|real[- ]world|projects? (?:do|use|implement)|patterns?|examples?)\b", query.lower()))`
- `is_comparative` and `explicit_url` follow the same regexes as `classify-query.md`.

When the helper is called without tags, it computes them via `classify_tags(query)`.

### Step 2 -- Concurrent dispatch

For each tag that resolves to True, schedule the matching MCP callable on a `concurrent.futures.ThreadPoolExecutor`. The helper records the start timestamp inside each callable; tests assert that the spread between starts is below 100ms, which is the empirical threshold separating concurrent dispatch from serial fallback.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    futures = {}
    if tags["mentions_library"]:
        futures[pool.submit(context7, query, tags=tags)] = "context7"
    if tags["mentions_microsoft"]:
        futures[pool.submit(ms_learn, query, tags=tags)] = "ms_learn"
    if tags["mentions_code_pattern"]:
        futures[pool.submit(gh_search, query, tags=tags)] = "gh_search"
    for future in concurrent.futures.as_completed(futures):
        ...
```

Failures (any exception) append the source to `degraded_sources` and do NOT abort the other futures.

### Step 3 -- Dedup

Two hits collide when:

- Both have a `url` and `urlparse(url)._replace(query="", fragment="").geturl()` is equal, OR
- Both have `repo` and `path` and the `(repo, path)` tuple is equal.

The first occurrence wins (stable order, matching the order MCPs report results). The helper exposes `dedup_hits(hits)` so tests can exercise the dedup logic in isolation.

### Step 4 -- Return

Return `Tier1Result(hits=deduped, degraded_sources=names)`. The synthesizer in `synthesize-with-citations.md` consumes the hits with `[N]` citations.

## Sources Invoked

- `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` when `tags.mentions_library` is true.
- `mcp__claude_ai_Microsoft_Learn__microsoft_docs_search` + `microsoft_code_sample_search` when `tags.mentions_microsoft` is true.
- `gh search code <query> --json repository,path,textMatches` + `gh search repos <topic>` (via Bash) when `tags.mentions_code_pattern` is true.

## Resilience

On any per-source failure (Context7 MCP down, MS Learn timeout, gh CLI rate-limited), the helper catches the exception, appends the source name to `degraded_sources`, and continues with the surviving futures. The synthesizer in `synthesize-with-citations.md` reads `degraded_sources` and surfaces a visible warning to the user, e.g.:

- A single source down -> "Tier 1 degraded: <source> unavailable; results from <surviving sources>".
- All three sources down -> "Tier 1 degraded: all external MCPs unavailable; falling back to local context (Tier 0)".

The helper never re-raises; the skill is responsible for routing degraded-mode warnings into the synthesizer's `warnings` list. This guarantees a query still returns useful output when one source fails transiently.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier1_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow.

## Status

Phase 2 (T-2.3) implementation. Resilience hardening lands in Phase 4 (T-4.9).
