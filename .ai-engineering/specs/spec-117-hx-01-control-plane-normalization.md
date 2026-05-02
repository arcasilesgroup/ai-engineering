---
spec: spec-117-hx-01
title: Control Plane Normalization
status: done
effort: large
---

# Spec 117 HX-01 - Control Plane Normalization

## Summary

ai-engineering currently has a split control plane. Constitutional authority is divided between root `CONSTITUTION.md` and workspace `.ai-engineering/CONSTITUTION.md`; manifest ownership and provenance semantics are mixed with generated and descriptive data; ownership enforcement is implemented through state defaults and projections rather than one authoritative resolver; and validators, sync logic, updater, doctor, and tests encode overlapping assumptions about root surfaces. This feature normalizes the control plane so the repository has one constitutional authority, one deterministic canonical-vs-generated model, and one compatibility-safe enforcement contract.

## Goals

- Resolve the dual-constitution model so one surface is constitutional and the other, if retained, has a narrower non-constitutional role.
- Define a per-field control-plane authority model for manifest inputs, generated projections, and descriptive docs.
- Create one authoritative ownership/provenance contract that validator, updater, doctor, sync, observability, and tests can share.
- Preserve runtime safety through a compatibility-first migration that supports old and new names or paths during the cutover window.
- Tighten validator and test coverage so control-plane drift is detected deterministically rather than only through indirect failures.
- Keep source-repo and template-workspace behavior aligned by updating live and template control-plane artifacts in lockstep.

## Non-Goals

- Rewriting mirror-local references beyond the minimum provenance changes needed to normalize control-plane authority.
- Implementing work-plane or task-ledger behavior from `HX-02`.
- Performing runtime-core extractions unrelated to shared control-plane resolvers.
- Deleting generated projections or historical artifacts without a replacement contract and compatibility plan.
- Reworking broader documentation or product-positioning surfaces outside the control-plane scope.

## Control-Plane Surface Inventory

### Constitutional Surfaces

- `CONSTITUTION.md`: root constitutional winner targeted by `HX-01`; this is the only surface intended to keep Step 0 authority after normalization.
- `.ai-engineering/CONSTITUTION.md`: active compatibility surface that currently behaves like a peer constitution and therefore must be demoted, renamed, or narrowed during the feature.

### Canonical Runtime Inputs

- `.ai-engineering/manifest.yml`: primary live control-plane input containing operator-authored and framework-managed regions that must be normalized per field.
- `CLAUDE.md`: live root entry point and runtime-consumed workspace overlay that remains non-constitutional but still participates in control-plane authority and compatibility handling.
- `src/ai_engineering/templates/.ai-engineering/manifest.yml`: template workspace counterpart of the manifest that must move in lockstep with the live repo contract.
- `src/ai_engineering/templates/project/CLAUDE.md`: template workspace counterpart of the live Claude overlay.

### Generated Or Downstream Control-Plane Outputs

- `AGENTS.md`: generated shared runtime contract derived downstream from canonical control-plane data.
- `GEMINI.md`: generated or rendered provider-specific root overlay that must remain downstream of canonical control-plane authority.
- `.github/copilot-instructions.md`: generated provider-specific root overlay that participates in the same downstream contract.
- `.ai-engineering/state/ownership-map.json`: generated ownership projection that must never remain a peer authority.
- `.ai-engineering/state/framework-capabilities.json`: generated capability projection that must remain downstream of the normalized control plane.
- `src/ai_engineering/templates/project/AGENTS.md`, `src/ai_engineering/templates/project/GEMINI.md`, and `src/ai_engineering/templates/project/copilot-instructions.md`: template workspace projections that must stay aligned with the live generated overlays.

### Descriptive Or Non-Authoritative Surfaces

- `.ai-engineering/README.md`: governance guidance and descriptive framing, not a peer control-plane authority.
- `README.md`: user-facing descriptive overview that may reference the control plane but cannot define it.
- `GETTING_STARTED.md`: onboarding guidance that consumes the normalized control plane rather than authoring it.

## Compatibility Boundary

### Constitution Path Boundary

- Root `CONSTITUTION.md` is the only intended constitutional winner, but `.ai-engineering/CONSTITUTION.md` remains a required compatibility input until runtime readers, runbooks, and generated workspace artifacts stop treating it as a peer constitution.
- Any rename or demotion of `.ai-engineering/CONSTITUTION.md` must therefore land behind dual-read handling rather than immediate path removal.

### Ownership And Provenance Field Boundary

- `.ai-engineering/manifest.yml` remains the canonical source for control-plane ownership and provenance semantics during migration.
- `.ai-engineering/state/ownership-map.json` and `.ai-engineering/state/framework-capabilities.json` stay readable as generated projections only; they are compatibility outputs, not peer authorities.
- Existing field names such as `owner`, `frameworkUpdate`, `canonical_source`, `runtime_role`, `sync.template_path`, and `sync.mirror_paths` must support migration through shared resolver logic before any stricter rename or demotion is attempted.

### Root Entry Point Anchor Boundary

