---
spec: spec-117-hx-07
title: Context Packs and Learning Funnel
status: done
effort: large
---

# Spec 117 HX-07 - Context Packs and Learning Funnel

## Summary

ai-engineering currently carries working, episodic, semantic, and procedural memory across many surfaces, but it does not yet have one deterministic task-context pack or one governed lifecycle for learning artifacts. Shared buffers, event logs, lessons, instincts, proposals, notes, and run-oriented manifests all influence context selection by convention. This feature adds deterministic context packs derived from the work plane, defines a reference-first handoff and compaction contract, and governs the learning funnel so lessons, instincts, proposals, and notes remain advisory or promotable artifacts rather than runtime truth.

## Goals

- Generate deterministic context packs from authoritative control-plane and work-plane inputs.
- Define a pack-manifest contract with explicit source classification and regeneration rules.
- Make handoffs compact, reference-first, and sufficient for resume-from-disk execution.
- Govern the learning funnel so notes, lessons, instincts, and proposals have explicit lifecycle and promotion boundaries.
- Keep context selection token-efficient without making chat memory or prior packs authoritative.
- Preserve clear ownership boundaries with the work plane, state plane, and capability layer.

## Non-Goals

- Replacing the `HX-02` work plane as the authority for task identity, lifecycle state, or evidence.
- Replacing the `HX-05` state plane as the authority for events or task traces.
- Replacing the `HX-06` capability contract as the authority for tool scope, write scope, or topology.
- Building the broader eval or measurement architecture from `HX-11`.
- Using lessons, instincts, or notes as a backdoor policy engine.

## Decisions

### D-117-48: Context packs are deterministic projections from authoritative inputs

`HX-07` generates context packs from authoritative work-plane and control-plane inputs. Packs may include derived explanatory context, but they cannot depend on chat memory, residue, or prior packs for correctness.

**Rationale**: reproducible resume requires one projection rule, not conversational reconstruction.

### D-117-49: Every pack input is classified by source role and authority

Pack inputs must be classified as authoritative, derived, optional advisory, or excluded residue, with explicit source plane, owner, and inclusion reason.

**Rationale**: token efficiency and correctness both depend on knowing what is truth, what is helpful context, and what should be excluded.

### D-117-50: Handoff sufficiency is reference-first and resumable from disk alone

Persisted handoffs must include minimum sufficiency fields and use artifact references instead of large inline logs or duplicated task state.

**Rationale**: handoffs are useful only if a later agent can resume from files alone without reloading the whole repo or trusting chat memory.

### D-117-51: Learning artifacts remain a funnel, not a peer runtime authority

Lessons, instincts, proposals, and notes remain advisory or promotable. Promotion into canonical homes is one-way and leaves provenance or backlinks behind, but not active duplicated authority.

**Rationale**: the repo already has knowledge-placement rules; `HX-07` must operationalize them instead of letting the funnel become a soft second source of truth.

### D-117-52: Pack and learning artifacts live under the owning work plane or canonical home, not global durable state

Persisted packs, handoff compacts, and learning-funnel artifacts stay out of the global durable state root unless they are promoted into an already canonical surface.

**Rationale**: otherwise context artifacts would recreate the mixed-lifecycle state problem that `HX-05` is fixing.

## Authority Matrix

| Surface | Role | Source plane | Runtime authority |
| --- | --- | --- | --- |
| `CONSTITUTION.md`, `.ai-engineering/manifest.yml`, `.ai-engineering/state/decision-store.json` | bootstrap input | control plane | authoritative |
| `.ai-engineering/specs/spec.md`, `.ai-engineering/specs/plan.md`, `.ai-engineering/specs/task-ledger.json`, summaries, handoff/evidence refs | task input | work plane | authoritative |
| `.ai-engineering/state/framework-capabilities.json` | capability projection | capability plane | derived |
| `.ai-engineering/LESSONS.md`, `.ai-engineering/instincts/instincts.yml`, `.ai-engineering/instincts/proposals.md` | learning context | learning funnel | optional advisory |
| `.ai-engineering/state/framework-events.ndjson`, instinct observations, strategic compacts, prior packs, chat transcript residue | runtime residue | runtime residue | excluded residue |

