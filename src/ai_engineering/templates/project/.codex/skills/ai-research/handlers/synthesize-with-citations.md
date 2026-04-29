# Handler: Synthesize With Citations

## Purpose

Produce a synthesized response where every external claim carries `[N]` or `[unsourced]`. The hard-rule is enforced by a regex validator (`\[\d+\]|\[unsourced\]`) that must match at least once per claim paragraph; on failure, retry with a stricter system message (max 2 retries). Failure on retry exhaustion produces output with a visible warning "citations malformed".

## Procedure

Phase 1 ships this handler as a placeholder; full synthesis and validation logic is implemented in Phase 4 (T-4.1 through T-4.3).

### Inputs

- `query` (string).
- `sources` (numbered list of `{title, url, accessed_at}`) collected across Tiers 0-3.
- `tier_outputs` (object) -- raw hits per tier.

### Outputs

- `findings` (string) -- markdown with inline `[N]` citations and `[unsourced]` markers where the model is filling from training data.
- `validation_passed` (bool).
- `warnings` (list of strings) -- e.g., "citations malformed", "Tier 3 degraded", "domain filter yielded zero results".

### Validator

Regex `\[\d+\]|\[unsourced\]` must match at least once per paragraph that contains an external claim. Internal-only paragraphs (e.g., a meta-summary of the local context) are exempt.

### Retry Loop

1. Synthesize with default system message.
2. Run validator.
3. On fail, append "STRICT: every external claim MUST carry [N] or [unsourced]" to system message and retry.
4. On second fail, return last output with warning "citations malformed".

## Status

Phase 1 placeholder. Logic implemented in Phase 4 (T-4.2).
