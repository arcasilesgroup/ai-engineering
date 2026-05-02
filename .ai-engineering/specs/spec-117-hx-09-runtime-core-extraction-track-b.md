---
spec: spec-117-hx-09
title: Runtime Core Extraction - Track B
status: done
effort: large
---

# Spec 117 HX-09 - Runtime Core Extraction - Track B

## Summary

Installer, doctor, and updater already express similar convergence logic through different flow families, result models, and resource slices. This feature introduces one resource reconciler core with explicit inspect, plan, apply, and verify phases, so local convergence work stops being duplicated across install, diagnose, repair, and update flows. Resource adapters remain per domain, preview modes become side-effect-free, and rollback/postcondition handling becomes explicit. Kernel-level blocking and state-plane vocabulary remain out of scope.

## Goals

- Define one resource reconciler core for local convergence surfaces.
- Unify inspect, plan, apply, and verify semantics across installer, doctor, and updater adapters.
- Preserve resource-domain adapters such as governance, IDE config, hooks, state, tools, and detect.
- Make preview and dry-run modes explicit and side-effect-free.
- Preserve rollback and postcondition boundaries.

## Non-Goals

- Replacing `HX-04` as the owner of local check blocking semantics.
- Replacing `HX-05` as the owner of event and state vocabulary.
- Thinning CLI adapters or asset/runtime split from `HX-10`.
- Pulling unstable network or policy probes into the reconciler too early.

## Decisions

### D-117-62: Track B defines one resource reconciler core

The core contract is inspect, plan, apply, verify over explicit resource adapters.

**Rationale**: installer, doctor, and updater already contain this shape in partial forms.

### D-117-63: Resource adapters remain the unit of domain ownership

Detect, governance, IDE config, hooks, state, tools, and similar slices remain domain adapters over the reconciler instead of being flattened into one service.

**Rationale**: those seams already carry real behavior boundaries and should survive the rewrite.

### D-117-64: Preview must be side-effect-free and apply must own rollback

Inspect and plan paths may not perform hidden mutations. Apply owns explicit mutation plus rollback hooks and postcondition verification.

**Rationale**: current preview or mixed flows still hide side effects and weaken trust.

### D-117-65: Outer runtime policy probes remain outside the first reconciler cut

Auth, branch-policy, feed health, and similar network or policy probes remain outer adapters until they can express stable reconcile postconditions.

**Rationale**: pulling them into the core too early would widen blast radius and mix runtime policy with local convergence.

## Risks

- **Outcome-family risk**: installer, doctor, and updater currently expose different result models. **Mitigation**: keep adapters over the reconciler until compatibility is proven.
- **Hidden-side-effect risk**: preview paths currently mutate in some cases. **Mitigation**: fail tests on side-effectful preview and isolate legacy migrations.
- **UX regression risk**: install and auto-remediation behavior is user-visible. **Mitigation**: preserve adapter semantics until reconciler parity is shown.

## Implementation Notes

- Added `src/ai_engineering/reconciler.py` as the shared resource reconciler core with inspect, plan, apply, verify, rollback, and finalize lifecycle hooks.
- Installer phases now run through `_InstallPhaseAdapter` in `src/ai_engineering/installer/phases/pipeline.py`, preserving `PipelineSummary`, dry-run plan-only behavior, phase criticality, and progress callbacks.
- Doctor phases now run through `_DoctorPhaseAdapter` in `src/ai_engineering/doctor/service.py`, preserving phase module `check()`/`fix()` contracts, diagnostic result models, phase filters, and runtime checks.
- Updater flows now run through `_UpdateAdapter` in `src/ai_engineering/updater/service.py`, preserving `UpdateResult`/`FileChange` compatibility while making update apply explicit and verified.
- Updater dry-run no longer runs the legacy hooks-directory migration, and updater rollback now restores updated files, newly created files, and deleted disabled-provider orphan files when later apply or postcondition steps fail.
- Outer runtime probes for feed preflight, VCS auth, branch policy, and version checks remain outside the first reconciler cut.
- Kernel blocking semantics from `HX-04`, event/state vocabulary from `HX-05`, and CLI adapter thinning from `HX-10` remain deferred and are not re-owned by Track B.

## Verification

- `51` focused reconciler/adapter tests passed.
- `76` focused-plus-adjacent updater and install e2e tests passed after Sonar cleanup.
- `245` broader doctor and installer phase compatibility tests passed.
- Ruff syntax/import checks passed for touched source and test files.
- Editor diagnostics reported no errors for touched source and test files.
- SonarQube for IDE touched-file analysis returned `findingsCount: 0`.

## References

- doc: .ai-engineering/specs/spec-117-hx-09-runtime-core-extraction-track-b-explore.md
- doc: .ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md
- doc: src/ai_engineering/installer/phases/pipeline.py
- doc: src/ai_engineering/doctor/service.py
- doc: src/ai_engineering/updater/service.py

## Open Questions

- Resource families moved first: installer phases, doctor phases, and updater local template/orphan resources through compatibility adapters.
- Preview purity in the first cut: reconciler preview stops after inspect/plan; updater dry-run is side-effect-free for the legacy hook migration; doctor fix dry-run remains a legacy side-effect-free compatibility surface.
- Outer policy probes remain outside the reconciler until a later feature defines deterministic postconditions for them.