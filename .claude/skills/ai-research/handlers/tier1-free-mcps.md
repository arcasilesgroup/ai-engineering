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
- `context7_available`, `ms_learn_available`, `gh_search_available` (bool, default True): per-source capability-detection results. Each routes through the shared `is_available` guard so a False flag means the source is treated as absent (not wired / unauthenticated) and its callable is NEVER invoked (spec `notebooklm-async-tier3` D7).

### Outputs

A `Tier1Result` containing:

- `hits` (list of `Tier1Hit`): deduplicated results across all invoked MCPs.
- `degraded_sources` (list[str]): names of MCPs that were skipped because they were absent (capability detection said unavailable) OR that raised exceptions during invocation. The synthesizer uses this list to surface a visible degraded-mode warning. Both fail-soft paths feed the same list (see "Resilience").

`Tier1Hit` shape: `{title: str, url: str|None, snippet: str, source: str, repo: str|None, path: str|None}`. `url` is set for web/doc sources; `repo` and `path` are set for code-search hits.

### Step 1 -- Classify the query

Build the tag set the way `classify-query.md` describes. The minimal heuristic:

- `mentions_library = bool(re.search(r"\b(react|vue|angular|django|flask|fastapi|rails|express|nestjs|next\.js|nextjs|nuxt|prisma|spring|laravel|tailwind|axios|pandas|numpy|pytorch|tensorflow|library|framework|sdk|cli)\b", query.lower()))`
- `mentions_microsoft = bool(re.search(r"\b(azure|microsoft|\.net|asp\.net|ef core|entity framework|dotnet|powershell|teams)\b", query.lower()))`
- `mentions_code_pattern = bool(re.search(r"\b(github|how do|how does|how to|implementations? of|real[- ]world|projects? (?:do|use|implement)|patterns?|examples?)\b", query.lower()))`
- `is_comparative` and `explicit_url` follow the same regexes as `classify-query.md`.

When the helper is called without tags, it computes them via `classify_tags(query)`.

### Step 2 -- Capability detection (per-source absence guard, D7)

Before scheduling anything, build the dispatch `plan` by intersecting two predicates per source:

1. **Applicable** -- the matching classifier tag is True (`mentions_library` → Context7, `mentions_microsoft` → MS Learn, `mentions_code_pattern` → `gh search`).
2. **Available** -- the source's `*_available` flag, routed through the shared `is_available` guard in `tests/integration/_ai_research_capability.py`. The same guard every tier uses, so "absent" means the same thing across Tier 1 / Tier 2 / Tier 3 (spec `notebooklm-async-tier3` D7, §10.4 DRY).

A source that is applicable but **absent** (its `*_available` flag is False, e.g. Context7 / MS Learn / `gh` not wired or unauthenticated) is **skipped silently**, its name is appended to `degraded_sources` up front, and its callable is **never invoked**. This is distinct from the transient-exception path below: absence is detected *before* dispatch, an exception is caught *during* dispatch -- both feed `degraded_sources`.

```python
availability = {
    "context7": context7_available,
    "ms_learn": ms_learn_available,
    "gh_search": gh_search_available,
}
candidates = [
    ("context7", context7, tags["mentions_library"]),
    ("ms_learn", ms_learn, tags["mentions_microsoft"]),
    ("gh_search", gh_search, tags["mentions_code_pattern"]),
]
plan, degraded = [], []
for name, callable_, applicable in candidates:
    if not applicable:
        continue
    if not is_available(lambda flag=availability[name]: flag):
        degraded.append(name)   # absent: skipped silently, recorded, never invoked
        continue
    plan.append((name, callable_))
```

### Step 3 -- Concurrent dispatch

Schedule each planned MCP callable on a `concurrent.futures.ThreadPoolExecutor`. The helper records the start timestamp inside each callable; tests assert that the spread between starts is below 100ms, which is the empirical threshold separating concurrent dispatch from serial fallback.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=len(plan)) as pool:
    futures = {pool.submit(callable_, query, tags=tags): name for name, callable_ in plan}
    for future in concurrent.futures.as_completed(futures):
        ...
```

When `plan` is empty (no applicable+available source), return `Tier1Result(degraded_sources=degraded)` immediately without opening a pool. Transient failures (any exception raised by an invoked callable) append the source to `degraded_sources` and do NOT abort the other futures.

### Step 4 -- Dedup

Two hits collide when:

- Both have a `url` and `urlparse(url)._replace(query="", fragment="").geturl()` is equal, OR
- Both have `repo` and `path` and the `(repo, path)` tuple is equal.

The first occurrence wins (stable order, matching the order MCPs report results). The helper exposes `dedup_hits(hits)` so tests can exercise the dedup logic in isolation.

### Step 5 -- Return

Return `Tier1Result(hits=deduped, degraded_sources=degraded)`. The `degraded` list already carries the names of absent sources (skipped up front in Step 2) plus any invoked source that raised in Step 3. The synthesizer in `synthesize-with-citations.md` consumes the hits with `[N]` citations and the `degraded_sources` for its degraded-mode banner.

## Sources Invoked

- `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` when `tags.mentions_library` is true.
- `mcp__claude_ai_Microsoft_Learn__microsoft_docs_search` + `microsoft_code_sample_search` when `tags.mentions_microsoft` is true.
- `gh search code <query> --json repository,path,textMatches` + `gh search repos <topic>` (via Bash) when `tags.mentions_code_pattern` is true.

## Resilience

Tier 1 fail-soft (spec `notebooklm-async-tier3` D7, G5) runs on **two distinct paths**, both feeding `degraded_sources` and neither ever raising:

1. **Absence (capability detection).** A source whose `*_available` flag is False -- routed through the shared `is_available` guard -- is detected as absent BEFORE dispatch (Step 2). It is skipped silently, recorded in `degraded_sources`, and its callable is never invoked. This covers a source that is not wired at all or is present-but-unauthenticated (e.g. `gh` without a token). It is the same up-front absence semantics every tier uses, so "absent" is uniform across Tier 1 / Tier 2 / Tier 3.
2. **Transient failure (exception during invocation).** An available source whose callable raises mid-call (Context7 MCP down, MS Learn timeout, gh CLI rate-limited) is caught post-hoc in Step 3, appended to `degraded_sources`, and the surviving futures continue.

The synthesizer in `synthesize-with-citations.md` reads `degraded_sources` (it does not distinguish the two paths -- a degraded source is degraded) and surfaces a visible warning to the user, e.g.:

- A single source down/absent -> "Tier 1 degraded: <source> unavailable; results from <surviving sources>".
- All three sources down/absent -> "Tier 1 degraded: all external MCPs unavailable; falling back to local context (Tier 0)".

The helper never re-raises; the skill is responsible for routing degraded-mode warnings into the synthesizer's `warnings` list. This guarantees a query still returns useful output when a source is absent or fails transiently.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier1_helper.py` (with the shared absence guard in `tests/integration/_ai_research_capability.py`). The public `tier1_free_mcps` signature carries the three `*_available` flags. The helper and this handler stay in sync by design (AC7) -- if either changes, the other must follow.

## Status

Capability detection + fail-soft for the three free MCPs in lockstep with `_ai_research_tier1_helper.py` (spec `notebooklm-async-tier3`, Phase 3, D7/G5/AC4): per-source `*_available` absence guard distinct from the transient-exception path, both feeding `degraded_sources`. The classifier-driven applicability, parallel dispatch, dedup, and `Tier1Result(hits, degraded_sources)` shape are unchanged from the spec-111 Phase 2 implementation.
