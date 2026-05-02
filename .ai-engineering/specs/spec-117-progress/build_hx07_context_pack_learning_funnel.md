# Build: HX-07 Context Packs and Learning Funnel

## Scope

Implemented the first deterministic context-pack and learning-funnel contract for `spec-117-hx-07`.

## Changes

- Added context-pack source-role, source-plane, ceiling, manifest, handoff compact, learning artifact, and advisory-result models in `src/ai_engineering/state/models.py`.
- Added `src/ai_engineering/state/context_packs.py` for deterministic pack generation from control-plane and active work-plane inputs.
- Classified context-pack sources as authoritative, derived, optional advisory, or excluded residue.
- Kept inline pack content at zero by default so persisted packs stay reference-first.
- Added handoff compact validation requiring task identity, objective, authoritative refs, and either next action or blockers.
- Added learning-funnel helpers for classification, canonical promotion, and weak/noisy/redundant advisory checks.
- Wired generated context-pack validation into `manifest-coherence` as `context-pack-manifest-contract`.

## Boundary

Context packs are derived projections. They do not replace the task ledger, decision store, framework-capabilities projection, event stream, or learning artifact canonical homes.
