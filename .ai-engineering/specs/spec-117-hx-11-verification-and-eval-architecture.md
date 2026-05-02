---
spec: spec-117-hx-11
title: Verification and Eval Architecture
status: done
effort: large
---

# Spec 117 HX-11 - Verification and Eval Architecture

## Summary

ai-engineering already runs many forms of checking, testing, scoring, and performance measurement, but they are classified by different vocabularies and owned by different surfaces. Local gate checks, repo-governance validation, scored verify flows, CI job names, scenario-style integration tests, and perf workflows all exist without one declarative taxonomy or one replayable eval plane. This feature adds a canonical verification taxonomy, replayable eval and scenario-pack architecture, measurement and scorecard rules, and explicit boundaries between blocking checks and reporting-only metrics. It sits above the harness kernel and state plane rather than replacing them.

## Goals

- Define one canonical check-plane taxonomy with stable IDs and metadata.
- Separate kernel checks, repo-governance checks, evals, shell-adapter checks, and perf-stability checks cleanly.
- Add replayable eval and scenario-pack architecture using existing scenario-heavy tests as seed material.
- Define reliability metrics and derived scorecards such as pass@k, pass^k, trend reports, and latency or retry summaries.
- Normalize test-shape and measurement boundaries across unit, integration, e2e, perf, parity, and resilience suites.
- Keep blocking versus reporting-only boundaries explicit and governed.
- Avoid creating a second execution engine or second durable truth store.

## Non-Goals

- Replacing `HX-04` as the authority for local execution order, retry policy, loop caps, or blocking semantics.
- Replacing `HX-05` as the authority for event truth, task traces, or derived-state boundaries.
- Replacing `HX-07` as the authority for context-pack lifecycle.
- Rewriting mirror-family governance from `HX-03`.
- Making every metric or score a blocking merge gate by default.

## Decisions

### D-117-53: `HX-11` defines one canonical verification taxonomy above the kernel

Every check receives exactly one primary plane such as kernel, repo-governance, eval, shell-adapter, or perf-stability. Stable IDs and metadata map current names across local gate surfaces, verify modes, validator categories, CI jobs, and perf suites into one registry.

**Rationale**: the current system has many check families but no single classification plane.

### D-117-54: Evals are replayable reliability artifacts, not a second blocker path

Eval and scenario packs measure reliability over time through repeatable packs, pass@k or pass^k, regression baselines, and similar metrics. They do not become a separate silent blocker path; if any eval becomes blocking, it is promoted through the governed repo-governance path.

**Rationale**: evals should measure capability drift, not quietly replace the kernel or governance gates.

### D-117-55: Verify remains scored and explanatory

`verify` remains a scored and explanatory reporting family that can aggregate kernel and governance inputs, but it does not redefine pass/fail authority.

**Rationale**: verify already serves explanation and synthesis better than deterministic blocking.

### D-117-56: Scores, pass rates, and baselines are derived outputs with provenance

Policy thresholds and approved plane classifications may be authoritative, but verify scores, pass rates, latency distributions, retry summaries, and trend reports remain derived outputs with regeneration paths.

**Rationale**: otherwise measurement views would become yet another competing truth source.

### D-117-57: The architecture must be rewrite-safe for later runtime tracks

`HX-11` depends on stable contracts, scenario fixtures, and plane taxonomy rather than current module layout, so later runtime rewrites in `HX-08` through `HX-10` do not force a taxonomy rewrite.

**Rationale**: verification architecture should survive internal implementation churn.

## Taxonomy Matrix

