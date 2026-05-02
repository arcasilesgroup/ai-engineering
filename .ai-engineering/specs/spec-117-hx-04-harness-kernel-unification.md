---
spec: spec-117-hx-04
title: Harness Kernel Unification
status: done
effort: large
---

# Spec 117 HX-04 - Harness Kernel Unification

## Summary

ai-engineering currently has split local check authority. The legacy hook gate engine, the newer orchestrated gate path, validator families, verify scoring, and CI job fan-in each decide parts of check execution and failure semantics through different result models and different blocking rules. This feature unifies the local execution core so one authoritative harness kernel owns check registration, mode and profile resolution, execution order, normalized findings, retry ceilings, loop caps, residual output, and final blocking disposition. Git hooks, gate CLI variants, workflow helpers, and other local callers become adapters over that kernel. State-plane event vocabulary and eval taxonomy remain outside this feature.

## Goals

- Make one kernel the sole deterministic authority for local check execution and local blocking disposition.
- Standardize one normalized findings envelope for kernel outcomes and residuals.
- Unify check registration, mode/profile resolution, execution order, risk-accept partitioning, retry ceilings, and loop caps.
- Replace separate local gate authorities in hooks and CLI flows with thin adapters over the kernel.
- Keep failure output action-oriented and LLM-readable without making prose the authoritative source of truth.
- Preserve explicit sequencing and single-writer expectations for shared findings and adjacent audit artifacts.
- Avoid absorbing state-plane or eval-plane ownership that belongs to later features.

## Non-Goals

- Redesigning the full CI job graph or merge-protection topology.
- Replacing validator or verify with one universal report family.
- Owning event vocabulary normalization, task traces, or broader state-plane governance from `HX-05`.
- Owning check classification, eval packs, or broader verification architecture from `HX-11`.
- Rewriting work-plane schema from `HX-02` or mirror-family governance from `HX-03`.

## Decisions

### D-117-36: One harness kernel becomes the only deterministic authority for local check execution

`HX-04` converges on one kernel that owns check registration, mode/profile resolution, execution order, findings normalization, severity-to-disposition policy, retry ceilings, loop caps, residual output, and blocked disposition output.

**Rationale**: the repo currently has at least two real local gate authorities and several incompatible result families, which weakens determinism and makes migration risky.

### D-117-37: Local callers become adapters over the kernel rather than separate decision-makers

Gate CLI variants, git hooks, and workflow helpers must become transport or adapter layers over the kernel. They may choose invocation surface and formatting, but they do not redefine check policy or blocking semantics.

**Rationale**: today hooks and CLI still use different engines and therefore different rules.

### D-117-38: The kernel uses one normalized findings envelope and keeps publish responsibility explicit

The kernel must return one stable structured findings envelope for authoritative local outcomes and one compatible residual output model. Publish responsibility must be explicit so findings are not silently constructed without being persisted.

**Rationale**: result construction and result publication are currently split across layers, which creates sequencing hazards and weakens auditability.

### D-117-39: Validate and verify remain distinct reporting families, not parallel gate authorities

`validate` remains strict and category-based over integrity invariants; `verify` remains scored and explanatory. Both may consume kernel data where relevant, but neither becomes a second local gate authority in this feature.

**Rationale**: validator and verify families serve different purposes and should not be collapsed into the kernel prematurely.

### D-117-40: Serialized output families remain serialized and auditable

Mirror sync before mirror validation, event-emitting validations in sequence, and single-writer expectations for shared findings artifacts remain explicit kernel or adapter rules where they affect local execution safety.

**Rationale**: the repo already has proven race hazards around shared artifacts and audit-chain writers.

### D-117-41: `HX-04` stops at local execution truth and defers state/eval ownership to later features

`HX-04` owns the local harness kernel and its authoritative output envelope. It does not own broader event vocabulary, task traces, scorecards, eval classification, or perf baselines.

**Rationale**: those concerns belong to `HX-05` and `HX-11`, and absorbing them here would recreate split ownership.

## Risks

- **Parity regression**: swapping hook and CLI callers onto the new kernel before real parity exists could weaken enforcement. **Mitigation**: move adapters only after failing coverage and parity proof exist.
- **Semantic migration risk**: replacing `GateResult`-style behavior with findings-envelope behavior changes operator expectations. **Mitigation**: make compatibility rules explicit and preserve deterministic block semantics.
- **Artifact race risk**: shared findings and audit appenders can still race if publish responsibility is widened carelessly. **Mitigation**: keep serialized families explicit and single-writer where required.
- **CI contract risk**: kernel changes can accidentally break required workflow names or downstream expectations. **Mitigation**: keep CI orchestration outside the first cut and expose machine-readable kernel output instead.
- **Scope bleed risk**: event vocabulary and eval taxonomy can pull the feature too wide. **Mitigation**: defer those ownership planes explicitly.

