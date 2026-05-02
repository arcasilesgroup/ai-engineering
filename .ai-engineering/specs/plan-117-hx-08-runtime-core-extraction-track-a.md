# Plan: spec-117-hx-08 Runtime Core Extraction - Track A

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-08` changes repository-facing runtime access inside one framework runtime. It should serialize with adjacent runtime tracks because config, state, and their consumers are highly coupled.

### Phase 1: Inventory And Boundary Freeze
**Gate**: One authority matrix exists for manifest access, durable-state access, projections, and direct file leakage.
- [x] T-1.1: Consolidate the `HX-08` exploration evidence into one governed repository-boundary matrix covering manifest reads, state-family reads, projections, and leaking consumers (agent: build).
- [x] T-1.2: Run a governance review on typed-versus-partial reads, compatibility semantics, and ownership boundaries with `HX-04`, `HX-05`, and `HX-09` before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass on 2026-05-02; no implementation tasks reopened.
- [x] T-1.3: Define the compatibility boundary for existing raw readers, path probes, and private-helper consumers so migration can be compatibility-first (agent: build, blocked by T-1.2).

### Phase 2: Manifest Repository Contract
**Gate**: One public manifest repository exists with typed load, raw snapshot, and patch semantics.
- [x] T-2.1: Write failing tests for typed manifest reads, raw or partial snapshots, patch behavior, and projection consumers (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the public manifest repository while preserving comment-aware write behavior (agent: build, blocked by T-2.1).
- [x] T-2.3: Move projection consumers off duplicated parse logic and onto repository-backed inputs (agent: build, blocked by T-2.2).

### Phase 3: Durable-State Repository Contract
**Gate**: One public durable-state repository exists for stable state families and paths.
- [x] T-3.1: Write failing tests for install-state, decision-store, ownership-map, framework-capabilities, and event-path access through one repository boundary (agent: build, blocked by T-2.3).
- [x] T-3.2: Implement the durable-state repository while preserving install-state migration behavior and stable path ownership (agent: build, blocked by T-3.1).
- [x] T-3.3: Keep event append semantics and broader state taxonomy outside Track A ownership while aligning path access to the new boundary (agent: build, blocked by T-3.2).

### Phase 4: Consumer Cutover And Leakage Removal
**Gate**: Upper-layer consumers no longer own file-access details.
- [x] T-4.1: Migrate bounded consumer families off direct file probing and private helper leakage onto repository or projection APIs (agent: build, blocked by T-3.3).
- [x] T-4.2: Add validation or compatibility checks for forbidden direct access patterns in the owned runtime slice (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for repository behavior, compatibility readers, and migrated call paths before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Runtime Work
**Gate**: Repository boundaries are proven and deferred runtime work remains explicit.
- [x] T-5.1: Flip strict runtime consumers to repository-backed access once compatibility shims and projections are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-09` and `HX-10`, especially reconciler convergence and CLI/asset-runtime cleanup (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- Track A serializes with Tracks B and C unless scopes are proven disjoint.
- Manifest repository lands before projection cutover.
- Durable-state repository preserves family-specific semantics.
- Event schema and residue taxonomy remain outside Track A ownership.

## Exit Conditions

- One public manifest repository exists.
- One public durable-state repository exists.
- Projection APIs consume repository inputs.
- Upper layers stop owning broad file-access details.