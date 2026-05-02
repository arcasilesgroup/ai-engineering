# Plan: spec-117-hx-01 Control Plane Normalization

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-01` changes governance and control-plane contracts inside one repository and one installed-workspace model. It does not introduce new deployables; it normalizes authority and enforcement across manifest/config, validator categories, sync generation, updater protection, doctor phases, observability, and template workspaces. That is a modular-monolith change with strong internal seams and compatibility requirements.

**Reconciliation Note:** `HX-01` ran to `T-5.3` in the governed work plane and has a recorded focused proof. The previously unchecked guard checkpoints (`T-1.2` and `T-2.3`) were not preserved as standalone progress packets, so this plan now marks them closed retroactively to match the task-ledger execution record and final proof.

### Phase 1: Authority Inventory And Compatibility Boundary
**Gate**: The feature has one explicit inventory of constitutional, canonical, generated, and descriptive control-plane surfaces, plus a compatibility boundary for anything that may be renamed or demoted.
- [x] T-1.1: Consolidate the `HX-01` exploration evidence into one governed feature artifact and confirm the exact list of constitutional, canonical, generated, and descriptive surfaces (agent: build).
- [x] T-1.2: Run a governance review on constitutional authority, workspace-charter role, and source-repo vs template-workspace implications before implementation begins (agent: guard, blocked by T-1.1).
- [x] T-1.3: Define the compatibility boundary for constitution paths, ownership/provenance field names, and root-entry-point anchors that must support dual-read migration (agent: build, blocked by T-1.2).

### Phase 2: Canonical Authority Contract
**Gate**: One explicit control-plane authority contract exists, including constitutional winner, per-field manifest authority, and canonical-vs-generated classification.
- [x] T-2.1: Write failing tests or invariant coverage for the normalized constitutional authority and control-plane authority table, including live/template parity where applicable (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the constitutional demotion/rename strategy and the per-field authority model in the live repo and template workspace artifacts (agent: build, blocked by T-2.1).
- [x] T-2.3: Run a governance review on the resulting authority model, especially canonical-vs-generated semantics and workspace-charter boundaries (agent: guard, blocked by T-2.2).

### Phase 3: Shared Ownership And Provenance Resolver
**Gate**: Validator, updater, doctor, sync, observability, and tests consume one shared ownership/provenance contract instead of duplicated assumptions.
- [x] T-3.1: Write failing tests for a shared ownership/provenance resolver covering root entry points, control-plane paths, and compatibility aliases (agent: build, blocked by T-2.3).
- [x] T-3.2: Implement the shared resolver and migrate updater/doctor/state enforcement to it before tightening validators (agent: build, blocked by T-3.1).
- [x] T-3.3: Update generated ownership/capability projections so they are clearly downstream outputs of the normalized contract rather than peer authorities (agent: build, blocked by T-3.2).

### Phase 4: Validator And Runtime Hardening
**Gate**: Control-plane invariants are checked explicitly and the runtime tolerates the transition safely.
- [x] T-4.1: Strengthen `manifest_coherence`, `mirror_sync`, file-existence, and cross-reference coverage for the normalized control-plane contract and paths (agent: build, blocked by T-3.3).
- [x] T-4.2: Update runtime consumers in sync, observability, audit, and any control-plane readers to use the shared compatibility resolver (agent: build, blocked by T-3.2).
- [x] T-4.3: Add targeted verification for the normalized control plane, including template parity, projection regeneration, and compatibility-path behavior (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Cleanup Envelope
**Gate**: The normalized control plane is proven by focused validation, and any remaining aliases or legacy names are explicitly documented for later removal.
- [x] T-5.1: Flip strict tests and validators to the normalized contract once compatibility support is in place and green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document any remaining compatibility aliases, deferred cleanup, and follow-on work for `HX-03`, `HX-05`, or `HX-06` rather than widening `HX-01` (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with relevant unit/integration tests plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).
	- Status: `DONE`. The focused proof bundle passed with `402 passed` across install-clean, manifest, state, updater, doctor-phase-state, validator, framework-context, observability, and template-parity coverage; `file-existence`, `cross-reference`, and `manifest-coherence` also passed in the real repository.

## Sequencing Notes

- Live and template manifest/control-plane changes must land together.
- Ownership enforcement must migrate before schema tightening.
- Compatibility aliases must exist before any destructive rename, demotion, or path cutover.
- Projection regeneration must not be treated as proof of authority; proof comes from the shared resolver plus validation.

## Exit Conditions

- One constitutional surface is authoritative.
- The manifest and related control-plane artifacts have explicit canonical vs generated semantics.
- Ownership/provenance enforcement is shared across runtime and validation layers.
- Focused validation proves control-plane references and file existence still hold.
- Deferred cleanup is explicit and routed to later HX features instead of leaking scope into `HX-01`.