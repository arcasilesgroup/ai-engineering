# Plan: spec-117-hx-06 Multi-Agent Capability Contracts

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-06` changes one repository-wide orchestration and policy layer spanning manifest metadata, canonical agent and skill contracts, provider-aware metadata generation, task-packet acceptance, validators, and guarded execution flows. It remains a modular-monolith change because there is still one framework runtime and one governed repo, but it needs careful boundaries so it extends the `HX-02` work plane and consumes the `HX-03` mirror model rather than duplicating either.

### Phase 1: Capability Authority And Boundary
**Gate**: One explicit capability authority exists, and the feature boundary between `HX-02`, `HX-03`, and `HX-06` is fixed before new schemas or validators land.
- [x] T-1.1: Consolidate the `HX-06` exploration evidence into one governed capability-authority model covering capability cards, mutation classes, tool scope, provider compatibility, topology role, and task-packet acceptance rules (agent: build).
- [x] T-1.2: Run a governance review on capability authority, deterministic versus advisory checks, and the ownership split with `HX-02` and `HX-03` before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass on 2026-05-02; no implementation tasks reopened.
- [x] T-1.3: Define the compatibility boundary for existing manifest metadata, provider-specific sync enrichments, and shallow capability projections so migration can be compatibility-first (agent: build, blocked by T-1.2).

### Phase 2: Schema, Taxonomy, And Projection Contract
**Gate**: One machine-readable capability schema exists, with write-scope taxonomy, tool-scope policy, topology role, and provider compatibility modeled strongly enough for runtime and validation consumers.
- [x] T-2.1: Write failing tests or invariant coverage for capability cards, task-packet acceptance inputs, write-scope taxonomy, tool-scope policy, topology role, and provider compatibility rules (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the canonical capability-card schema and derived projection model so `framework-capabilities.json` becomes downstream output instead of peer authority (agent: build, blocked by T-2.1).
- [x] T-2.3: Add the write-scope taxonomy and tool-scope policy to the owned metadata surfaces without collapsing work-plane or mirror ownership into the capability layer (agent: build, blocked by T-2.2).
- [x] T-2.4: Run a governance review on topology role, provider degradation semantics, and artifact ownership boundaries before policy enforcement begins (agent: guard, blocked by T-2.3). Completed in the final end-of-implementation review pass on 2026-05-02; no implementation tasks reopened.

### Phase 3: Topology And Acceptance Wiring
**Gate**: Orchestration flows can classify capabilities and validate task-packet acceptance deterministically before work begins.
- [x] T-3.1: Write failing tests for prompt/tool parity, delegation parity, topology role drift, and invalid capability/task matches across public and internal orchestration surfaces (agent: build, blocked by T-2.4).
- [x] T-3.2: Implement topology classification and task-packet acceptance logic so a capability may only accept legal mutation classes, tool requests, write scopes, and provider bindings (agent: build, blocked by T-3.1).
- [x] T-3.3: Preserve internal specialist participation without letting those surfaces become peer public capability outputs or count authorities (agent: build, blocked by T-3.2).

### Phase 4: Integration Gates And Advisory Checks
**Gate**: Invalid capability/task combinations are blocked deterministically, and broader execution risks surface as advisory checks rather than folklore.
- [x] T-4.1: Add integration gates for overlapping serialized writes, missing dependency or handoff edges, illegal tool requests, illegal mutation classes, and provider-incompatible execution (agent: build, blocked by T-3.3).
- [x] T-4.2: Add advisory checks for overly broad legal scopes, semantic coupling risk, degraded host quality, and poor token posture without turning them into false hard failures (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for acceptance logic, integration-gate failures, advisory-check signaling, and compatibility behavior before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred-Policy Envelope
**Gate**: Capability contracts are proven end to end, and any deeper scheduling or kernel work remains explicitly deferred rather than implicitly promised.
- [x] T-5.1: Flip strict policy consumers to capability-card and task-packet authority once compatibility shims and projections are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-04`, `HX-05`, and `HX-07`, especially kernel-wide retry/loop handling, deeper event ownership, worktree isolation, and context-budget enforcement (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- `HX-06` extends `HX-02` task packets and consumes `HX-03` public/internal boundary; it must not redefine either.
- Capability-card schema must exist before topology or policy enforcement can be trusted.
- Provider-specific enrichments need explicit compatibility modeling before generalized capability gating tightens.
- Internal specialist surfaces may remain runtime participants, but they cannot become peer public capability authorities.
- Deterministic gates should remain limited to correctness-critical cases in this slice; broader heuristics stay advisory.
- Guard/review tasks were completed in the final implementation review pass requested by the user; the build foundation is recorded in `spec-117-progress/build_hx06_capability_contract_foundation.md`.
- Internal specialist topology is recorded in `spec-117-progress/build_hx06_internal_topology_parity.md`; public prompt/tool parity coverage is recorded in `spec-117-progress/build_hx06_prompt_tool_parity.md`.
- Focused end-to-end proof is recorded in `spec-117-progress/verify_hx06_focused_end_to_end_proof.md`.

## Exit Conditions

- One machine-readable capability-card contract exists for first-class agents and skills.
- Mutation authority, write-scope taxonomy, tool scope, provider compatibility, and topology role are explicit.
- Task-packet acceptance is validated against capability authority rather than prompt convention.
- Invalid delegate/tool/write combinations are blocked deterministically.
- `framework-capabilities.json` is a projection of the normalized capability contract, not a competing source.
- Deferred kernel, state, and context-budget work is explicit and routed to later HX features.