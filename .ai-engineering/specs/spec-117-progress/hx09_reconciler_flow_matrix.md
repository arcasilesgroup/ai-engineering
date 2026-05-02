# HX-09 Reconciler Flow Matrix

## Scope

`HX-09` owns the local convergence lifecycle shared by install, doctor, and update flows. The governed core contract is inspect, plan, apply, verify, with resource adapters preserving each domain's existing result model.

## Lifecycle Matrix

| Surface | Inspect | Plan | Apply | Verify | Compatibility Boundary |
| --- | --- | --- | --- | --- | --- |
| Installer pipeline | Adapter snapshots the `InstallContext` without mutation. | Existing phase `plan()` output is wrapped as explicit `ReconcileAction` records. | Existing phase `execute()` runs unchanged through the adapter. | Existing phase `verify()` remains the source of pass/fail and non-critical behavior. | `PipelineSummary`, `PhasePlan`, `PhaseResult`, `PhaseVerdict`, dry-run behavior, and progress callback behavior remain stable. |
| Doctor phase runner | Adapter calls phase `check()` once to collect a diagnostic snapshot. | Fixable warnings/failures become explicit fix actions. | Existing phase `fix()` runs only in fix mode and still receives `dry_run`. | Doctor diagnostics stay report-driven; reconciler verification is pass-through so check failures remain diagnostic data, not core failures. | `DoctorReport`, `PhaseReport`, fix-mode replacement behavior, phase filters, pre-install mode, and runtime checks remain stable. |
| Updater | Adapter loads ownership, manifest, install state, providers, and template maps before planning. | Governance, project-template, and orphan changes become explicit update/orphan/skip actions. | Apply owns file writes, orphan cleanup, ownership persistence, legacy cleanup, and event emission after successful postconditions. | Postconditions verify copied content and orphan removal. Failed apply/postconditions restore updated files and deleted orphan files. | `UpdateResult`, `FileChange`, grouped JSON counts, ownership protections, provider filtering, rollback behavior, and dry-run reporting remain stable. |

## Resource Adapter Boundaries

| Resource Family | Owner After HX-09 | First-Cut Behavior |
| --- | --- | --- |
| Detect, governance, IDE config, state, tools, hooks | Existing installer/doctor phase modules | Wrapped by adapters; phase internals are not flattened into one service. |
| Framework update files | Updater service adapter | Evaluated during plan, written during apply, verified before finalize. |
| Disabled-provider orphans | Updater service adapter | Planned as orphan actions; apply deletes them; rollback restores them when later apply steps fail. |
| Feed preflight, VCS auth, branch policy, version checks | Outer runtime probes | Remain outside the first reconciler cut. |
| Kernel blocking semantics | `HX-04` | Not re-owned by Track B. |
| Event/state vocabulary | `HX-05` | Not re-owned by Track B; updater events are emitted after postconditions pass. |
| CLI thinning and asset/runtime split | `HX-10` | Not re-owned by Track B. |

## Preview And Rollback Rules

- Reconciler preview mode stops after inspect and plan.
- Installer dry-run uses reconciler preview and therefore produces plans without execution or verification.
- Updater dry-run uses reconciler preview and no longer runs the legacy hooks-directory migration.
- Doctor fix dry-run remains adapter-level compatibility behavior: legacy phase `fix(..., dry_run=True)` still runs side-effect-free to produce the existing planned-fix result surface.
- Apply failures and postcondition failures trigger adapter rollback hooks.
- Updater rollback now restores updated files, removes newly created files from failed applies, and restores deleted disabled-provider orphan files.

## Deferred Work

- Network and policy probes remain outer adapters until they can express deterministic postconditions.
- Kernel retry/blocking semantics remain governed by `HX-04`.
- Event taxonomy and state-plane vocabulary remain governed by `HX-05`.
- CLI command thinning and installed asset/runtime cleanup remain governed by `HX-10`.