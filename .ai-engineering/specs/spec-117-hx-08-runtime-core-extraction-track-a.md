---
spec: spec-117-hx-08
title: Runtime Core Extraction - Track A
status: done
effort: large
---

# Spec 117 HX-08 - Runtime Core Extraction - Track A

## Summary

ai-engineering currently accesses manifest and durable-state artifacts through a mix of typed loaders, raw or partial readers, projection helpers, direct file probing, and private helper leakage across packages. This feature introduces explicit repository boundaries for manifest and durable state, plus downstream projection APIs, so upper layers stop owning file access details. The goal is not to rename packages for style; it is to eliminate duplicated parsing and broad path-coupling while preserving comment-preserving manifest writes, install-state migration behavior, and stable event append seams.

## Goals

- Add one public manifest repository with typed load, raw snapshot, and field patch capabilities.
- Add one public durable-state repository for stable state families and paths.
- Move upper-layer consumers onto repository or projection APIs rather than direct file reads.
- Preserve stable seams such as comment-preserving manifest writes and install-state migration behavior.
- Reduce parser duplication and private helper leakage.

## Non-Goals

- Redesigning event vocabulary or task traces from `HX-05`.
- Redesigning kernel execution or findings semantics from `HX-04`.
- Converging installer, doctor, and updater flows from `HX-09`.
- Thinning CLI adapters or asset/runtime duplication from `HX-10`.

## Decisions

### D-117-58: Track A defines repository boundaries, not cosmetic package merges

The feature adds explicit manifest and durable-state repositories plus downstream read projections. The value is in ownership and access discipline, not in moving code for cosmetic cleanliness.

**Rationale**: the real runtime debt is duplicated parsing and direct file access, not naming alone.

### D-117-59: Manifest repository must support typed and partial read modes

The manifest repository must expose strict typed reads, raw or partial snapshots, and patch/update paths where needed.

**Rationale**: some legitimate consumers cannot require full-manifest validation, but they still need a governed access path.

### D-117-60: Durable-state repository preserves state-family-specific semantics

Install-state migration rules, ownership/projection paths, and event-stream path ownership remain explicit repository behavior rather than collapsing into generic JSON helpers.

**Rationale**: several state families already carry compatibility semantics that upper layers rely on.

### D-117-61: Projection APIs are downstream read models, not peer authorities

Projection-style helpers remain valuable, but they must consume repository inputs rather than own separate parse logic or competing file access rules.

**Rationale**: projections should simplify reads, not recreate authority sprawl.

## Risks

- **Compatibility-reader risk**: strict-only manifest access would break legitimate partial readers. **Mitigation**: support raw/partial repository reads explicitly.
- **Migration-loss risk**: flattening install-state behavior into generic storage would lose compatibility logic. **Mitigation**: keep state-family-specific semantics owned by the repository.
- **Blast-radius risk**: many call sites currently probe paths directly. **Mitigation**: migrate by bounded consumer families with compatibility shims.

## Implementation Notes

- Added `src/ai_engineering/state/repository.py` as the public repository boundary for manifest and durable-state artifacts.
- `ManifestRepository` exposes typed load, raw snapshot, dotted partial read, and comment-preserving field patch operations.
- `DurableStateRepository` exposes stable paths and load/save operations for install state, decision store, ownership map, framework capabilities, and framework events.
- `state/manifest.py` now consumes repository-backed raw manifest snapshots for downstream projection loaders.
- `StateService` remains a compatibility facade while delegating stable state-family reads and writes through the durable-state repository.
- Event append behavior remains delegated to `state.observability` so Track A does not re-own event vocabulary or audit-chain semantics.

## References

- doc: .ai-engineering/specs/spec-117-hx-08-runtime-core-extraction-track-a-explore.md
- doc: .ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md
- doc: .ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md
- doc: src/ai_engineering/config/loader.py
- doc: src/ai_engineering/state/manifest.py
- doc: src/ai_engineering/state/service.py
- doc: src/ai_engineering/state/observability.py

## Open Questions

- Raw snapshots and dotted partial reads are now permanent manifest repository APIs for compatibility readers.
- Event append remains behind the existing observability writer; the durable-state repository only exposes the stable path and a delegating compatibility method.
- Broader installer, doctor, updater, CLI adapter, and asset-runtime cleanup is deferred to `HX-09` and `HX-10`.