- `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `.github/copilot-instructions.md` remain the governed root-entry anchors for compatibility purposes, but they must be discovered through manifest metadata and shared resolver logic rather than duplicated default maps.
- Template counterparts for those anchors must move in lockstep with the live repo surfaces; any aliasing or fallback retained during migration must be shared between live and template flows.

## Decisions

### D-117-11: Root `CONSTITUTION.md` is the sole constitutional authority for this repository

The root constitution becomes the only constitutional surface in this repo. If `.ai-engineering/CONSTITUTION.md` remains, it must be renamed or narrowed into a workspace charter/project-policy surface and must no longer claim supreme authority or Step 0 status.

**Rationale**: the current dual-constitution model creates active authority conflicts in bootstrap, runbooks, runtime loading, and event reporting.

### D-117-12: Control-plane authority is modeled per field, not per file

`manifest.yml` may continue to contain both operator-authored and framework-managed regions, but each control-plane field must be classified as canonical input, generated projection seed, compatibility alias, or descriptive metadata. Generated state files and descriptive docs are never peer authorities.

**Rationale**: the current problem is not only mixed files but mixed semantics inside the manifest and around it.

### D-117-13: Ownership and provenance enforcement must converge on one shared resolver

Ownership and provenance rules must be resolved through one executable contract reused by validator, updater, doctor, sync, observability, and tests. Generated ownership or capability projections become downstream outputs of that contract.

**Rationale**: manifest prose, state defaults, generated maps, and tests currently encode overlapping but non-identical control-plane assumptions.

### D-117-14: `HX-01` uses compatibility-first migration

Before any canonical rename, demotion, or deletion, the runtime must support dual-read compatibility for affected constitution, manifest, root-surface, and ownership/provenance anchors. Strict validators and tests can only flip after that compatibility layer exists.

**Rationale**: the current control plane is consumed by runtime code, validators, sync generation, doctor phases, updater protection, observability, and tests. Direct cutover would create avoidable breakage.

### D-117-15: Live and template control-plane artifacts move together

Any normalized control-plane contract must be updated in both the source repo and the template workspace artifacts in the same feature slice.

**Rationale**: source-repo behavior and installed workspace behavior already share assumptions; splitting them would create a false pass locally and broken installs downstream.

### D-117-16: Control-plane validation must become explicit, not incidental

`HX-01` must add or strengthen validation so constitutional authority, canonical-vs-generated classification, ownership/provenance contract shape, and normalized control-plane paths are checked directly.

**Rationale**: today many failures surface only through indirect test breakage or stale generated projections rather than a first-class control-plane invariant.

## Risks

- **Constitution migration risk**: renaming or demoting `.ai-engineering/CONSTITUTION.md` could break runbooks, bootstrap, or event reporting. **Mitigation**: add dual-read compatibility and path coverage before cutover.
- **Ownership enforcement regression**: moving to a shared resolver could accidentally weaken updater or doctor protections. **Mitigation**: port executable enforcement first, then tighten schema and tests.
- **Template drift risk**: updating only the live repo would desynchronize generated workspaces. **Mitigation**: require live/template lockstep in the same feature.
- **Projection staleness risk**: stale `ownership-map.json` or `framework-capabilities.json` can mask whether the new authority model is correct. **Mitigation**: regenerate or explicitly reclassify projections during validation.
- **Scope bleed into HX-03/HX-05/HX-06**: provenance, state, and multi-agent concerns overlap with later features. **Mitigation**: keep `HX-01` focused on authority and enforcement contracts, not broader mirror/runtime cleanup.

## Deferred Cleanup From HX-01

- `HX-03` owns retirement of the remaining root-first plus workspace-charter fallback wording that still lives in mirrored runbooks, provider-local skills, and manual instruction families. `HX-01` keeps those surfaces compatibility-safe but does not try to rewrite or retire mirror-local alias guidance.
- `HX-05` owns any eventual removal or reclassification of workspace-charter compatibility reads that still exist for observability, audit, or state-plane continuity. `HX-01` only normalizes the control-plane contract and keeps the dual-read path safe during the migration window.
- `HX-06` owns the final capability-side cutover for transitional projections such as `framework-capabilities.json` and any machine-readable mutation policy over constitutional, charter, and generated control-plane surfaces. `HX-01` only classifies those surfaces as canonical input versus derived output.

## References

- doc: .ai-engineering/specs/spec-117-hx-01-control-plane-normalization-explore.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: CONSTITUTION.md
- doc: AGENTS.md
- doc: .ai-engineering/CONSTITUTION.md
- doc: .ai-engineering/manifest.yml
- doc: .ai-engineering/state/ownership-map.json
- doc: .ai-engineering/state/framework-capabilities.json
- doc: src/ai_engineering/state/defaults.py
- doc: src/ai_engineering/state/models.py
- doc: src/ai_engineering/validator/categories/manifest_coherence.py
- doc: src/ai_engineering/validator/categories/mirror_sync.py
- doc: scripts/sync_command_mirrors.py

## Open Questions

- Should the workspace-level charter rename happen inside `HX-01`, or can it remain temporarily at the same path with a reduced role?
- Should `framework-capabilities.json` remain committed after authority normalization, or be reclassified as generated/runtime residue?
- Which `work_items` fields belong in canonical manifest input vs generated discovery state?
- Should prompt-only bootstrap fields remain in manifest after control-plane normalization, or be moved later under a narrower contract?
