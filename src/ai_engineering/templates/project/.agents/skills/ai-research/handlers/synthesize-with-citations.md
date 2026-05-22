# Handler: Synthesize With Citations

## Purpose

Produce a synthesized response where every external claim carries `[N]` or `[unsourced]`, ending with EXACTLY 3 recommended strategic directions. The hard-rule is enforced by a regex validator (`\[\d+\]|\[unsourced\]`) that must match at least once per claim paragraph and per recommended direction; on failure, retry with a stricter system message (max 2 retries). Failure on retry exhaustion produces output with a visible warning ("citations malformed" and/or "recommended directions invalid: ...") and does not raise.

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_synthesize_helper.py`) implements.

### Inputs

- `query` (string).
- `sources` (numbered list of `Source(title, url, accessed_at)`) collected across Tiers 0-2, then fused with NotebookLM-discovered URLs (see "Source Merge"). Source numbering is stable across the synthesizer call and the persisted artifact's `## Sources` section so `[N]` citations resolve consistently.
- `notebooklm_sources` (`list[str]`) -- the URLs the Tier 3 NotebookLM deep-research job discovered autonomously (`Tier3Result.sources_discovered`). Accepted as a plain string list to keep synthesis decoupled from the Tier 3 helper (no cross-import).
- `synthesizer` (callable): the LLM-as-synthesizer entry point. The helper module accepts this as an injected dependency so tests can substitute deterministic fakes. It returns either the findings string (citation-only contract) or a `(findings, directions)` tuple (full contract with recommended directions).

### Outputs

A `SynthesizeResult` containing:

- `findings` (string) -- markdown with inline `[N]` citations and `[unsourced]` markers where the model is filling from training data.
- `validation_passed` (bool).
- `warnings` (list[str]) -- e.g., "citations malformed", "recommended directions invalid: ...", "Tier 3 degraded", "domain filter yielded zero results". The Tier-degradation entries are appended by the upstream tier handlers.
- `attempts` (int) -- number of synthesizer invocations consumed (1, 2, or 3).
- `recommended_directions` (`list[Direction]`) -- EXACTLY 3 strategic directions (see "Recommended Directions"). Each `Direction` carries `title`, `rationale`, `trade_off`, and `citations` (the `[N]` / `[unsourced]` markers).

### Source Merge

NotebookLM (Tier 3) runs autonomous deep research and discovers its own sources, while Tiers 0-2 run independently (spec `notebooklm-async-tier3` D2 -- merge at synthesis). Before synthesizing, fuse the two source sets with `merge_sources(tier_sources, notebooklm_sources)`:

- De-duplicate by URL. **Tier sources come first** (stable order); a NotebookLM URL already present in the tier sources is dropped so the richer tier `Source` (with its real title) wins.
- NotebookLM URLs with no title become `Source` entries with a derived placeholder title (`NotebookLM source: <host/path>`) and an empty `accessed_at` (the discovery timestamp is owned by Tier 3).

The merged, de-duplicated list is what gets numbered for `[N]` citations.

### Recommended Directions

The output ALWAYS ends with a `## Recommended Directions` block carrying EXACTLY 3 strategic directions ("rumbo") -- spec `notebooklm-async-tier3` D8/G7, AC5. Each direction is a `Direction(title, rationale, trade_off, citations)`:

- `title` -- a short imperative label.
- `rationale` -- a 1-2 line justification.
- `trade_off` -- the cost / risk the option carries.
- `citations` -- the `[N]` / `[unsourced]` markers backing the direction.

The directions are synthesizer-derived from the merged evidence (OQ3). Rendered shape:

```markdown
## Recommended Directions

1. **<title>** — <rationale> [N]. Trade-off: <trade_off>.
2. **<title>** — <rationale> [N]. Trade-off: <trade_off>.
3. **<title>** — <rationale> [unsourced]. Trade-off: <trade_off>.
```

### Validator

Two checks run on every synthesizer output:

1. **Per-paragraph citations.** Regex `\[\d+\]|\[unsourced\]` (pinned in `CITATION_PATTERN`) must match at least once per paragraph (paragraphs are split by blank-line gaps). Internal-only paragraphs that already contain a marker pass automatically. Empty responses are treated as malformed.
2. **Recommended directions** (`validate_directions`). There MUST be EXACTLY 3 directions, and each direction MUST carry at least one `[N]` / `[unsourced]` marker -- in its `citations` list OR inline in its rationale/trade-off prose. The same pinned `CITATION_PATTERN` is reused, so the directions rule never drifts from the per-paragraph rule. The directions gate applies only when the synthesizer returns the `(findings, directions)` tuple form.

### Retry Loop

1. Synthesize with the default system message:
   `"Synthesize a research summary for the user query. Cite every external claim with `[N]` referring to the numbered Sources list. If a claim comes from prior knowledge with no source, mark it `[unsourced]`. End with exactly 3 recommended directions, each with a title, a 1-2 line rationale, a trade-off, and at least one `[N]` or `[unsourced]` citation."`
2. Run BOTH validators. On a clean pass (citations AND directions), return immediately with `validation_passed=True` and no warnings.
3. On any failure, retry with the stricter system message (default + `"STRICT: every external claim MUST carry [N] or [unsourced], and there MUST be EXACTLY 3 recommended directions, each individually cited. No exceptions."`).
4. On the second failure (third synthesizer call total), return the last output with `validation_passed=False` and the relevant warning(s): `"citations malformed"` and/or `"recommended directions invalid: <problems>"`. The pipeline records the warning and does NOT raise.

The cap at 2 retries (3 total invocations) is intentional: more retries inflate the agent's context budget without measurable improvement in citation density.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_synthesize_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow. The helper exports `validate_citations(text)`, `validate_directions(directions)`, `merge_sources(tier_sources, notebooklm_sources)`, and `synthesize_with_citations(query, sources, synthesizer)` for tests to drive directly.

## Status

Phase 4 (T-4.3, sub-003) implementation: source merge (D2) + the exactly-3 `## Recommended Directions` output block (D8/G7, AC5). The `CITATION_PATTERN` regex stays pinned and `validate_citations` / the per-paragraph enforcement are unchanged. Resilience warnings (degraded sources from Tier 1 / Tier 3) flow into `SynthesizeResult.warnings` from the upstream handlers.
