# Plan: spec-117-hx-02 Work Plane and Task Ledger

## Pipeline: full
## Phases: 5
## Tasks: 17 (build: 13, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-02` changes the execution model inside one repository and one installed-workspace shape. It introduces a spec-scoped work-plane contract, task-ledger state, compatibility views for legacy buffers, and a shared active-work-plane resolver consumed across CLI, runtime, validation, telemetry, and orchestration layers. That remains a modular-monolith change: one operational unit, strong internal seams, and a need for careful migration across many readers.

**Closure Reconciliation:** `HX-02` now meets the closure standard for this `spec-117` wave. Earlier contract, schema, resolver, CLI, and consumer-integration phases are marked complete through the implemented runtime surfaces and the cumulative `T-4.3` / `T-5.3` proof bundles; the remaining `T-4.2` validation scope was closed by the lifecycle-coherence slice recorded in this plan.

### Phase 1: Contract And Compatibility Boundary
**Gate**: The feature has one explicit work-plane contract, one build-readiness rule, and one compatibility boundary for legacy singleton buffers.
- [x] T-1.1: Consolidate the `HX-02` exploration evidence into one governed work-plane contract covering active pointer, task ledger, handoffs, evidence, current summary, and history summary (agent: build).
- [x] T-1.2: Run a governance review on the build-start rule, portfolio-wide readiness requirement, and compatibility expectations for legacy buffers before implementation begins (agent: guard, blocked by T-1.1).
- [x] T-1.3: Define the compatibility boundary for `spec.md`, `plan.md`, `_history.md`, `done.md`, and install/bootstrap behavior so migration can be dual-read before cutover (agent: build, blocked by T-1.2).

