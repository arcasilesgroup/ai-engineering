# Plan: spec-117-hx-10 Runtime Core Extraction - Track C

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-10` changes CLI and installed asset boundaries inside one framework runtime. It should serialize with Tracks A and B unless scopes are proven disjoint, because CLI, template assets, hooks, and services are tightly coupled.

### Phase 1: Inventory And Boundary Freeze
**Gate**: One explicit matrix exists for thin adapter targets, packaged service seams, and runtime-native template assets.
- [x] T-1.1: Consolidate the `HX-10` exploration evidence into one governed adapter and asset/runtime boundary matrix covering large CLI modules, good service seams, and template helper families (agent: build).
- [x] T-1.2: Run a governance review on adapter boundaries and runtime-native asset rules, including the ownership split with `HX-03`, `HX-04`, and `HX-09` before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass requested by the user.
- [x] T-1.3: Define the compatibility boundary for current command modules, template assets, and hook runtime expectations so migration can be compatibility-first (agent: build, blocked by T-1.2).

### Phase 2: CLI Adapter Contract
**Gate**: One thin-adapter contract exists for oversized command modules.
- [x] T-2.1: Write failing tests for parse/confirm/render-only CLI behavior and packaged-service orchestration responsibility in the target command slices (agent: build, blocked by T-1.3).
- [x] T-2.2: Extract packaged services and thin the highest-value CLI modules without changing public command contracts (agent: build, blocked by T-2.1).
- [x] T-2.3: Preserve existing good service seams and forbid reintroducing broad domain mutation into command modules in the owned slice (agent: build, blocked by T-2.2).

### Phase 3: Asset/Runtime Classification And Reduction
**Gate**: Template assets are classified as runtime-native or duplicated-packaged logic, and only safe duplication is reduced.
- [x] T-3.1: Write failing tests or invariant coverage for runtime-native asset classification, duplicated helper identification, and provenance expectations (agent: build, blocked by T-2.3).
- [x] T-3.2: Reduce duplicated packaged logic in template assets where execution constraints allow it, while preserving stdlib-only runtime assets (agent: build, blocked by T-3.1).
- [x] T-3.3: Keep hook manager and install deployment seams stable while the asset/runtime split tightens (agent: build, blocked by T-3.2).

### Phase 4: Adapter And Asset Parity Proof
**Gate**: Thin CLI modules and classified template assets preserve behavior and ownership boundaries.
- [x] T-4.1: Add validation or compatibility checks for forbidden broad command-module mutation and for runtime-native asset misclassification (agent: build, blocked by T-3.3).
- [x] T-4.2: Tighten service-layer boundaries and packaged-versus-runtime provenance in the owned slices (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for command parity, template runtime parity, and boundary preservation before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Runtime Ownership
**Gate**: Track C boundaries are proven, and deferred mirror/kernel/reconciler work remains explicit.
- [x] T-5.1: Flip strict consumers and tests to the normalized adapter and asset/runtime boundaries once compatibility shims are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-03`, `HX-04`, and `HX-09`, especially remaining mirror-governance, kernel-semantics, and reconciler concerns outside Track C (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- Track C serializes with Tracks A and B unless scopes are proven disjoint.
- CLI thinning lands before broad asset/runtime reduction.
- Runtime-native template assets remain standalone where required.
- Mirror, kernel, and reconciler ownership boundaries remain consumed rather than reopened.

## Exit Conditions

- Oversized command modules have thin-adapter boundaries.
- Packaged services own orchestration and mutation in the owned slices.
- Template assets are explicitly classified as runtime-native or reduced duplicates.
- Public command behavior and standalone hook execution guarantees remain intact.