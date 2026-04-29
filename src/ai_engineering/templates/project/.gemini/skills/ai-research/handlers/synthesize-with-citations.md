# Handler: Synthesize With Citations

## Purpose

Produce a synthesized response where every external claim carries `[N]` or `[unsourced]`. The hard-rule is enforced by a regex validator (`\[\d+\]|\[unsourced\]`) that must match at least once per claim paragraph; on failure, retry with a stricter system message (max 2 retries). Failure on retry exhaustion produces output with a visible warning "citations malformed".

## Algorithm

This handler documents the algorithm that the agent (and the lockstep helper at `tests/integration/_ai_research_synthesize_helper.py`) implements.

### Inputs

- `query` (string).
- `sources` (numbered list of `Source(title, url, accessed_at)`) collected across Tiers 0-3. Source numbering is stable across the synthesizer call and the persisted artifact's `## Sources` section so `[N]` citations resolve consistently.
- `synthesizer` (callable): the LLM-as-synthesizer entry point. The helper module accepts this as an injected dependency so tests can substitute deterministic fakes.

### Outputs

A `SynthesizeResult` containing:

- `findings` (string) -- markdown with inline `[N]` citations and `[unsourced]` markers where the model is filling from training data.
- `validation_passed` (bool).
- `warnings` (list[str]) -- e.g., "citations malformed", "Tier 3 degraded", "domain filter yielded zero results". The latter two are appended by the upstream tier handlers.
- `attempts` (int) -- number of synthesizer invocations consumed (1, 2, or 3).

### Validator

Regex `\[\d+\]|\[unsourced\]` (pinned in `CITATION_PATTERN`) must match at least once per paragraph (paragraphs are split by blank-line gaps). Internal-only paragraphs that already contain a marker pass automatically. Empty responses are treated as malformed.

### Retry Loop

1. Synthesize with the default system message:
   `"Synthesize a research summary for the user query. Cite every external claim with `[N]` referring to the numbered Sources list. If a claim comes from prior knowledge with no source, mark it `[unsourced]`."`
2. Run the validator. On pass, return immediately with `validation_passed=True` and no warnings.
3. On fail, retry with the stricter system message (default + `"STRICT: every external claim MUST carry [N] or [unsourced]. No exceptions."`).
4. On the second failure (third synthesizer call total), return the last output with `validation_passed=False` and warning `"citations malformed"`.

The cap at 2 retries (3 total invocations) is intentional: more retries inflate the agent's context budget without measurable improvement in citation density.

## Implementation Reference

The Python lockstep implementation lives at `tests/integration/_ai_research_synthesize_helper.py`. The helper and this handler stay in sync by design -- if either changes, the other must follow. The helper exports `validate_citations(text)` and `synthesize_with_citations(query, sources, synthesizer)` for tests to drive directly.

## Status

Phase 4 (T-4.2) implementation. Resilience warnings (degraded sources from Tier 1 / Tier 3) flow into `SynthesizeResult.warnings` from the upstream handlers.
