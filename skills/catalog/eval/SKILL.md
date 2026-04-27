---
name: eval
description: Use when evaluating LLM skills/agents on Cost, Latency, Efficacy, Assurance, Reliability — the CLEAR framework. Trigger for "evaluate this skill", "run evals", "is this skill regressing", "compare providers". Hard gate on critical skills if score drops 2 runs in a row.
effort: max
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-eval

CLEAR-framework evaluation (ADR-0010): Cost, Latency, Efficacy,
Assurance, Reliability. Single-run accuracy is statistically meaningless;
pass@k stability and cost-normalized accuracy are first-class.

> Source: arXiv 2511.14136 — 37% gap between lab benchmark and prod;
> 50× cost variance across agents at similar accuracy.

## When to use

- Skill / agent regression testing on PR
- Provider routing decisions (Claude vs GPT vs DeepSeek)
- Cost runaway investigation
- Pre-release evaluation of critical skills
- New skill onboarding — establish baseline

## CLEAR dimensions

| Dimension | Metric | Source |
|-----------|--------|--------|
| **Cost** | tokens used, USD per successful task | provider billing API |
| **Latency** | p50 / p95 / p99 wall time | OTel spans |
| **Efficacy** | task completion rate (binary) | golden-set assertions |
| **Assurance** | policy adherence score | Dual-Plane audit log |
| **Reliability** | pass@k stability over k re-runs | repeated execution |

## Process

1. **Load golden datasets** from `.ai-engineering/evals/<skill>/`
   — input, expected output, judging criteria.
2. **Dispatch runners** — `promptfoo` (TypeScript) for prompt-level
   matrices; `deepeval` (Python) for assertion-rich graders.
3. **Re-run k times** (default k=5) to compute pass@k and variance.
4. **Compute cost-normalized accuracy** — efficacy ÷ USD per task.
5. **Compare to baseline** — flag regressions ≥ 5% on any dimension.
6. **Aggregate verdict** — pass / regress / fail; persist to
   `.ai-engineering/evals/<skill>/runs/<ts>.json`.
7. **Emit telemetry** — `eval.completed` with full CLEAR vector.

## Critical skill gate

Hard block on `commit`, `release-gate`, `security`, `verify` if any
CLEAR dimension regresses **two runs in a row**. Other skills surface
dashboard regressions but don't block merge.

## Hard rules

- NEVER use single-run accuracy as a release signal.
- NEVER ignore cost dimension — runaway is a leading indicator of
  prompt-engineering decay.
- Provider switches must include a CLEAR-equivalent baseline run
  before cutover.
- Golden datasets are versioned alongside skills; PR changes to the
  dataset require justification in the spec.

## Common mistakes

- Treating efficacy as the only metric (cost variance dwarfs accuracy)
- Comparing across providers without re-running with identical prompts
- Forgetting reliability — a skill that works 90% of the time is
  unsafe at production scale
- Skipping assurance — policy violations don't show up in efficacy
