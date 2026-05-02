# HX-09 Explore - Runtime Core Extraction Track B

This artifact captures the evidence gathered before writing the feature spec for `HX-09`.

## Scope

Feature: `HX-09` Runtime Core Extraction - Track B.

Question: what must change so installer, doctor, and updater converge on one inspect/plan/apply/verify reconciler engine instead of parallel flow families with duplicated resource logic and mixed mutation/verification semantics?

## Evidence Summary

### All Three Families Already Hint At A Reconciler Shape

- Installer already has explicit phase plan, execute, and verify behavior.
- Doctor mirrors similar domains as check/fix modules.
- Updater already behaves like preview/apply with explicit action objects and rollback behavior.

The repo therefore already contains the seeds of one reconciler, but they are spread across three outcome families.

### Resource Domains Are Repeated Across Installer And Doctor

- Detect, governance, state, hooks, and tools exist as parallel installer and doctor slices.
- Tools are the strongest duplication family, with similar probing, normalization, and remediation pathways.
- Shared remediation and install-to-doctor delegation already exist as partial common seams.

This is the clearest convergence target for Track B.

### Mutation And Verification Are Still Mixed In Several Flows

- Some install and update paths mix inspection, migration, mutation, and re-verification in one flow.
- Some doctor fix helpers combine re-check and mutation without a separate plan artifact.
- Updater preview still contains side effects in some legacy migrations.

Track B therefore needs a stricter separation between inspect, plan, apply, and verify.

### Stable Seams Should Survive

- Resource adapters by domain should remain the ownership unit.
- Updater action vocabulary and rollback boundaries are good seeds.
- Runtime probes for auth, branch policy, feeds, or version should remain outside the core reconciler until they can express stable postconditions.

### `HX-09` Must Not Re-Own Kernel Semantics

- `HX-04` already owns execution order, retry, loop, and findings semantics for local checks.
- Track B should hand verify outcomes to those layers, not redefine blocking semantics or retry policy.

## High-Signal Findings

1. The highest-value boundary for Track B is one resource reconciler core: inspect, plan, apply, verify.
2. Resource adapters should remain per domain instead of being flattened.
3. Dry-run purity needs to become explicit because preview modes are not fully side-effect-free today.
4. Auth, branch policy, and networked policy checks should remain outer adapters until they can express stable reconcile postconditions.

## Recommended Decision Direction

### Preferred Reconciler Direction

- Define one resource reconciler core for local convergence surfaces such as governance files, IDE files, hooks, state artifacts, and tools.
- Make inspect side-effect-free and snapshot-oriented.
- Make plan emit explicit reconcile actions and expected postconditions.
- Make apply run resource-specific executors plus rollback hooks.
- Make verify report domain drift outcomes without redefining kernel semantics.

### Preferred Adapter Direction

- Installer becomes one adapter over the reconciler.
- Doctor becomes inspect-plus-verify or inspect-plan-apply-verify in fix mode.
- Updater becomes preview/apply over the same engine.
- Runtime probes remain outside until their lifecycle is more stable.

## Migration Hazards

- Three current outcome families are live and incompatible.
- Ownership semantics differ across updater and installer flows.
- Preview modes are not purely side-effect-free today.
- UX around non-critical tools and auto-remediation is already user-visible and easy to regress.

## Scope Boundaries For HX-09

In scope:

- reconciler engine core
- resource adapter convergence for local convergence surfaces
- inspect/plan/apply/verify contract
- rollback and postcondition boundaries

Out of scope:

- kernel blocking semantics from `HX-04`
- event/state taxonomy from `HX-05`
- CLI adapter thinning from `HX-10`

## Open Questions

- Which resource families should move first into the reconciler core?
- How pure must preview mode be in the first cut?
- When can auth/branch-policy/network probes join the reconciler rather than remain outer adapters?

## Source Artifacts Consulted

- `src/ai_engineering/installer/phases/**`
- `src/ai_engineering/installer/service.py`
- `src/ai_engineering/installer/auto_remediate.py`
- `src/ai_engineering/doctor/service.py`
- `src/ai_engineering/doctor/phases/**`
- `src/ai_engineering/doctor/runtime/**`
- `src/ai_engineering/doctor/remediation.py`
- `src/ai_engineering/updater/service.py`
- `.ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md`