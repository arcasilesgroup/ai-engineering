# Handler: Tier 3 -- NotebookLM Persistent

## Purpose

Build a NotebookLM corpus from the URLs collected in Tier 2 and query it with citation instructions. Triggered when `--depth=deep`, when the query is comparative, or when Tier 1+2 collected ≥10 sources. Persistent: the notebook ID is captured and embedded in the artifact for later reuse via `--reuse-notebook`.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_tier3_helper.py`) implements.

### Inputs

- `query` (string): the user's verbatim research question.
- `sources` (list[str]): URLs collected from Tiers 1+2.
- `timestamp_iso` (string): ISO 8601 invocation timestamp -- used in the notebook title hash.
- `reuse_notebook` (string|None) -- if provided, skip `notebook_create`.
- `notebook_create`, `source_add`, `notebook_query` (callables): tool-shaped invocation handles. The helper accepts these as injected dependencies so tests can substitute mocks.

### Outputs

A `Tier3Result` containing:

- `synthesized_response` (string with `[N]` citations).
- `notebook_id` (string).
- `conversation_id` (string).
- `sources_added` (list[str]) -- the (possibly capped) URL list actually sent.

### Trigger Heuristic (T-3.6)

Implemented by `should_invoke_tier3(query, *, depth, tier12_source_count)`:

- `depth.lower() == 'deep'` always triggers Tier 3.
- Comparative queries (regex `\b(vs|versus|compare|difference between|alternatives?)\b`, case-insensitive) trigger Tier 3.
- `tier12_source_count >= 10` triggers Tier 3.
- Otherwise: do not invoke.

### Notebook Naming

`ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>` where:

- `topic-slug` = `re.sub(r'[^a-z0-9]+', '-', query.lower())[:40].strip('-')` (T-3.3).
- `<YYYY-MM-DD>` is the first 10 chars of `timestamp_iso`.
- `hash6` = `hashlib.sha256(f"{query}|{timestamp_iso}".encode()).hexdigest()[:6]` (T-3.4).

Helpers `topic_slug`, `hash6`, and `notebook_title` are exported from the lockstep module.

### Sequence (T-3.5 + T-4.9)

1. **(T-4.9) Auth probe**: if a `server_info` callable is provided, invoke `mcp__notebooklm-mcp__server_info()` first. If the probe raises OR returns `{"authenticated": false}`, short-circuit Tier 3 with `degraded=True` and warning `notebooklm auth expired -- run \`nlm login\` to re-authenticate; Tier 3 skipped, falling back to Tier 2 sources`. The skill MUST NOT call `notebook_create`, `source_add`, or `notebook_query` in this branch. The user receives the warning visibly so they can recover.
2. **Resolve notebook id**:
   * If `reuse_notebook` was provided -> use that string directly.
   * Else call `mcp__notebooklm-mcp__notebook_create(title=notebook_title(...))` and read `notebook_id` from the response.
3. **Add sources, capped at 20**: take the first 20 entries from `sources` and call `mcp__notebooklm-mcp__source_add(notebook_id=..., source_type='url', url=<each>)` per URL, in input order.
4. **Query with citation instruction**: call `mcp__notebooklm-mcp__notebook_query(notebook_id=..., query=f"{query} Answer with citations to the provided sources, using `[N]` notation.")`. Capture `answer` and `conversation_id`.
5. **Return** `Tier3Result(synthesized_response=answer, notebook_id=..., conversation_id=..., sources_added=capped, degraded=False, warnings=[])`.

### Cap on Source Count

`_MAX_SOURCES = 20`. Even when Tier 1+2 collected >20 URLs the helper sends only the first 20 (insertion order), preserving deterministic behaviour for tests.

## Resilience

NotebookLM auth expiry is the most common failure mode. The auth probe in step 1 short-circuits Tier 3 with `degraded=True` and surfaces a warning suggesting `nlm login`. The synthesizer then falls back to the Tier 2 corpus.

When the probe itself raises (network error, MCP server unavailable), Tier 3 is also marked degraded with a corresponding warning so the user knows the answer is missing the deep-corpus tier.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_tier3_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow.

## Status

Phase 3 (T-3.5) implementation. Resilience hardening and degraded-mode UI land in Phase 4 (T-4.9).
