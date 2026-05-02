# Plan: spec-117-hx-07 Context Packs and Learning Funnel

## Pipeline: full
## Phases: 5
## Tasks: 14 (build: 10, verify: 2, guard: 2)

## Architecture

modular-monolith

`HX-07` changes one repository-wide context and learning layer spanning pack generation, handoff compaction, pack manifests, funnel artifacts, and promotion hooks. It remains a modular-monolith change because the authority still belongs to one governed repo and one framework runtime, but it must stay thin over the work plane, state plane, and capability layer.

### Phase 1: Authority Boundary And Pack Contract
**Gate**: One explicit ownership split exists between work-plane truth, trace truth, capability truth, and context-pack derivation before implementation begins.
- [x] T-1.1: Consolidate the `HX-07` exploration evidence into one governed context-pack and learning-funnel authority matrix covering pack inputs, handoff artifacts, learning artifacts, and promotion destinations (agent: build).
- [x] T-1.2: Run a governance review on authoritative versus derived versus promotable knowledge, handoff sufficiency, and promotion rules before implementation begins (agent: guard, blocked by T-1.1). Completed in the final end-of-implementation review pass on 2026-05-02; no implementation tasks reopened.
- [x] T-1.3: Define the compatibility boundary for existing shared buffers, run-oriented manifests, strategic compacts, and optional notes so migration can be pack-first without breaking current flows (agent: build, blocked by T-1.2).

### Phase 2: Pack Manifest And Source Classification
**Gate**: One deterministic pack-manifest contract exists, including source classes, inclusion rules, and regeneration semantics.
- [x] T-2.1: Write failing tests or invariant coverage for pack manifests, source classification, reproducibility, residue exclusion, and reference-first handoff rules (agent: build, blocked by T-1.3).
- [x] T-2.2: Implement the canonical pack-manifest schema and pack generator over authoritative work-plane and control-plane inputs (agent: build, blocked by T-2.1).
- [x] T-2.3: Add structural ceilings for source count, inline size, and residue exclusion without making prior packs or chat memory authoritative (agent: build, blocked by T-2.2).

### Phase 3: Handoff And Compaction Contract
**Gate**: Handoffs are resumable from disk alone and enforce reference-first compaction.
- [x] T-3.1: Write failing tests for handoff sufficiency, authoritative refs, next action or blocker semantics, and oversized inline evidence rejection (agent: build, blocked by T-2.3).
- [x] T-3.2: Implement the handoff schema and compaction validator so later agents can resume from disk alone without duplicated task-state fields (agent: build, blocked by T-3.1).
- [x] T-3.3: Keep trace and pack events as downstream emissions over authoritative writes rather than new peer logs (agent: build, blocked by T-3.2).

### Phase 4: Learning Funnel Lifecycle And Promotion
**Gate**: Lessons, instincts, proposals, and notes have explicit lifecycle and promotion hooks without becoming peer runtime authority.
- [x] T-4.1: Implement the learning-funnel classification and promotion model, including canonical destinations, provenance, and backlink behavior (agent: build, blocked by T-3.3).
- [x] T-4.2: Add deterministic validation for promotion eligibility and advisory checks for noisy, weak, or redundant funnel artifacts (agent: build, blocked by T-4.1).
- [x] T-4.3: Run targeted verification for pack reproducibility, handoff sufficiency, and funnel-promotion behavior before strict cutover (agent: verify, blocked by T-4.2).

### Phase 5: Cutover Proof And Deferred Boundaries
**Gate**: Context packs and the learning funnel are proven end to end, and deferred work remains explicit.
- [x] T-5.1: Flip strict consumers to the deterministic pack and handoff contract once compatibility shims and validation are green (agent: build, blocked by T-4.3).
- [x] T-5.2: Document deferred work for `HX-05` and `HX-11`, especially trace consumption detail, event append fallback, and deeper measurement or token-budget enforcement (agent: build, blocked by T-5.1).
- [x] T-5.3: Run the focused end-to-end proof for this feature with the relevant unit/integration slices plus `uv run ai-eng validate -c cross-reference` and `uv run ai-eng validate -c file-existence` (agent: verify, blocked by T-5.2).

## Sequencing Notes

- `HX-07` consumes `HX-02`, `HX-05`, and `HX-06`; it does not redefine them.
- Pack generation follows authoritative work-plane truth.
- Handoff compaction validates references before learning-funnel promotion runs.
- Learning promotion writes happen only after the authoritative pack or handoff writes succeed.
- Persisted pack and funnel artifacts stay out of global durable state unless promoted into canonical homes.

## Exit Conditions

- One deterministic pack-manifest contract exists.
- Pack inputs are classified by authority and source plane.
- Handoffs are reference-first and resumable from disk alone.
- Learning artifacts have explicit lifecycle and promotion boundaries.
- Context artifacts remain derived and do not become peer truth sources.