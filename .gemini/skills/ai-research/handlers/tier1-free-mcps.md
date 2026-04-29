# Handler: Tier 1 -- Free MCPs (Parallel)

## Purpose

Invoke the three free, already-connected sources IN PARALLEL: Context7 (library docs), Microsoft Learn (Azure/.NET docs), and `gh search code/repos` (real-world code patterns). Dedup results by URL or `repo+path`.

## Procedure

Phase 1 ships this handler as a placeholder; the parallel invocation logic and dedup are implemented in Phase 2 (T-2.1 through T-2.4).

### Inputs

- `query` (string).
- `tags` (object) from `classify-query.md`.

### Outputs

- `hits` (list of `{title, url|path, snippet, source}`).
- `degraded_sources` (list) -- MCPs that failed (timeout, auth, network) so the synthesizer can warn the user.

### Sources Invoked

- `mcp__context7__resolve-library-id` + `mcp__context7__query-docs` when `tags.mentions_library` is true.
- `mcp__claude_ai_Microsoft_Learn__microsoft_docs_search` + `microsoft_code_sample_search` when `tags.mentions_microsoft` is true.
- `gh search code <query> --json repository,path,textMatches` + `gh search repos <topic>` (via Bash) when `tags.mentions_code_pattern` is true.

### Parallelism

All applicable MCPs are invoked concurrently. Phase 2 test `test_three_mcps_called_in_parallel` validates that the timestamp delta between starts is <100ms.

### Dedup

- Web/doc URLs -- strip query params and fragment, then compare.
- Code hits -- compare `repo+path`.

### Resilience

On any per-source failure, log a visible warning, append the source to `degraded_sources`, and continue. Phase 4 (T-4.9) implements degraded-mode logic.

## Status

Phase 1 placeholder. Logic implemented in Phase 2 (T-2.3) and resilience in Phase 4 (T-4.9).
