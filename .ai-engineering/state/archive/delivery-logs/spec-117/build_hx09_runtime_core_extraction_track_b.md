# Build: HX-09 Runtime Core Extraction Track B

## Summary

Implemented a shared local resource reconciler and routed installer, doctor, and updater convergence flows through adapter-backed inspect, plan, apply, and verify phases.

## Code Changes

- Added `src/ai_engineering/reconciler.py` with the public `ResourceReconciler` lifecycle, action vocabulary, lifecycle result records, adapter protocol, rollback hooks, and finalize hook.
- Routed `src/ai_engineering/installer/phases/pipeline.py` through `_InstallPhaseAdapter`, preserving `PipelineSummary`, dry-run plan-only behavior, phase criticality, and progress callbacks.
- Routed `src/ai_engineering/doctor/service.py` through `_DoctorPhaseAdapter`, preserving phase `check()`/`fix()` modules, `DoctorReport`, fix-mode replacement behavior, phase filters, and runtime checks.
- Routed `src/ai_engineering/updater/service.py` through `_UpdateAdapter`, preserving `UpdateResult` and `FileChange` surfaces while making update preview a reconciler plan and update apply an explicit apply/verify/finalize pass.
- Isolated the legacy hook-directory migration from updater dry-run so preview no longer mutates disk.
- Tightened updater rollback so failed applies restore updated files, remove newly created files, and restore deleted disabled-provider orphan files.
- Moved update event emission to reconciler finalize so events are emitted only after postconditions pass.

## Tests Added Or Updated

- Added `tests/unit/test_reconciler.py` for preview purity, postcondition verification, apply-exception rollback, and verification-failure rollback.
- Added installer pipeline coverage proving phases run through the reconciler lifecycle.
- Added doctor service coverage proving phase execution runs through the reconciler lifecycle.
- Added updater coverage for dry-run hook-migration purity and orphan restore after a later apply failure.

## Boundaries Preserved

- Installer phase classes remain the resource-domain owners for install semantics.
- Doctor phase modules remain the resource-domain owners for diagnostic checks and fixes.
- Updater service remains the owner of template evaluation, ownership enforcement, and provider filtering.
- Runtime feed preflight, VCS auth, branch policy, and version checks remain outside the first reconciler cut.
- Kernel blocking semantics from `HX-04`, event/state vocabulary from `HX-05`, and CLI thinning from `HX-10` remain deferred.