## Authority Matrix And Cut Line

### Local Gate Engines

| Surface | Current path | Current role | `HX-04` cut line |
| --- | --- | --- | --- |
| Orchestrated gate path | `src/ai_engineering/policy/orchestrator.py`, `src/ai_engineering/policy/mode_dispatch.py`, `src/ai_engineering/policy/checks/stack_runner.py` | Closest existing kernel seed for mode resolution, findings, and severity-based blocking | Promote to the sole deterministic local execution authority |
| Legacy hook gate engine | `src/ai_engineering/policy/gates.py` | Older local gate authority still used by hooks and helper paths | Demote to compatibility-only behavior, then replace with thin adapters |
| Content-integrity validator family | `src/ai_engineering/validator/service.py` | Deterministic integrity reporting over category invariants | Stay downstream as strict reporting, not a peer gate authority |
| Verify scoring family | `src/ai_engineering/verify/service.py`, `src/ai_engineering/verify/scoring.py` | Scored and explanatory quality readout | Stay downstream as advisory/scored reporting, not the local blocker |
| CI fan-in | `.github/workflows/ci-check.yml` | Downstream merge and workflow authority | Consume kernel-compatible outputs without becoming the local execution kernel |

### Adapter Layers

| Surface | Current path | Current role | `HX-04` cut line |
| --- | --- | --- | --- |
| Git hook manager | `src/ai_engineering/hooks/manager.py` | Installs and routes hook entry points through legacy engine behavior | Keep as transport and installation adapter only |
| Gate CLI surface | `src/ai_engineering/cli_commands/gate.py` | Invokes checks and formats local operator output | Keep as invocation/reporting adapter only |
| Workflow helpers | `src/ai_engineering/policy/gates.py`, `.github/hooks/hooks.json` | Reuse legacy local gate decisions across helper flows | Repoint to kernel-backed adapters once parity is proven |

### Result Models

| Surface | Current model | Current owner | `HX-04` cut line |
| --- | --- | --- | --- |
| Orchestrated local checks | `GateFindingsDocument` plus residual formatting | Orchestrated gate path | Becomes the normalized kernel envelope seed |
| Legacy hook execution | `GateResult` | Legacy hook gate engine | Preserve only for compatibility during migration |
| Integrity validation | `IntegrityReport` | Validator family | Remains validator-owned and category-specific |
| Scored verification | `VerifyScore` | Verify family | Remains verify-owned and explanatory |
| Workflow/job outcomes | Shell exit codes and job fan-in state | CI workflows | Remain downstream consumption signals |

### Serialized Artifact Families

| Surface | Current path | Current role | `HX-04` cut line |
| --- | --- | --- | --- |
| Findings and residual outputs | `src/ai_engineering/policy/watch_residuals.py` and orchestrated findings publication | Local findings envelope and residual emission | Kernel-owned publish semantics must be explicit and single-writer-safe |
| Audit chain and framework events | `.ai-engineering/state/framework-events.ndjson`, `src/ai_engineering/state/audit.py`, `src/ai_engineering/state/audit_chain.py`, `src/ai_engineering/state/observability.py` | Durable event vocabulary and append-only audit trail | `HX-04` may enforce serialized call order but does not own the state-plane schema |
| Gate cache | Kernel-adjacent cache tree under the policy engine | Local execution residue and reuse hints | Kernel-owned cache behavior stays local and deterministic |
| Workflow-local artifacts | `.github/workflows/ci-check.yml` outputs | CI-only aggregation and merge-facing evidence | Stay outside the first local-kernel cut |

### Cut Line Summary

- `HX-04` owns deterministic local check execution, normalized findings and residual output, retry ceilings, loop caps, and blocked disposition output.
- Hook, CLI, and workflow-helper surfaces become adapters over the kernel instead of policy-owning peers.
- `validate` and `verify` remain distinct reporting families over kernel or repo data rather than alternate gate authorities.
- State-plane vocabulary, task traces, and broader audit semantics stay with `HX-05`.
- Check taxonomy, eval packs, and broader measurement architecture stay with `HX-11`.

## Compatibility Boundary

### Legacy Hook Gate Behavior Boundary

- Generated local hook entry points still route through `ai-eng gate pre-commit` and `ai-eng gate pre-push`, and those gate commands still resolve through `src/ai_engineering/policy/gates.py` rather than the orchestrated kernel path.
- `HX-04` must therefore preserve parity-first compatibility between the legacy hook-gate dispatch path and the orchestrated kernel until hook adapters can move without weakening local blocking behavior.

### Findings Publication Boundary

