# Plan: spec-117-hx-05 State Plane and Observability Normalization

## Pipeline: full
## Phases: 5
## Tasks: 15 (build: 11, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-05` changes one repository-wide state and observability layer spanning durable ledgers, derived state projections, residue paths, event emitters, task traces, and reporting surfaces. It remains a modular-monolith change because the authority still belongs to one framework runtime and one governed repo, but it must serialize with audit-chain writers and stay tightly bounded against kernel, work-plane, and learning-funnel ownership.

### Phase 1: Inventory And Ownership Boundary
**Gate**: One explicit inventory exists for durable truth, derived projections, residue, and spec-local evidence, and the ownership boundary with `HX-02`, `HX-04`, `HX-06`, and `HX-07` is fixed before state moves begin.
- [x] T-1.1: Consolidate the `HX-05` exploration evidence into one governed inventory of global durable state, residue, spec-local evidence, event emitters, and report surfaces (agent: build).
- [x] T-1.2: Run a governance review on durable-versus-derived-versus-residue classification, serialized families, and deferred ownership before implementation begins (agent: guard, blocked by T-1.1) -- PASS-WITH-NOTES
- [x] T-1.3: Define the compatibility boundary for quasi-authoritative current files, event-writer paths, and downstream report consumers so migration can be compatibility-first (agent: build, blocked by T-1.2).

### Phase 2: Durable State And Residue Split
**Gate**: Global durable truth, residue, and spec-local evidence have explicit homes and classification rules.
- [x] T-2.1: Write failing tests or invariant coverage for global durable-state membership, residue membership, and spec-local evidence relocation rules (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the durable-state versus residue layout and reclassify existing ambiguous files without yet widening report ownership (agent: build, blocked by T-2.1).
- [x] T-2.3: Move spec-local audit or classification artifacts out of global state and under the owning work plane with the required compatibility shims (agent: build, blocked by T-2.2).

### Phase 3: Canonical Event Contract And Task Traces
**Gate**: One canonical event vocabulary exists, and task traces are emitted as append-only audit views over authoritative mutations.
- [x] T-3.1: Write failing tests for canonical provider IDs, event kinds, root event fields, task trace fields, and writer-path parity across runtime and hook emitters (agent: build, blocked by T-2.3).
- [x] T-3.2: Implement the canonical event contract and adapter all supported writers through it without creating a second audit log or chain field (agent: build, blocked by T-3.1).
- [x] T-3.3: Add task trace emission tied to authoritative work-plane and kernel outcomes, not to derived reports or chat heuristics (agent: build, blocked by T-3.2).
- [x] T-3.4: Run a governance review on task traces, audit-chain integrity, and derived-versus-authoritative semantics before scorecard work begins (agent: guard, blocked by T-3.3) -- PASS-WITH-NOTES.

### Phase 4: Scorecards, Reports, And Sequencing Safety
**Gate**: Scorecards are derived views over authoritative inputs, and shared event/output families run with explicit safe sequencing.
- [x] T-4.1: Add scorecard and report reducers for task resolution, retry, rework, verification tax, drift, and related views without letting them become peer authorities (agent: build, blocked by T-3.4).
- [x] T-4.2: Encode safe sequencing for event-emitting validations, audit writers, and downstream report generation so hash-chain and derived-view integrity are preserved (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for state classification, event normalization, task trace emission, and scorecard derivation before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Ownership
**Gate**: State-plane normalization is proven end to end, and deferred capability, context, and eval ownership remains explicit.
- [x] T-5.1: Flip strict runtime and validation consumers to the normalized state-plane contract once compatibility shims and derived-view proofs are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-06`, `HX-07`, and `HX-11`, especially capability projection cleanup, learning-funnel ownership, and deeper eval/report taxonomy (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- Event-emitting validations remain sequential.
- Audit-chain writers stay single-writer or explicitly serialized.
- Task trace emission follows authoritative mutation; scorecards run after trace append.
- Residue GC cannot delete anything still needed for audit or derived reporting.
- `HX-05` consumes `HX-04` kernel outputs and `HX-02` work-plane state rather than redefining them.

## Exit Conditions

- Global durable state contains only cross-spec authoritative records.
- Residue and spec-local evidence have distinct homes and rules.
- Provider IDs and event kinds normalize through one state-layer contract.
- Task traces exist as first-class append-only audit views.
- Scorecards and reports are clearly derived, with provenance and regeneration rules.
- Shared event/output families have explicit safe sequencing behavior.