## Implementation Cutover Status

- `ContextPackManifest` now records `sources`, `ceilings`, and `regenerationInputs`; every source carries role, plane, owner, inclusion reason, and inline character count.
- `build_context_pack()` deterministically projects pack manifests from active work-plane/control-plane inputs and writes them under `.ai-engineering/specs/context-packs/`.
- `manifest-coherence` validates generated pack manifests for active task packets via `context-pack-manifest-contract` and fails drifted packs.
- `HandoffCompact` plus `validate_handoff_compact()` enforces reference-first resume fields without duplicating task lifecycle state.
- `LearningFunnelArtifact`, `classify_learning_artifact()`, `promote_learning_artifact()`, and `evaluate_learning_artifact()` keep notes, lessons, instincts, and proposals advisory until promotion names a canonical destination and backlink/provenance path.
- The committed proof pack is `.ai-engineering/specs/context-packs/HX-07-context-pack-learning-funnel.json`.

## Compatibility Boundary

- Shared `spec.md` and `plan.md` buffers remain compatibility views owned by `HX-02`; packs read them as work-plane inputs and do not replace task-ledger authority.
- State/event traces remain owned by `HX-05`; packs can reference residue as excluded context but do not replay or summarize trace truth.
- Capability contracts remain owned by `HX-06`; packs consume `framework-capabilities.json` as a derived projection only.
- Strategic compacts and chat-history residue can inform humans, but they are excluded from deterministic context-pack authority.
- Learning-funnel promotion is explicit and one-way into canonical homes; advisory artifacts are not a policy backdoor.

## Deferred Boundaries

- `HX-05` still owns event append fallback, trace-slice consumption detail, and any state-plane lifecycle changes.
- `HX-11` still owns deeper evaluation, measurement, reporting taxonomy, and hard token-budget scoring.
- This slice enforces structural source count and inline-size ceilings, but does not attempt semantic token prediction.
- Final guard/review remains deferred to the end-of-implementation review pass requested by the user.

## Risks

- **Stale-pack risk**: persisted packs can become peer authorities if regeneration paths are weak. **Mitigation**: make packs explicitly derived and reproducible from authoritative inputs.
- **Promotion drift**: notes and lessons can quietly become runtime guidance. **Mitigation**: require explicit promotion hooks and canonical destinations.
- **Duplication risk**: packs can restate task state or traces and create split authority. **Mitigation**: keep work-plane truth and trace truth external and reference-first.
- **Token-folklore risk**: token-efficiency remains subjective if structure is not enforced. **Mitigation**: validate pack size, source count, and compaction rules structurally.

## References

- doc: .ai-engineering/specs/spec-117-hx-07-context-packs-and-learning-funnel-explore.md
- doc: .ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md
- doc: .ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md
- doc: .ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .ai-engineering/contexts/knowledge-placement.md
- doc: .ai-engineering/LESSONS.md
- doc: .ai-engineering/instincts/instincts.yml
- doc: .github/skills/ai-instinct/SKILL.md
- doc: .github/skills/ai-learn/SKILL.md
- doc: .github/skills/ai-note/SKILL.md

## Open Questions

- Resolved in this slice: pack manifests live under `.ai-engineering/specs/context-packs/` and are generated from control-plane and work-plane references.
- Resolved in this slice: trace and runtime residue are referenced only as `excluded-residue`; they are not inlined as pack authority.
- Deferred to `HX-11`: semantic token-budget scoring beyond structural source-count and inline-size ceilings.
- Deferred to `HX-05`: compensating paths for trace append failures.
- Resolved in this slice: notes, lessons, instincts, and proposals can promote only through explicit canonical-destination metadata and provenance/backlink retention.