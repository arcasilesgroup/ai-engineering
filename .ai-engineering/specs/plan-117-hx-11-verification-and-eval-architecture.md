# Plan: spec-117-hx-11 Verification and Eval Architecture

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-11` changes one repository-wide measurement and classification layer spanning check taxonomy, eval packs, verify score composition, test-shape reporting, and perf or stability baselines. It remains a modular-monolith change because it still sits inside one framework runtime and repo, but it must stay above the kernel and state planes rather than competing with them.

### Phase 1: Taxonomy Boundary And Classification Contract
**Gate**: One explicit boundary exists between kernel execution, repo-governance validation, evals, shell-adapter checks, and perf-stability checks before any reporting or baseline work begins.
- [x] T-1.1: Consolidate the `HX-11` exploration evidence into one governed verification taxonomy matrix covering check families, current naming variants, ownership planes, and reporting surfaces (agent: build).
- [x] T-1.2: Run a governance review on blocking versus reporting-only boundaries, derived versus authoritative metrics, and the ownership split with `HX-04` and `HX-05` before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass on 2026-05-02; no implementation tasks reopened.
- [x] T-1.3: Define the compatibility boundary for current check names, verify modes, CI job labels, and perf suite labels so migration can be stable-ID-first (agent: build, blocked by T-1.2).

### Phase 2: Canonical Registry And Reporting Inputs
**Gate**: One canonical verification registry exists with stable IDs and metadata strong enough for reporting, replay, and baseline generation.
- [x] T-2.1: Write failing tests or invariant coverage for the canonical check-plane registry, stable IDs, ownership planes, and derived-metric provenance rules (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the registry and map existing gate names, validator categories, verify modes, CI jobs, and perf suites onto it without changing upstream execution ownership (agent: build, blocked by T-2.1).
- [x] T-2.3: Keep verify scored and explanatory while aligning its inputs to the canonical registry rather than freeform current naming (agent: build, blocked by T-2.2).

### Phase 3: Eval Packs And Test-Shape Architecture
**Gate**: Replayable eval/scenario packs and explicit test-shape boundaries exist without creating a second execution engine.
- [x] T-3.1: Write failing tests for eval-pack definitions, scenario-pack replay metadata, baseline provenance, and test-shape boundaries across unit, integration, e2e, perf, parity, and resilience suites (agent: build, blocked by T-2.3).
- [x] T-3.2: Implement the eval/scenario-pack architecture using current scenario-heavy tests as seed material and keeping runtime execution delegated to existing runners (agent: build, blocked by T-3.1).
- [x] T-3.3: Add reporting hooks for replay outcomes, pass@k or pass^k, and per-pack regression summaries as derived outputs (agent: build, blocked by T-3.2).

### Phase 4: Perf And Reliability Measurement
**Gate**: Perf, stability, and reliability baselines are measurable, derived, and explicitly classified as blocking or reporting-only.
- [x] T-4.1: Normalize perf and stability baseline inputs across existing perf tests and workflow budgets without making them peer authorities (agent: build, blocked by T-3.3).
- [x] T-4.2: Add scorecards and reports for reliability, latency, retry behavior, cache effects, and regression trends with explicit provenance and blocking status rules (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for taxonomy mapping, eval-pack replay, and derived-metric provenance before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Execution Ownership
**Gate**: Verification architecture is proven end to end, and deferred execution/state ownership remains explicit.
- [x] T-5.1: Flip reporting consumers and governed blocking hooks to the canonical taxonomy once stable IDs, compatibility shims, and derived-metric proofs are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-04`, `HX-05`, and runtime tracks, especially any upstream result-field gaps or scenario coverage gaps that still need exposure (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration/perf slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- `HX-11` consumes kernel and state outputs rather than re-owning execution.
- Stable IDs land before broad renaming or dashboard/report cleanup.
- Eval packs reuse current runners; they do not invent a second execution engine.
- Derived metrics and baselines require provenance before they can persist.
- Blocking promotion for evals or perf budgets must route through governance rules, not side channels.

## Exit Conditions

- One canonical verification taxonomy exists with stable IDs.
- Evals and scenario packs are replayable and distinct from kernel execution.
- Verify aligns to the taxonomy while remaining explanatory rather than authoritative.
- Reliability, perf, and trend scorecards are derived outputs with provenance.
- Blocking versus reporting-only boundaries are explicit and governed.