# HX-08 Explore - Runtime Core Extraction Track A

This artifact captures the evidence gathered before writing the feature spec for `HX-08`.

## Scope

Feature: `HX-08` Runtime Core Extraction - Track A.

Question: what must change so manifest and durable-state access converge on repository and projection boundaries instead of duplicated loaders, private helper leakage, and direct file probing across the repo?

## Evidence Summary

### Typed Manifest Authority Already Exists, But It Is Not The Only Reader

- `config/loader.py` is the strongest typed manifest load and write authority and preserves comments.
- Projection APIs already exist in `state/manifest.py` for specific read use cases.
- Other consumers still read manifest data through raw or partial code paths for prereqs, validators, and governance checks.

The repo therefore already has a good seed seam, but not one shared repository boundary.

### Durable State Access Is Split Across Façades, Direct File Reads, And Cross-Package Leakage

- Install-state logic, event append, and partial state access are already structured in parts of `state/service.py` and `state/observability.py`.
- Many modules still probe state paths or parse state files directly.
- Some state-layer code reaches back into config loader, and some installer code reaches into private state projection helpers.

The result is broad file access instead of explicit repository contracts.

### The Best Existing Seams Should Survive

- Manifest write authority in `config/loader.py` is a real behavioral contract.
- Projection-style APIs in `state/manifest.py` are useful read seams if they stop owning their own loading rules.
- Install-state migration behavior in `state/service.py` is valuable and should not be flattened into generic JSON helpers.
- Event append and audit-chain behavior should stay stable and outside Track A ownership changes.

### `HX-08` Must Not Re-Own Kernel Or State Vocabulary Work

- `HX-04` already owns local execution truth.
- `HX-05` already owns state-plane vocabulary, traces, and residue split.
- Track A should focus on repository and projection boundaries, not on redesigning event schema, trace semantics, or kernel logic.

## High-Signal Findings

1. The highest-value Track A boundary is one durable-artifact access layer with separate read projections.
2. Typed load, raw snapshot, and field patch need to coexist because not every consumer can or should require full strict manifest validation.
3. Broad file access and private helper leakage are the real runtime debt, not package naming alone.
4. Install-state migration behavior and event append semantics are stable seams worth preserving.

## Recommended Decision Direction

### Preferred Repository Direction

- Add a public manifest repository that owns typed load, raw snapshot, and field patch for `manifest.yml`.
- Add a public durable-state repository that owns install-state, decision store, ownership map, framework capabilities, and event-stream path or append access.
- Move consumers above those repositories onto typed snapshots or projection APIs instead of direct file access.

### Preferred Projection Direction

- Keep projection-style helpers as downstream read models.
- Stop duplicating YAML/JSON loader logic across validators, prereq probes, and command flows.
- Preserve comment-preserving writes and compatibility reads as first-class repository capabilities.

## Migration Hazards

- Forcing every consumer onto one strict typed manifest loader would break legitimate partial or raw readers.
- Replacing install-state logic with generic helpers would lose compatibility and migration semantics.
- Touching event append/storage semantics here would duplicate `HX-05`.
- Broad call-site rewrites have high blast radius because many modules currently do path-based checks or raw reads.

## Scope Boundaries For HX-08

In scope:

- manifest repository boundary
- durable-state repository boundary
- projection and snapshot APIs
- removal of direct file-access leakage from upper layers

Out of scope:

- event vocabulary or task traces from `HX-05`
- kernel execution authority from `HX-04`
- reconciler convergence from `HX-09`
- CLI adapter thinning from `HX-10`

## Open Questions

- Which raw or partial readers deserve permanent repository support versus eventual migration to typed snapshots?
- Should event append live in the same durable-state repository or as a narrower dedicated writer service?
- How much path-helper cleanup belongs in this track versus in later CLI/runtime cleanup?

## Source Artifacts Consulted

- `src/ai_engineering/config/loader.py`
- `src/ai_engineering/state/manifest.py`
- `src/ai_engineering/state/service.py`
- `src/ai_engineering/state/observability.py`
- `src/ai_engineering/state/audit_chain.py`
- `src/ai_engineering/prereqs/uv.py`
- `src/ai_engineering/validator/categories/required_tools.py`
- `src/ai_engineering/paths.py`
- `src/ai_engineering/installer/service.py`
- `src/ai_engineering/doctor/phases/state.py`
- `src/ai_engineering/updater/service.py`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md`