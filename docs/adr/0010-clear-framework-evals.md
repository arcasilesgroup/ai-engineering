# ADR-0010 — CLEAR Framework for Skill Evals

- **Status**: Accepted
- **Date**: 2026-04-27
- **Source**: arXiv 2511.14136 (November 2025)

## Context

Single-run accuracy is statistically meaningless for LLM agents — the
2026 industry baseline is **CLEAR**: Cost, Latency, Efficacy, Assurance,
Reliability. Three uncomfortable findings from the source paper:

1. 37% average gap between lab benchmark scores and production
   deployment performance.
2. Cost varies up to 50× across agents achieving similar accuracy.
3. No major public benchmark reports cost as a first-class metric.

## Decision

The `eval` skill uses the CLEAR five-dimension evaluation:

| Dimension | Metric |
|-----------|--------|
| **Cost** | tokens used, USD per successful task |
| **Latency** | p50 / p95 / p99 wall time |
| **Efficacy** | task completion rate (binary) |
| **Assurance** | policy adherence score (Dual-Plane → audit log) |
| **Reliability** | pass@k stability over re-runs |

Hard gate **only** on critical skills (`commit`, `release-gate`,
`security`, `verify`) — block merge if score drops 2 runs in a row.
Other skills surface dashboard regressions but don't block.

## Consequences

- **Pro**: cost runaway is detectable as a regression, not a surprise on
  the bill.
- **Pro**: cross-provider routing decisions become data-driven (replace
  Claude Opus with DeepSeek where reliability stays ≥ 95% at 20× lower
  cost).
- **Con**: more setup than golden-input/output evals. Mitigated by
  `promptfoo` + `deepeval` already producing CLEAR-compatible metrics.

## Implementation references

- Skill: `skills/catalog/eval/SKILL.md` (Phase 6)
- Adapter: `python/ai_eng_evals/clear_runner.py` (Phase 6)
