# Plan: spec-117-hx-12 Engineering Standards and Legacy Retirement

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-12` is the late-wave closure layer over one framework runtime and one governed repo. It should run after earlier slices are real and validated, and retire legacy surfaces family by family.

### Phase 1: Standards And Retirement Inventory
**Gate**: One explicit matrix exists for canonical standards surfaces, review/verify consumers, and legacy deletion families.
- [x] T-1.1: Consolidate the `HX-12` exploration evidence into one governed matrix covering standards surfaces, missing canon, review/verify gaps, and legacy deletion families (agent: build).
- [x] T-1.2: Run a governance review on standards canon, rubric binding, deletion sequencing, and ownership boundaries with earlier HX slices before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass requested by the user.
- [x] T-1.3: Define the compatibility boundary for current standards docs, missing references, and legacy families so retirement remains parity-first (agent: build, blocked by T-1.2).

### Phase 2: Canonical Standards Binding
**Gate**: Canonical engineering standards exist and are bound to review/verify rubrics.
- [x] T-2.1: Write failing tests or invariant coverage for canonical standards surfaces, Harness Engineering canon, and standards-to-rubric mappings (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the canonical standards surfaces and the standards matrix for Clean Code, Clean Architecture, SOLID, DRY, KISS, YAGNI, TDD, SDD, and Harness Engineering (agent: build, blocked by T-2.1).
- [x] T-2.3: Bind review and verify consumers to the standards matrix without making them re-own earlier runtime contracts (agent: build, blocked by T-2.2).

### Phase 3: Adoption And Migration Guidance
**Gate**: Framework and adoption docs explain the implemented harness model without outrunning runtime truth.
- [x] T-3.1: Write failing coverage or review checks for migration-guide completeness and canonical-reference usage (agent: build, blocked by T-2.3).
- [x] T-3.2: Implement framework-level migration and adoption guides for task ledger, harness check, mirror rules, context packs, and related runtime contracts that are already real (agent: build, blocked by T-3.1).
- [x] T-3.3: Keep README and GETTING_STARTED deferred until runtime commands and artifacts are proven real (agent: build, blocked by T-3.2).

### Phase 4: Legacy Deletion Manifest And Parity Proof
**Gate**: Legacy surface families have replacement owners, parity proofs, and rollback criteria.
- [x] T-4.1: Build the family-by-family deletion manifest with replacement owner, proof requirement, and rollback path (agent: build, blocked by T-3.3).
- [x] T-4.2: Add parity-proof and rollback validation hooks so deletions cannot proceed without explicit evidence (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for standards binding, migration docs, and deletion-manifest semantics before strict closure work begins (agent: verify, blocked by T-4.2).

### Phase 5: Closure Proof And Serialized Retirement Path
**Gate**: The closure layer is proven and future retirements are governed rather than improvised.
- [x] T-5.1: Flip strict consumers to the canonical standards matrix and governed deletion manifest once compatibility proofs are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document the ordered retirement sequence for legacy families and the user-facing rollout plan for adopted runtime features (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration/doc slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- `HX-12` runs after earlier replacement slices are real.
- Legacy families retire one at a time.
- Review and verify consume the standards matrix without re-owning runtime semantics.
- Root docs trail implemented contracts.

## Exit Conditions

- Canonical engineering standards are explicit and reusable.
- Review and verify are bound to the standards matrix.
- Migration and adoption docs exist for implemented runtime features.
- Legacy retirement is governed by manifest, parity proof, and rollback criteria.