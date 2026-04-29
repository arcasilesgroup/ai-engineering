# Handler: Classify Query

## Purpose

Decide which tiers and which Tier 1 MCPs apply for a given research query. Classification drives parallel invocation in Tier 1 and the depth heuristic for Tier 3.

## Procedure

Phase 1 ships this handler as a placeholder; full classification logic is filled in by Phase 2 (Tiers 1-2) tasks T-2.1 through T-2.4. The classifier reads the user query and emits a tag set used by downstream handlers.

### Inputs

- `query` (string): the user's verbatim research question.
- `flags` (object): parsed CLI flags (`depth`, `reuse_notebook`, `persist`, `allowed_domains`, `blocked_domains`).

### Outputs

A tag set with at least:

- `mentions_library` (bool) -- true when the query references a known library, framework, SDK, or CLI tool.
- `mentions_microsoft` (bool) -- true when the query mentions Azure, .NET, Microsoft Learn, or Microsoft tooling.
- `mentions_code_pattern` (bool) -- true when the query asks about real-world code (e.g., "how do projects do X", "implementations of Y").
- `is_comparative` (bool) -- true when the query matches `\b(vs|versus|compare|difference between|alternatives?)\b`.
- `explicit_url` (string|None) -- a URL extracted from the query, if present.

### Heuristic

Phase 2 fills the regex/keyword heuristic. For Phase 1, the placeholder section header documents the contract above.

## Status

Phase 1 placeholder. Logic implemented in Phase 2 (T-2.3).
