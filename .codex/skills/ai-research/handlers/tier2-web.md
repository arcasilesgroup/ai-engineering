# Handler: Tier 2 -- Web

## Purpose

Invoke `WebSearch` (raw web results) and `WebFetch` (specific URL when known) IN PARALLEL when Tier 1 produced fewer than 5 high-quality hits, or the user query referenced an explicit URL. Honors `--allowed-domains` and `--blocked-domains` flags as pass-through to the WebSearch tool.

## Procedure

Phase 1 ships this handler as a placeholder; full web invocation logic is filled in by Phase 2 (T-2.5 through T-2.8).

### Inputs

- `query` (string).
- `tier1_hits` (list) from `tier1-free-mcps.md`.
- `flags.allowed_domains` (list|None).
- `flags.blocked_domains` (list|None).

### Outputs

- `hits` (list of `{title, url, snippet, source: 'web'}`), capped at 10 results × 200 tokens for context-window safety.

### Skip Heuristic

If `len(tier1_hits) >= 5` AND no explicit URL in query, skip Tier 2. Phase 2 test `test_tier2_skipped_when_tier1_yields_5_plus_hits` validates the skip path.

### Domain Filters

- `--allowed-domains a.com,b.com` -- pass-through to WebSearch as `allowed_domains` parameter.
- `--blocked-domains x.com,y.com` -- pass-through to WebSearch as `blocked_domains` parameter.
- If filters yield zero results, surface a visible warning suggesting removal of filters.

## Status

Phase 1 placeholder. Logic implemented in Phase 2 (T-2.7).