### Phase 2: Task-Ledger Schema And Artifact Topology
**Gate**: One structured task-ledger model exists, with fixtures/templates for valid and invalid task states plus clear separation of current, history, handoff, and evidence artifacts.
- [x] T-2.1: Write failing schema and fixture coverage for task identity, status transitions, dependency edges, write scopes, blocked reasons, handoff refs, and evidence refs (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the task-ledger schema/models and the spec-local artifact topology in live and template workspace assets (agent: build, blocked by T-2.1).
- [x] T-2.3: Add templates or generated views for build, review, verify, blocked, current, and history artifacts without making them peer authorities of the ledger (agent: build, blocked by T-2.2).
- [x] T-2.4: Run a governance review on ledger semantics, artifact ownership, and write-scope boundaries before consumer wiring begins (agent: guard, blocked by T-2.3).

### Phase 3: Active Resolver And CLI Lifecycle
**Gate**: Runtime and CLI flows can resolve, initialize, inspect, and transition the active work plane without relying on hard-coded singleton buffers.
- [x] T-3.1: Write failing tests for active-pointer resolution, spec-local work-plane discovery, plan/spec coherence, and compatibility views for legacy buffer consumers (agent: build, blocked by T-2.4).
- [x] T-3.2: Implement the shared active-work-plane resolver and spec-local directory lifecycle in the owned runtime slice (agent: build, blocked by T-3.1).
- [x] T-3.3: Update `spec` CLI and maintenance/reset flows so they initialize, switch, summarize, and close work through the resolver rather than by overwriting singleton buffers (agent: build, blocked by T-3.2).
- [x] T-3.4: Preserve or generate compatibility views for existing user-facing paths so fresh installs and legacy flows remain operable during migration (agent: build, blocked by T-3.3).

### Phase 4: Validation, Telemetry, And Consumer Integration
**Gate**: Validators, policy gating, telemetry, work-item sync, and PR generation consume the new work-plane contract directly and reject invalid task states.
- [x] T-4.1: Update work-item sync, PR description generation, verify service, gate-cache invalidation, observability, audit, and orchestration readers to use the shared resolver and ledger-derived state (agent: build, blocked by T-3.4).
- [x] T-4.2: Add task-ledger and work-plane validation for duplicate overlapping writes, invalid dependencies, missing handoffs/evidence, illegal terminal states, and active spec/plan mismatch (agent: build, blocked by T-4.1).
	- Status: `task-dependency-validation` slice = `DONE_WITH_CONCERNS`. Concern: focused Sonar snippet analysis failed to initialize, but focused pytest, `ai-eng validate -c manifest-coherence`, editor problems, and specialist review all passed. Remaining `T-4.2` scope: overlapping writes, missing handoffs/evidence, illegal terminal states, and active spec/plan mismatch.
	- Status: `task-state-consistency` slice = `DONE`. Focused pytest, `ai-eng validate -c manifest-coherence`, editor problems, and specialist review all passed.
	- Status: `task-artifact-reference-validation` slice = `DONE`. Focused pytest, `ai-eng validate -c manifest-coherence`, editor problems, and specialist review all passed after adding explicit absolute-path and escaping-path regression coverage.
	- Status: `task-write-scope-duplicate-validation` slice = `DONE`. Focused pytest, `ai-eng validate -c manifest-coherence`, editor problems, and specialist review all passed after adding explicit overlap-vs-exact regression coverage.
	- Status: `lifecycle-coherence-validation` slice = `DONE`. Focused task-ledger and manifest-coherence tests passed after adding overlap-aware `writeScope` validation, active spec/plan identity mismatch detection, lifecycle artifact requirements, and blockedReason state consistency. Live `manifest-coherence` shows all `HX-02` task-ledger checks green; the remaining validator failure is unrelated pre-existing control-plane authority drift.
	- Status: `T-4.2` is `DONE`. No explicit validation scope remains open for duplicate overlapping writes, invalid dependencies, missing handoffs/evidence, illegal terminal states, or active spec/plan mismatch.
- [x] T-4.3: Run targeted verification for resolver behavior, compatibility views, and validator failure modes before strict cutover (agent: verify, blocked by T-4.2).
	- Status: `DONE`. Focused `TestManifestCoherence` plus `ai-eng validate -c manifest-coherence` passed, and the targeted resolver/compatibility bundle passed with `16 passed` across work-plane, activation, reset, CLI activation, orchestrator hash, and activation-then-reset integration coverage.
	- Reconciliation note: this targeted bundle now stands with the completed `T-4.2` lifecycle-coherence slice as the validator and resolver closeout proof.

### Phase 5: Cutover Proof And Cleanup Envelope
**Gate**: Build readiness is durable, compatibility behavior is proven, and any deferred cleanup is explicit instead of hidden inside the work plane.
- [x] T-5.1: Flip strict runtime and validator checks so build readiness and work-plane coherence derive from the ledger and resolver, not placeholder text or unchecked global buffers (agent: build, blocked by T-4.3).
	- Status: `active-spec-ledger-coherence` validator sub-slice = `DONE`. Focused pytest, full `TestManifestCoherence`, `ai-eng validate -c manifest-coherence`, editor problems, and review all passed after tightening the pointer-aware regression to prove the resolved work plane controls both `spec.md` and `task-ledger.json` selection.
	- Status: `wave1-ledger-aware-active-spec-gate` runtime/orchestrator sub-slice = `DONE`. Focused Wave 1 regressions and the full `tests/unit/test_orchestrator_wave1.py` file passed after fixing explicit `project_root` cwd propagation, resolved-ledger idle discrimination, and relative-path convergence tracking.
	- Status: `work-items-ledger-aware-active-spec-dir` runtime/work-items sub-slice = `DONE`. Focused live-ledger regression, focused active-spec-root coverage, the full `tests/unit/test_work_items_service.py` file, and narrow Ruff checks all passed after mirroring the existing Wave 1 placeholder-to-ledger rule while preserving done-ledger and unreadable-ledger idle behavior.
	- Status: `spec-list-ledger-aware-active-work-plane` runtime/CLI sub-slice = `DONE`. Focused live-ledger regression, focused placeholder-spec coverage, the full `tests/unit/test_spec_cmd.py` file, and narrow Ruff checks all passed after teaching `spec_list()` to consult the resolved ledger and fall back to the work-plane directory name when the compatibility spec buffer is still placeholder text.
	- Status: `state-audit-ledger-aware-active-spec-id` audit sub-slice = `DONE`. Focused `TestAuditEnrichment` coverage and local Ruff checks passed after teaching `_read_active_spec()` to consult the resolved ledger, keeping the raw work-plane name as canonical lookup identity, and removing stale audit spec-id caching.
	- Status: `pr-description-ledger-aware-active-spec-id` PR reader sub-slice = `DONE`. The full `tests/unit/test_pr_description.py` file and narrow Ruff checks passed after teaching `_read_active_spec()` to consult the resolved ledger, preserving raw lookup identity for linked issues, and normalizing only user-facing title/body text.
	- Status: `T-5.1` is `DONE` for the known strict readers in `HX-02`; build readiness and identifier-driven runtime surfaces now derive active-spec context from the resolver plus ledger rather than placeholder prose alone.
- [x] T-5.2: Document deferred cleanup for `HX-04`, `HX-05`, and `HX-06`, including any temporary compatibility views or event-model limitations left intentionally in place (agent: build, blocked by T-5.1).
	- Status: `DONE`. `HX-02` now has an explicit deferred-cleanup routing section, and the `HX-04`, `HX-05`, and `HX-06` specs each now state the exact compatibility-view, event-model, or capability-enforcement follow-on work inherited from the work-plane cutover.
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).
	- Status: `DONE`. The focused proof bundle passed with `185 passed` across resolver, maintenance, CLI, runtime-reader, validator, and reset-integration slices, and the final `cross-reference` plus `file-existence` validators both passed in the same closeout run.
	- Reconciliation note: this proof bundle is now accepted as part of the full `HX-02` closure envelope together with the completed `T-4.2` lifecycle-coherence validation slice.

## Sequencing Notes

- The active resolver must land before consumer migration can be considered real.
- Task-ledger schema and artifact topology must exist before CLI or validator semantics can be tightened safely.
- Compatibility views for `spec.md` and `plan.md` must be preserved until install/bootstrap, CLI, and downstream readers are green on the resolver-backed model.
- Build-start gating should tighten only after portfolio and feature-level readiness can be derived from durable artifacts.
- Live and template workspace work-plane assets must move together.

## Exit Conditions

- One authoritative active-work-plane resolver exists.
- A first-class task ledger records owner role, dependencies, write scope, handoffs, evidence, and blocked metadata.
- Current summary, history summary, handoffs, and evidence are distinct artifact classes.
- Legacy singleton buffers are compatibility or generated views rather than peer authorities.
- Build readiness is represented and validated through durable work-plane state.
- Focused validation proves spec/plan coherence, file existence, and cross-reference integrity for the new work plane.