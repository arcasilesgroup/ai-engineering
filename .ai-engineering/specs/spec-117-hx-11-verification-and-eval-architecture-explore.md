# HX-11 Explore - Verification and Eval Architecture

This artifact captures the evidence gathered before writing the feature spec for `HX-11`.

## Scope

Feature: `HX-11` Verification and Eval Architecture.

Question: what must change so ai-engineering can classify checks coherently, organize replayable eval/scenario packs, measure reliability and performance over time, and keep those concerns distinct from the harness kernel and state plane?

## Evidence Summary

### Check Families Already Exist, But They Are Classified By Several Incompatible Vocabularies

- Local blocking gate/harness still spans legacy and newer authorities.
- Deterministic repo-governance validation lives under `validate` and `spec verify`.
- Advisory verification is a separate scored reporting family.
- CI job names, stack names, stage names, validator categories, and verify modes all describe overlapping realities through different labels.

The repo therefore has many check families but no single canonical plane taxonomy.

### Test Shape And Performance Surfaces Exist, But They Are Not Tied To One Verification Model

- Test suites are already split into unit, integration, e2e, perf, and cross-OS or cross-IDE workflows.
- Performance and stability checks already exist through pytest perf suites and dedicated budget workflows.
- Coverage policy is declared through constitution, manifest, and Sonar rather than one local cov-fail-under contract.

The pieces exist, but they are not yet joined into one measurement architecture.

### Eval Contract Exists In Prose, Not In Runtime Architecture

- `ai-eval` already describes eval definitions, baselines, and pass@k or pass^k metrics.
- The repo does not yet expose a concrete eval directory, registry, runner, or persisted baseline flow.
- Existing scenario-heavy integration tests are the closest seed material, but they are feature-local tests, not reusable eval packs.

This means the repo has the language for evals but not the architecture.

### Score And Report Surfaces Are Already Fragmented

- Verify already computes weighted scores.
- Perf budgets and install-time budgets are enforced elsewhere.
- CI writes its own workflow-local artifacts.
- No single scorecard ties cache behavior, retries, latency, parity, and scenario outcomes together.

Without a coherent architecture, measurement will continue to fragment into local reports instead of one governed eval plane.

### `HX-11` Must Sit Above `HX-04` And `HX-05`, Not Beside Them

- `HX-04` owns deterministic local execution and findings semantics.
- `HX-05` owns durable audit and derived state/report boundaries.
- `HX-11` should classify, group, replay, and score those results rather than re-executing or re-owning them.

If `HX-11` becomes a second execution engine or second truth store, it will duplicate the kernel or state plane.

## High-Signal Findings

1. The highest-value boundary for `HX-11` is a declarative verification taxonomy and measurement plane above `HX-04` and `HX-05`.
2. Every check needs one primary plane such as kernel, repo-governance, eval, shell-adapter, or perf-stability.
3. Verify must remain scored and explanatory rather than becoming a second blocker.
4. Existing scenario-style integration tests are the best seed for replayable eval packs.
5. Metrics, scores, and baselines should be derived outputs with provenance, not new peer authorities.

## Recommended Decision Direction

### Preferred Taxonomy Direction

- Define one canonical check-plane registry with stable IDs and metadata.
- Map current gate names, validator categories, verify modes, CI jobs, and perf suites into that registry.
- Ensure each check has exactly one primary plane even if it appears in multiple runners.

### Preferred Eval Direction

- Add replayable scenario packs and reliability metrics such as pass@k and pass^k.
- Reuse existing scenario-style tests as seed material rather than inventing a second execution engine.
- Keep evals distinct from verify scores and from deterministic kernel checks.

### Preferred Reporting Direction

- Make scores, pass rates, latency distributions, retry summaries, and trend reports derived outputs over kernel/state data and approved baselines.
- Keep only policy thresholds and approved classifications authoritative.
- Default broad perf and trend surfaces to reporting-only unless explicitly promoted to blocking budgets.

## Migration Hazards

- Plane renaming can break current docs, CI, and dashboards if stable IDs are not introduced first.
- Evals can become a shadow blocker if promoted without a clear path through repo-governance rules.
- Persisted baselines can drift into peer authorities if provenance and regeneration rules are weak.
- Runtime rewrites in `HX-08` to `HX-10` can invalidate naive test or check taxonomies if `HX-11` depends on current module layout.
- Classification drift will persist if the registry does not absorb current naming variants.

## Scope Boundaries For HX-11

In scope:

- canonical check-plane taxonomy
- eval/scenario-pack architecture
- reliability metrics and scorecards
- test-shape and measurement boundaries
- perf and stability baselines as a governed plane

Out of scope:

- harness kernel execution order and blocking semantics from `HX-04`
- state-plane event truth from `HX-05`
- context-pack lifecycle from `HX-07`
- mirror-family governance from `HX-03`

## Open Questions

- What minimum kernel result fields must `HX-04` guarantee so `HX-11` can classify without re-owning semantics?
- Should eval baselines live as versioned fixtures, CI artifacts, or regenerated projections?
- Which cross-IDE and shell failures are true contract breaks versus host noise?
- Which performance budgets deserve blocking status beyond explicit hot-path budgets?
- Should `HX-11` read task traces directly from the event stream or from an `HX-05` projection?

## Source Artifacts Consulted

- `src/ai_engineering/policy/gates.py`
- `src/ai_engineering/policy/orchestrator.py`
- `src/ai_engineering/policy/mode_dispatch.py`
- `src/ai_engineering/policy/checks/stack_runner.py`
- `src/ai_engineering/cli_commands/validate.py`
- `src/ai_engineering/validator/service.py`
- `src/ai_engineering/cli_commands/spec_cmd.py`
- `src/ai_engineering/cli_commands/verify_cmd.py`
- `src/ai_engineering/verify/service.py`
- `src/ai_engineering/verify/scoring.py`
- `tests/**`
- `.github/workflows/ci-check.yml`
- `.github/workflows/test-hooks-matrix.yml`
- `.github/workflows/install-time-budget.yml`
- `.github/workflows/worktree-fast-second.yml`
- `sonar-project.properties`
- `pyproject.toml`
- `.github/skills/ai-eval/SKILL.md`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md`