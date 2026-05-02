# Plan: spec-117-hx-03 Mirror Local Reference Model

## Pipeline: full
## Phases: 5
## Tasks: 15 (build: 11, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-03` changes one repository-wide mirror system spanning generator code, canonical skills and agents, provider-local mirrors, template projections, validators, installer logic, CI checks, and generated overlays. It remains a modular-monolith change because the behavior still belongs to one framework runtime and one governed repository, but it requires careful sequencing so generator truth, validation truth, and public contract stay aligned.

**Reconciliation Note:** `HX-03` ran to `T-5.3` in the governed work plane. The initial mirror inventory and public-boundary work was absorbed into the early reference-model slice, and the later provider-local rewrite plus validator-parity slices were recorded in the task-ledger even though this checklist was not updated. The items below are now reconciled to match that execution record.

### Phase 1: Artifact Inventory And Public Boundary
**Gate**: One explicit mirror-family inventory exists, and the public versus internal surface boundary is governed before generator rewrites begin.
- [x] T-1.1: Consolidate the `HX-03` exploration evidence into one governed inventory of mirror families, provider-local root files, transform modes, and known compatibility exceptions (agent: build).
- [x] T-1.2: Run a governance review on the public/internal boundary, provider compatibility rules, and filtered public-count model before implementation begins (agent: guard, blocked by T-1.1).
- [x] T-1.3: Define the compatibility boundary for generated public mirrors, internal specialist assets, manual instruction files, and template/install projections so migration can be compatibility-first (agent: build, blocked by T-1.2).

### Phase 2: Provenance Contract And Reference Model
**Gate**: One executable mirror reference model exists with provenance, enablement predicates, and edit policy strong enough for generator, validator, installer, and test consumers.
- [x] T-2.1: Write failing tests or invariant coverage for the mirror-family inventory, provider compatibility predicates, provenance markers, and public/internal filtering contract (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the shared mirror reference model so generator code, template destinations, validator inventories, and CI-facing path logic stop using divergent hard-coded maps (agent: build, blocked by T-2.1).
- [x] T-2.3: Add explicit generated/manual provenance and non-editability markers for mirrored public outputs while preserving clearly classified manual families (agent: build, blocked by T-2.2).
- [x] T-2.4: Run a governance review on provenance semantics, filtered public counts, and internal specialist treatment before content rewrites begin (agent: guard, blocked by T-2.3).

### Phase 3: Provider-Local Rewrite And Surface Filtering
**Gate**: Public mirrored outputs are self-contained for their target provider and internal specialist surfaces are no longer treated as peer public contract.
- [x] T-3.1: Write failing tests for non-Claude local-reference leaks, Claude-only operational assumptions, provider-incompatible public files, and public-count drift from internal specialist surfaces (agent: build, blocked by T-2.4).
- [x] T-3.2: Update generator transforms, compatibility filters, and mirrored content rewrites so non-Claude mirrors no longer depend on `.claude`-specific references or Claude-only execution assumptions (agent: build, blocked by T-3.1).
- [x] T-3.3: Filter or relocate internal review and verify specialist assets so they remain orchestrator-facing internals rather than mirrored peer public entry points (agent: build, blocked by T-3.2).
- [x] T-3.4: Render root overlays and provider-facing catalogs from the filtered mirror contract so counts, anchors, and grouped views stay contract-driven (agent: build, blocked by T-3.3).

### Phase 4: Validator, Installer, And Template Parity
**Gate**: Sync generation, validation, install/template projection, and CI all consume the same mirror truth and reject invalid provider-local outputs.
- [x] T-4.1: Update installer/template logic, mirror validators, shared validator path inventories, and CI enforcement to use the shared mirror reference model (agent: build, blocked by T-3.4).
- [x] T-4.2: Add negative validation for stray `.claude` leaks, incompatible public surfaces, missing provenance markers, and orphaned or ungoverned mirror families (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification with `uv run ai-eng sync --check` plus the relevant mirror and content-integrity slices, ensuring sync completes before mirror validation (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Cleanup Envelope
**Gate**: The mirror contract is proven end to end, and any remaining deferred cleanup stays explicit instead of hidden in generated surfaces.
- [x] T-5.1: Flip strict tests and generated overlays to the normalized mirror contract once provider-local outputs, provenance markers, and filtered public counts are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred cleanup and follow-on work for `HX-04`, `HX-06`, or `HX-12`, especially any intentionally retained manual surfaces or unresolved root-overlay governance edges (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng sync --check`, `uv run ai-eng validate -c cross-reference`, and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- The mirror-family inventory and public/internal boundary must settle before generator rewrites start.
- Shared mirror reference data must exist before validator or installer parity can be trusted.
- Sync generation completes before mirror validation or content-integrity checks when canonical mirror sources change.
- Public counts must derive from the filtered registry rather than raw file counts.
- Live repo and install-template mirror logic move together.

## Exit Conditions

- One governed artifact inventory exists for the mirror families in scope.
- Non-Claude mirrored public surfaces are provider-local and free of `.claude` leaks.
- Provider compatibility and provider-local enrichments are explicit contract rules.
- Public mirrored surface is filtered from the first-class registry and no longer conflates internal specialist assets.
- Generated provenance and edit policy are explicit and consistent for mirrored public outputs.
- `sync`, validators, installer/template logic, and tests share the same mirror reference model.