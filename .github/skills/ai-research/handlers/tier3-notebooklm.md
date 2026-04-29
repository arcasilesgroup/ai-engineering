# Handler: Tier 3 -- NotebookLM Persistent

## Purpose

Build a NotebookLM corpus from the URLs collected in Tier 2 and query it with citation instructions. Triggered when `--depth=deep`, when the query is comparative, or when Tier 1+2 collected ≥10 sources. Persistent: the notebook ID is captured and embedded in the artifact for later reuse via `--reuse-notebook`.

## Procedure

Phase 1 ships this handler as a placeholder; full NotebookLM invocation logic is filled in by Phase 3 (T-3.1 through T-3.7).

### Inputs

- `query` (string).
- `sources` (list of URLs) from Tiers 1+2.
- `flags.reuse_notebook` (string|None) -- if provided, skip `notebook_create`.
- `flags.depth` (string).

### Outputs

- `synthesized_response` (string with `[N]` citations).
- `notebook_id` (string).
- `conversation_id` (string).
- `degraded` (bool) -- true if NotebookLM auth expired and Tier 3 was skipped.

### Trigger Heuristic

- `flags.depth == 'deep'` always triggers Tier 3.
- Comparative queries (regex `\b(vs|versus|compare|difference between|alternatives?)\b`) trigger Tier 3.
- ≥10 sources collected from Tier 1+2 trigger Tier 3.

### Notebook Naming

`ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>` where:

- `topic-slug` = `re.sub(r'[^a-z0-9]+', '-', query.lower())[:40].strip('-')`
- `hash6` = `hashlib.sha256(f"{query}|{timestamp_iso}".encode()).hexdigest()[:6]`

### Sequence

1. `mcp__notebooklm-mcp__server_info` -- probe auth. If expired, set `degraded=True`, surface warning suggesting `nlm login`, and skip Tier 3.
2. If `reuse_notebook` provided, use that ID; else `mcp__notebooklm-mcp__notebook_create` with the naming pattern above.
3. `mcp__notebooklm-mcp__source_add` per URL from `sources`, capped at 20 sources.
4. `mcp__notebooklm-mcp__notebook_query` with the user query plus instruction "answer with citations to the provided sources, using `[N]` notation".
5. Capture `notebook_id` and `conversation_id`; return synthesized response.

### Resilience

NotebookLM auth expiry is the most common failure mode. The `server_info` probe at step 1 makes this an explicit gate. Phase 4 test `test_notebooklm_auth_expired_degrades_to_tier2_only_with_warning` validates the degraded path.

## Status

Phase 1 placeholder. Logic implemented in Phase 3 (T-3.5) and resilience in Phase 4 (T-4.9).
