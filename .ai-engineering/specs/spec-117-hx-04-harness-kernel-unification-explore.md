# HX-04 Explore - Harness Kernel Unification

This artifact captures the evidence gathered before writing the feature spec for `HX-04`.

## Scope

Feature: `HX-04` Harness Kernel Unification.

Question: what must change so ai-engineering has one authoritative local check and findings kernel instead of split gate engines, split result envelopes, duplicated output policies, and partially duplicated retry or blocked-state behavior?

## Evidence Summary

### There Are Currently Multiple Authorities For Checks And Failure Semantics

- The newer orchestrated path in `src/ai_engineering/policy/orchestrator.py` plus `src/ai_engineering/policy/mode_dispatch.py` is the closest thing to a new kernel.
- Git hooks and workflow helpers still use the older gate engine in `src/ai_engineering/policy/gates.py`.
- Content-integrity validation is a separate deterministic family under `src/ai_engineering/validator/service.py`.
- Verify is a separate scored and explanatory family under `src/ai_engineering/verify/service.py`.
- CI merge authority still comes from workflow jobs and final fan-in rather than one shared harness call.

The repo therefore does not yet have one authoritative local execution engine for checks.

### Result Envelopes And Block Rules Are Fragmented

- The orchestrated path emits `GateFindingsDocument` and supports risk-accept partitioning, compact failure formatting, cache, and severity-based blocking.
- The legacy hook path returns `GateResult` and treats failed checks differently.
- Validators return `IntegrityReport`.
- Verify returns `VerifyScore`.
- CI aggregates shell and job outcomes independently.

This means the same repo can explain failure, severity, blocking, and remediation through several incompatible result models.

### The Newer Kernel Path Still Does Not Own All Real Execution

- The orchestrator has the most promising architecture, but its Wave 2 seams are still partial and some runner integration is stub-like.
- Hooks are still installed against the old engine.
- Some publish responsibility is split between service and CLI layers.
- Check selection still has dual paths in the stack runner.

`HX-04` is therefore a real convergence feature, not a small adapter cleanup.

### Artifact And Observability Flows Are Separate But Adjacent

- Findings artifacts live in gate findings and watch residuals.
- Event-chain artifacts live in `.ai-engineering/state/framework-events.ndjson`.
- Gate cache lives in its own tree.
- CI writes additional workflow-local artifacts.

These surfaces are related, but they do not have the same ownership. `HX-04` must unify the execution core without accidentally becoming the owner of all durable state and observability concerns.

### Sequencing And Concurrency Hazards Already Exist

- Mirror generation must complete before mirror validation.
- Event-emitting validations can race on the audit chain if they run in parallel.
- Shared findings and cache writes already show platform-specific atomic-write or timing scars.
- Pre-push stack tests already serialize because parallel I/O is flaky.

The kernel therefore needs explicit sequencing rules and single-writer expectations for shared outputs.

### `HX-04` Must Stay Thin Over State And Eval Ownership

- `HX-05` owns event vocabulary, task traces, and broader state-plane normalization.
- `HX-11` owns check taxonomy, eval packs, and broader verification architecture.
- `HX-04` should own deterministic local check execution, normalized findings envelopes, retry ceilings, loop caps, failure output, and adapter integration.

If `HX-04` absorbs state-plane or eval-plane ownership, the feature boundary will blur again.

## High-Signal Findings

1. The repo has two real local gate authorities today: the legacy hook engine and the newer orchestrator path.
2. One unified kernel must standardize check registration, mode resolution, execution order, normalized findings, retry and loop handling, and final blocking disposition.
3. Git hooks, CLI wrappers, workflow helpers, and CI should become adapters over that kernel rather than separate decision-makers.
4. Validate and verify should remain distinct reporting layers rather than becoming parallel gate authorities.
5. Shared findings publication and event-chain publication need explicit sequencing and ownership boundaries.

## Recommended Decision Direction

### Preferred Kernel Direction

- Make one kernel authoritative for check registration, mode/profile resolution, execution order, findings normalization, severity-to-exit policy, retry counters, loop caps, residual emission, and blocked-state output.
- Use the newer orchestrator and findings-envelope family as the seed surface.
- Replace the legacy hook engine with thin adapters over the kernel once feature parity exists.

### Preferred Adapter Direction

- Gate CLI variants, git hooks, and workflow helpers become transport/adaptation layers over the kernel.
- `validate` remains strict and category-based over its own report family.
- `verify` remains scored and explanatory over kernel and repo data, but does not become the authoritative blocker.
- CI continues to own matrix fan-out and merge wiring, but can consume machine-readable kernel results.

### Preferred Ownership Direction

- Kernel owns local execution truth and local findings envelopes.
- State-plane ownership such as event vocabulary, audit-chain guarantees, and task traces stays with `HX-05`.
- Eval and broader verification taxonomy stay with `HX-11`.

## Migration Hazards

- Repointing hooks or workflow helpers to the new kernel before real parity exists would weaken enforcement.
- Changing from `GateResult` semantics to `GateFindingsDocument` semantics will alter operator expectations unless compatibility is explicit.
- Required CI check names can break branch protection if kernel migration renames or collapses job surfaces carelessly.
- Shared publish responsibility across CLI and service layers can leave valid findings unpersisted.
- Audit-chain writers are append-only and race-prone if parallel event emission is widened carelessly.

## Scope Boundaries For HX-04

In scope:

- one authoritative local check kernel
- normalized findings envelope and residual output family
- check registration and mode/profile resolution
- retry ceilings, loop caps, and blocked disposition output
- hook and CLI adapter convergence over the kernel
- deterministic sequencing rules for shared findings outputs

Out of scope:

- state-plane event vocabulary and task traces from `HX-05`
- full verification and eval taxonomy from `HX-11`
- mirror-family ownership from `HX-03`
- work-plane schema from `HX-02`
- full CI job-graph redesign

## Open Questions

- Should the first cut include an explicit single-writer lock for framework-events and shared findings artifacts, or only sequencing rules plus adapters?
- Where exactly does blocked disposition stop and state mutation begin between `HX-04`, `HX-02`, and `HX-05`?
- What minimum classification fields should the kernel expose now so `HX-11` can later separate check families without breaking contracts?
- How much naming normalization is safe in `HX-04` before `HX-05` owns the wider event vocabulary?

## Source Artifacts Consulted

- `src/ai_engineering/policy/orchestrator.py`
- `src/ai_engineering/policy/mode_dispatch.py`
- `src/ai_engineering/policy/gates.py`
- `src/ai_engineering/policy/checks/stack_runner.py`
- `src/ai_engineering/hooks/manager.py`
- `src/ai_engineering/cli_commands/gate.py`
- `src/ai_engineering/validator/service.py`
- `src/ai_engineering/verify/service.py`
- `src/ai_engineering/verify/scoring.py`
- `src/ai_engineering/state/models.py`
- `src/ai_engineering/policy/watch_residuals.py`
- `src/ai_engineering/state/observability.py`
- `src/ai_engineering/state/audit.py`
- `src/ai_engineering/state/audit_chain.py`
- `.github/workflows/ci-check.yml`
- `.github/hooks/hooks.json`