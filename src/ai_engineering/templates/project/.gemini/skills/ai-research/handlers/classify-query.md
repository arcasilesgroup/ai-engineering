# Handler: Classify Query

## Purpose

Decide which Tier 1 MCPs apply for a given research query. Classification drives parallel invocation in Tier 1.

NotebookLM deep research (Tier 3) is **default-on whenever the tool is available** -- it is NOT gated by classification (no `--depth=deep` and no comparative-query signal). The launch decision lives in the Tier 3 handler (`should_launch_tier3(*, notebooklm_available)`), not here (spec notebooklm-async-tier3 D3). Classification therefore no longer computes a Tier 3 depth heuristic.

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
- `is_comparative` (bool) -- true when the query matches `\b(vs|versus|compare|difference between|alternatives?)\b`. Retained as routing metadata only; it does NOT gate Tier 3 launch (NotebookLM deep research is default-on when available, spec notebooklm-async-tier3 D3).
- `explicit_url` (string|None) -- a URL extracted from the query, if present.

### Heuristic

Phase 2 fills the regex/keyword heuristic. For Phase 1, the placeholder section header documents the contract above.

## Status

Phase 1 placeholder. Logic implemented in Phase 2 (T-2.3). Updated in spec notebooklm-async-tier3 Phase 5 (T-5.2): NotebookLM deep research is default-on when available; the comparative tag no longer gates Tier 3 (D3).
