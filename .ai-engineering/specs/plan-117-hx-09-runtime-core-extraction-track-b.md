# Plan: spec-117-hx-09 Runtime Core Extraction - Track B

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-09` changes the local convergence engine inside one framework runtime. It should serialize with other runtime tracks because install, doctor, updater, and state/policy flows are tightly coupled.

### Phase 1: Flow Inventory And Boundary Freeze
**Gate**: One explicit matrix exists for installer, doctor, updater, resource adapters, and outer runtime probes.
- [x] T-1.1: Consolidate the `HX-09` exploration evidence into one governed flow matrix covering inspect, plan, apply, verify, resource adapters, and current outcome families (agent: build).
- [x] T-1.2: Run a governance review on preview purity, rollback boundaries, and ownership split with `HX-04`, `HX-05`, and `HX-10` before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass on 2026-05-02; no implementation tasks reopened.
- [x] T-1.3: Define the compatibility boundary for installer, doctor, and updater result models so migration can be adapter-first (agent: build, blocked by T-1.2).

### Phase 2: Reconciler Core Contract
**Gate**: One resource reconciler core exists with side-effect-free inspect/plan and explicit apply/verify semantics.
- [x] T-2.1: Write failing tests for inspect purity, explicit plan actions, apply rollback hooks, and postcondition verification (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the reconciler core and its action vocabulary over preserved resource adapters (agent: build, blocked by T-2.1).
- [x] T-2.3: Keep outer runtime probes outside the first reconciler cut while exposing stable adapter hooks for them (agent: build, blocked by T-2.2).

### Phase 3: Adapter Convergence
**Gate**: Installer, doctor, and updater all consume the shared reconciler instead of parallel local engines.
- [x] T-3.1: Write failing tests for installer adapter parity, doctor inspect/fix parity, updater preview/apply parity, and tool/hook/governance resource behavior (agent: build, blocked by T-2.3).
- [x] T-3.2: Move installer onto the reconciler core while preserving resource-domain semantics and user-visible behavior (agent: build, blocked by T-3.1).
- [x] T-3.3: Move doctor and updater onto reconciler-backed adapters while preserving compatibility JSON and rollback expectations (agent: build, blocked by T-3.2).

### Phase 4: Preview Purity And Rollback Proof
**Gate**: Preview is side-effect-free and apply owns explicit rollback and verification behavior.
- [x] T-4.1: Eliminate or isolate legacy side effects in preview and inspect paths (agent: build, blocked by T-3.3).
- [x] T-4.2: Tighten rollback, orphan-cleanup, and postcondition verification behavior under the reconciler core (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for preview purity, adapter parity, rollback behavior, and postcondition verification before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Runtime Policy
**Gate**: One reconciler core is proven, and deferred runtime-policy work remains explicit.
- [x] T-5.1: Flip strict runtime adapters to the reconciler-backed path once compatibility coverage is green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-04`, `HX-05`, and `HX-10`, especially kernel semantics, event ownership, and CLI thinning still outside Track B (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- Track B serializes with Tracks A and C unless scopes are proven disjoint.
- Inspect and plan become pure before broad adapter cutover.
- Outer runtime probes remain outside the first core cut.
- Kernel blocking semantics remain outside Track B.

## Exit Conditions

- One resource reconciler core exists.
- Installer, doctor, and updater consume that core through adapters.
- Preview is side-effect-free.
- Apply owns rollback and postcondition verification.