- `GateFindingsDocument` is the intended normalized findings envelope, but the live repo still splits publish responsibility between orchestrator-side emission and gate-CLI-side persistence of `gate-findings.json`.
- `HX-04` must preserve a readable compatibility path for findings publication until one explicit publish owner can replace the split flow without changing failure semantics.

### CI-Facing Semantics Boundary

- Existing workflow job names, gate invocation surfaces, and downstream fan-in remain compatibility inputs for branch protection and operator expectations during the first kernel cut.
- `HX-04` may expose machine-readable kernel-compatible outputs to CI consumers, but it must not treat Phase 1 as a CI-graph redesign or rename required check surfaces prematurely.

### Residual Output Boundary

- Residual outputs remain compatibility-safe siblings of the normalized findings envelope through `watch_residuals` and adjacent gate-finding artifacts.
- `HX-04` must preserve residual-output readability and expected file-level semantics until the kernel owns one explicit residual contract and parity coverage proves the cutover.

## Deferred Cleanup From HX-02

- `HX-02` intentionally left task-state semantics separate from kernel outcome semantics. `HX-04` still needs to define the normalized kernel result envelope, blocked disposition, retry and loop limits, and adapter behavior that later work-plane mutations may rely on.
- The compatibility `spec.md` and `plan.md` views preserved during the `HX-02` migration must remain adapter inputs only. `HX-04` should consume the shared resolver and authoritative kernel output rather than allowing hook or CLI formatting paths to become a second authority.
- Any future hardening of how local check failures or blocked outcomes project into task-lifecycle changes must be driven from the kernel boundary here and consumed downstream by `HX-02` and `HX-05`.

## Deferred Cleanup From HX-03

- `HX-03` now depends on serialized local execution for mirror-affecting flows such as ordered `sync` before integrity validation and deterministic provider-surface repair in updater paths. If local execution converges under one kernel, `HX-04` must own that sequencing explicitly rather than letting mirror helpers become a second authority.
- Any future unification of updater, sync, and validation adapters must preserve the single-writer expectations and residual-output ordering that `HX-03` now enforces locally.

## Deferred Ownership After T-5.1

### HX-05 - State Plane And Observability Normalization

- Normalize the event vocabulary beyond the minimal append-safety rules that `HX-04` now enforces. `HX-04` may serialize writers, but `HX-05` owns the canonical naming, schema cleanup, and lifecycle meaning of those events.
- Add task traces that join kernel runs, work-plane task state, and operator-visible reports. `HX-04` only emits or protects local execution artifacts; it does not own durable trace projection.
- Define scorecards and durable rollups over kernel runs, validations, and workflow activity. `HX-04` now produces safer inputs for those reports, but `HX-05` owns the projection model and report semantics.
- Own any durable blocked-state mutation or task-lifecycle projection that should follow repeated kernel failures. `HX-04` stops at blocked disposition output and does not mutate long-lived task state.

### HX-11 - Verification And Eval Architecture

- Own the long-term check taxonomy and naming cleanup for kernel checks, repo-governance checks, shell checks, and eval scenarios. `HX-04` only preserves current compatible check ids well enough to finish the local cutover.
- Define eval packs, scenario coverage, and performance baselines on top of the now-stable local kernel. `HX-04` proves local execution convergence; it does not classify or score eval reliability over time.
- Separate CI-only aggregation and merge-facing proof from local kernel truth. `HX-04` can expose kernel-compatible outputs to CI, but `HX-11` owns how multi-job aggregation, required-check presentation, and measurement bundles are classified and reported.
- Own any later split between advisory verification, deterministic gating, and benchmark-style eval suites. `HX-04` intentionally keeps those families adjacent but distinct rather than redesigning them.

## References

- doc: .ai-engineering/specs/spec-117-hx-04-harness-kernel-unification-explore.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: src/ai_engineering/policy/orchestrator.py
- doc: src/ai_engineering/policy/gates.py
- doc: src/ai_engineering/policy/mode_dispatch.py
- doc: src/ai_engineering/policy/checks/stack_runner.py
- doc: src/ai_engineering/hooks/manager.py
- doc: src/ai_engineering/cli_commands/gate.py
- doc: src/ai_engineering/validator/service.py
- doc: src/ai_engineering/verify/service.py
- doc: src/ai_engineering/state/models.py
- doc: src/ai_engineering/policy/watch_residuals.py
- doc: .github/workflows/ci-check.yml

## Open Questions

- Should the first kernel cut add explicit locking for shared findings or audit writers, or only enforce serialized calling order?
- Where exactly should blocked disposition hand off into durable state mutation across `HX-02`, `HX-04`, and `HX-05`?
- What minimum result-classification fields are needed now so later eval architecture work can extend them safely?
- How much naming cleanup is safe before `HX-05` owns the wider event vocabulary?