| Family | Primary plane | Current names | Reporting surface | Blocking default |
| --- | --- | --- | --- | --- |
| Kernel gate checks | kernel | `gitleaks`, `ruff`, `ruff-check`, `ty`, `pytest-smoke`, `validate`, `semgrep`, `pip-audit`, `pytest-full` | local gate, CI | blocking |
| Validator categories | repo-governance | `file-existence`, `mirror-sync`, `counter-accuracy`, `cross-reference`, `manifest-coherence`, `skill-frontmatter`, `required-tools` | `validate`, CI | blocking |
| Verify specialists | verify-report | `verify:governance`, `verify:security`, `verify:architecture`, `verify:quality`, `verify:feature` | `verify` | reporting-only |
| Shell adapter parity | shell-adapter | `test-hooks-matrix`, `.github/workflows/test-hooks-matrix.yml` | CI | blocking |
| Perf and stability | perf-stability | `install-time-budget`, `worktree-fast-second`, `tests/perf`, `pytest-perf` | CI, perf | mixed, explicit |
| Eval scenario packs | eval | `eval.scenario.seed` | eval, verify | reporting-only |

## Implementation Cutover Status

- `src/ai_engineering/verify/taxonomy.py` now defines the canonical registry, stable IDs, primary planes, reporting surfaces, test-shape boundaries, eval scenario packs, replay outcomes, and reliability scorecards.
- Registry validation enforces unique stable IDs, unique current-name aliases, and provenance for derived metrics.
- `build_seed_eval_pack()` records replayable scenario metadata over existing pytest runners; execution remains delegated to existing test infrastructure.
- `build_replay_outcome()` computes pass@k and pass^k as derived metrics, and `summarize_replay_outcomes()` produces per-pack regression summaries.
- `build_reliability_scorecard()` derives pass rate, pass^k, regression count, p95 latency, retry count, and provenance-backed scorecard metadata.
- Verify findings now carry optional `stable_id` and `primary_plane` fields when sourced from known gate checks or validator categories.

## Compatibility Boundary

- Current check names remain accepted aliases; stable IDs are additive and land before any broad rename.
- `verify` remains explanatory and scored; taxonomy metadata does not change deterministic pass/fail ownership.
- CI workflow names and perf labels are mapped, not rewritten.
- Eval packs are replay metadata only; they do not execute checks directly and do not become shadow blockers.
- Derived metrics and scorecards require provenance and are reporting-only unless promoted through governed repo-governance rules.

## Deferred Boundaries

- `HX-04` still owns kernel execution order, retry policy, loop caps, and blocking semantics.
- `HX-05` still owns event truth, task traces, and any trace projection consumed by reports.
- `HX-08` through `HX-10` may add runtime-core fields or scenario coverage, but the taxonomy is anchored to contracts and scenario packs instead of module layout.
- Broader CI dashboard cleanup and historical baseline storage remain follow-on reporting work.
- Final guard/review remains deferred to the end-of-implementation review pass requested by the user.

## Risks

- **Naming migration risk**: plane normalization can break docs and CI if stable IDs do not precede renaming. **Mitigation**: introduce canonical IDs before broad relabeling.
- **Shadow-blocker risk**: evals or derived scores can become de facto blockers without governance. **Mitigation**: keep blocking status explicit and routed through repo-governance contracts.
- **Baseline drift risk**: persisted baselines can become peer authorities. **Mitigation**: require provenance and regeneration semantics.
- **Layout-coupling risk**: tying classification to current code layout will break under runtime refactors. **Mitigation**: anchor the taxonomy to contracts and scenario packs, not modules.

## References

- doc: .ai-engineering/specs/spec-117-hx-11-verification-and-eval-architecture-explore.md
- doc: .ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md
- doc: .ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .github/skills/ai-eval/SKILL.md
- doc: src/ai_engineering/verify/service.py
- doc: src/ai_engineering/verify/scoring.py
- doc: tests/
- doc: .github/workflows/ci-check.yml

## Open Questions

- Deferred to `HX-04`: any new kernel result fields beyond current check names and gate findings.
- Deferred reporting follow-up: durable baseline storage can be versioned fixtures, CI artifacts, or regenerated projections; this slice only requires provenance refs.
- Resolved in this slice: shell/cross-IDE checks have a separate `shell-adapter` plane so host noise can be reported without being confused with kernel failures.
- Resolved in this slice: perf budgets are explicitly classified; `install-time-budget` is blocking while broader perf/trend surfaces default to reporting-only.
- Deferred to `HX-05`: direct event-stream versus trace-projection joins for future scorecard generation.