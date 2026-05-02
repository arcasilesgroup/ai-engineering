---
spec: spec-117-hx-05
title: State Plane and Observability Normalization
status: done
effort: large
---

# Spec 117 HX-05 - State Plane and Observability Normalization

## Summary

ai-engineering currently mixes durable governance truth, derived projections, runtime residue, and spec-local evidence inside one global state root. Its audit plane is intended to be the hash-chained framework-events stream plus the decision ledger, but provider naming, event vocabulary, writer paths, and report surfaces drift across runtime code, hooks, and downstream consumers. This feature normalizes the state plane so durable truth, residue, and spec-local evidence have distinct homes, the event plane has one canonical contract, task traces become a first-class append-only audit view, and scorecards remain derived views rather than peer state authorities.

## Goals

- Separate cross-spec durable truth, runtime residue, and spec-local evidence into explicit artifact families.
- Keep only authoritative cross-spec records in the global durable state root.
- Normalize provider IDs, event kinds, and writer semantics into one canonical event contract.
- Add task traces with stable task identity, lifecycle phase, and artifact references as append-only audit views.
- Make scorecards and reporting surfaces derived from authoritative inputs rather than peer truths.
- Preserve audit-chain integrity and serialized families where shared append or publish hazards exist.
- Avoid absorbing kernel execution ownership, work-plane ownership, or learning-funnel ownership that belongs elsewhere.

## Non-Goals

- Replacing the `HX-04` harness kernel as the authority for local check execution.
- Replacing the `HX-02` work plane and task ledger as the authority for task state.
- Owning lessons, instincts, proposals, or context-pack lifecycle from `HX-07`.
- Owning full eval classification and performance baselines from `HX-11`.
- Rewriting mirror-family governance from `HX-03`.

## Decisions

### D-117-42: Global durable state is narrow and cross-spec only

Only records that remain authoritative across specs and after the originating task or session is gone may live in the global durable state root. Spec-local evidence must move under the owning work plane, and disposable outputs must move to residue.

**Rationale**: today the state root mixes long-lived ledgers with session residue and spec-specific artifacts, which obscures authority and retention rules.

### D-117-43: Runtime residue is disposable and cannot be required for correctness

Caches, last-run findings, compatibility snapshots, temporary diagnostics, and similar artifacts belong to a residue subtree with retention and GC rules. No validator, orchestrator, or reviewer may require residue for correctness.

**Rationale**: residue currently lives beside durable truth and can be mistaken for peer authority.

### D-117-44: Framework events and the decision ledger remain the canonical durable audit plane

`HX-05` keeps one append-only framework-events chain and one decision ledger as the durable audit substrate. It does not create a second canonical event log or chain field.

**Rationale**: audit truth must stay singular if later slices are going to trust it.

### D-117-45: Task traces are append-only audit views over authoritative mutations

Task traces become a first-class event envelope carrying stable task identity, lifecycle phase, parent/correlation lineage, and artifact references. They are emitted from authoritative work-plane and kernel outcomes, but they do not decide task state themselves.

**Rationale**: the repo already carries enough correlation primitives, but it lacks one stable task-level join model.

### D-117-46: Scorecards and reports are derived views, never peer authorities

Harness scorecards, task-resolution summaries, retry and rework reports, verification tax views, context-size views, and drift counts may be persisted for UX or performance, but only as clearly derived projections with provenance and regeneration paths.

**Rationale**: reporting already exists in fragmented forms, and it will become dangerous if those views harden into competing truth sources.

### D-117-47: Event vocabulary and provider naming normalize through one state-layer contract

Provider identifiers, event kinds, and root event fields must normalize through one canonical state-layer contract used by runtime writers and hook adapters.

**Rationale**: current drift across `copilot` and `github_copilot` and across one-off event kinds weakens observability joins and validation.

## Governed Inventory

### Global State And Evidence Families

| Family | Representative surfaces | Classification | Current authority | HX-05 migration note |
| --- | --- | --- | --- | --- |
| Cross-spec durable truth | `.ai-engineering/state/decision-store.json`, `.ai-engineering/state/framework-events.ndjson`, `.ai-engineering/state/install-state.json` | Durable global state | Governance and audit plane | Must stay authoritative and cross-spec after the split. |
| Generated cross-spec projections | `.ai-engineering/state/ownership-map.json`, `.ai-engineering/state/framework-capabilities.json` | Derived projection | Generated from code/contracts, not peer truth | Must remain visibly regenerated and never become required for correctness. |
| Runtime residue and last-run outputs | `.ai-engineering/state/gate-findings.json`, `.ai-engineering/state/watch-residuals.json`, `.ai-engineering/state/gate-cache/`, `.ai-engineering/state/strategic-compact.json`, `.ai-engineering/state/locks/` | Residue | Operational helpers and last-run output surfaces | Need explicit retention and compatibility rules; residue cannot be required for correctness. |
| Learning-funnel or session residue | `.ai-engineering/state/instinct-observations.ndjson` | Deferred ownership | `HX-07` learning funnel | `HX-05` must classify it without absorbing learning-funnel lifecycle. |
| Spec-local evidence relocated behind compatibility shims | `.ai-engineering/specs/evidence/spec-116/spec-116-t31-audit-classification.json`, `.ai-engineering/specs/evidence/spec-116/spec-116-t41-audit-findings.json` | Spec-local evidence | Owning spec evidence lane | Canonical copies now live under the spec-scoped evidence lane; the legacy `.ai-engineering/state/` paths remain temporary readable shims until direct readers finish cutting over. |

### Event Emitters And Writer Families

| Surface | Representative paths | Role | Ownership boundary |
| --- | --- | --- | --- |
| Runtime event appenders | `src/ai_engineering/state/observability.py` | Authoritative framework-events writers and helper emitters | `HX-05` owns the normalized event contract; `HX-04` sequencing and kernel outputs remain upstream inputs. |
| Hook-side event adapters | `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/hook-common.py`, `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/copilot-common.sh`, `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/copilot-common.ps1` | Compatibility writers that currently drift on provider ids and event kinds | Must adapt into one canonical state-layer contract rather than define semantics independently. |
| Audit-chain readers | `src/ai_engineering/state/audit_chain.py`, `src/ai_engineering/cli_commands/audit_cmd.py` | Derived integrity views over the canonical event and decision ledgers | Must stay downstream of the durable audit plane. |
| Kernel-adjacent result publishers | `src/ai_engineering/policy/orchestrator.py`, `src/ai_engineering/policy/watch_residuals.py` | Publish operator-facing findings and residual artifacts | `HX-04` keeps execution truth; `HX-05` only classifies these outputs as residue or derived report surfaces. |

### Report And Derived View Surfaces

| Surface | Representative paths | Classification | Constraint |
| --- | --- | --- | --- |
| Verification score output | `src/ai_engineering/cli_commands/verify_cmd.py`, `src/ai_engineering/verify/scoring.py` | Derived report | Must not harden into peer state authority. |
| Maintenance health report | `src/ai_engineering/maintenance/report.py`, `.ai-engineering/state/maintenance-report.md` | Derived report snapshot | If persisted, it needs provenance and regeneration rules. |
| CLI validation drift output | `src/ai_engineering/cli_commands/validate.py` | Derived report | Consumes authoritative inputs but does not own them. |
| Agentsview or export-style copies | `src/ai_engineering/state/agentsview.py` | Derived projection/export | Must stay downstream of normalized event and capability contracts. |

## Compatibility Boundary

### Compatibility Matrix

| Surface family | Current paths | Compatibility readers or writers | Compatibility-first rule |
| --- | --- | --- | --- |
| Generated current-state projections | `.ai-engineering/state/ownership-map.json`, `.ai-engineering/state/framework-capabilities.json` | `manifest_coherence`, doctor phases, installer or updater helpers, `agentsview` exports | Stay readable at current paths as generated projections only; consumers must tolerate regeneration or absence and cannot treat them as peer truth. |
| Residual findings and operator outputs | `.ai-engineering/state/gate-findings.json`, `.ai-engineering/state/watch-residuals.json`, `.ai-engineering/state/gate-cache/`, `.ai-engineering/state/strategic-compact.json`, `.ai-engineering/state/locks/` | `policy.orchestrator`, `policy.watch_residuals`, `risk` flows, watch or report surfaces, operator follow-up commands | Stay compatibility-safe residue until the normalized residue tree lands; no consumer may require them for correctness or infer durable state from their presence. |
| Durable audit append path | `.ai-engineering/state/framework-events.ndjson` | `state.observability`, hook adapters, `audit_chain`, `audit_cmd`, downstream activity readers | Remains the sole durable append target during migration, with the existing ordered or single-writer behavior preserved across runtime and hook writers. |
| Spec-local audit spillover compatibility shims | `.ai-engineering/specs/evidence/spec-116/spec-116-t31-audit-classification.json`, `.ai-engineering/specs/evidence/spec-116/spec-116-t41-audit-findings.json`; legacy readable shims at `.ai-engineering/state/spec-116-t31-audit-classification.json`, `.ai-engineering/state/spec-116-t41-audit-findings.json` | Remaining audit or validation readers that still probe the global state root | Canonical reads resolve through the spec-local evidence lane first; the legacy global paths stay readable shim copies until the last direct readers are retired. |

### Boundary Rules

- Compatibility readers may keep current paths during migration, but they must classify projections and residue as derived or advisory inputs rather than authoritative truth.
- Relocation or demotion must add a compatibility view or adapter before cutover; `HX-05` must not create second authorities just to preserve old paths.
- `gate-findings` publication, residual publication, and `framework-events` append semantics keep the explicit ordered-family rules carried forward from `HX-04`.
- `HX-05` Phase 1 stops at the reader or writer boundary: task-state ownership stays with `HX-02`, capability authority with `HX-06`, learning-funnel lifecycle with `HX-07`, and verification taxonomy with `HX-11`.

## Risks

- **Consumer breakage**: moving quasi-authoritative files out of global state may break consumers that depended on current paths. **Mitigation**: add compatibility views or adapters before cutover.
- **Audit-chain risk**: widening event emission without controlling writers can worsen hash-chain races. **Mitigation**: keep event-emitting families serialized and introduce shared writer rules before adding more emitters.
- **Projection drift**: persisted scorecards can become peer authorities if provenance is weak. **Mitigation**: require explicit regeneration paths and classification.
- **Boundary bleed**: task traces can accidentally become a second task-state machine. **Mitigation**: keep authoritative task state in `HX-02` and make traces append-only views.
- **Capability ambiguity**: framework-capabilities remains in an awkward transitional state until `HX-06` is enforced. **Mitigation**: classify it as derived and avoid creating similar ambiguous projections.

## Deferred Cleanup From HX-02

- `HX-02` keeps compatibility `spec.md` and `plan.md` views in place as derived migration shims. `HX-05` still needs to classify any remaining compatibility snapshots, residue, or projections so those paths stay visibly derived rather than drifting back into peer authority.
- `HX-02` only introduced the minimum ledger-aware audit and active-spec context needed to finish the resolver cutover. Event vocabulary normalization, task traces, scorecards, and the durable-versus-derived split for new work-plane projections remain owned here.
- The active pointer currently lives under `.ai-engineering/specs/active-work-plane.json` as a migration contract. `HX-05` remains the owner of any broader decision about whether that state should move under a wider state plane while preserving compatibility for existing readers.

## Deferred Cleanup From HX-01

- `HX-01` moved source and hook observability readers onto root-first helper-based constitution resolution but intentionally preserved the `.ai-engineering/CONSTITUTION.md` compatibility fallback. `HX-05` owns any eventual retirement, reclassification, or audit-plane treatment of that alias-aware state and observability behavior.
- If workspace-charter compatibility reads become residue, derived audit views, or disappear entirely, `HX-05` owns the retention and event-vocabulary consequences. `HX-01` only established the control-plane contract that those later state-plane decisions must honor.

## Deferred Follow-On Owners After HX-05

### HX-06 - Capability Projection Cleanup

- `framework-capabilities.json` is now explicitly classified as a derived projection, but it remains a transitional capability view until `HX-06` formalizes capability cards, mutation classes, tool scope, provider compatibility, and topology role as the authoritative contract. `HX-05` will not turn that projection into a peer authority.
- The strict state-plane cutover in `T-5.1` means capability-aware readers must consume canonical state-plane paths and task traces rather than probing compatibility shims. `HX-06` owns any machine-readable capability policy that constrains which agents or skills may mutate state-plane, report, or evidence surfaces.
- If capability projections are renamed, regenerated from a new schema, or retired entirely, `HX-06` owns the migration contract. `HX-05` only guarantees that the current projection stays visibly derived and downstream of the normalized state and observability plane.

### HX-07 - Learning-Funnel Ownership

- `HX-05` classified `.ai-engineering/state/instinct-observations.ndjson` as deferred learning-funnel residue and intentionally stopped short of defining retention, promotion, pack-manifest linkage, or knowledge-placement lifecycle. Those rules remain owned by `HX-07`.
- Task traces and work-plane summaries are now stable enough for `HX-07` to consume as inputs to context-pack generation and learning-funnel transitions, but `HX-07` must not re-own task state, trace semantics, or the canonical event writer. `HX-05` only exposes those surfaces as upstream contracts.
- If learning artifacts need durable or derived projections outside the funnel, `HX-07` owns the promotion rules and provenance links. `HX-05` will not widen the global state root to host learning outputs directly.

### HX-11 - Eval And Report Taxonomy

- `HX-05` normalized local validation drift output, maintenance scorecards, and task traces as derived reports over authoritative inputs, but it does not define the broader verification taxonomy, check-family classification, or eval-pack architecture. Those concerns remain with `HX-11`.
- `HX-11` should consume canonical framework events, task traces, and derived scorecards as upstream inputs when it defines measurement families, aggregation, and reporting cuts. `HX-05` will not create a second measurement plane or encode eval-only semantics into the state layer.
- Deeper report taxonomy decisions such as whether future verification views join directly to `framework-events.ndjson`, consume a trace projection, or aggregate maintenance or validate outputs into a shared measurement model are explicitly deferred to `HX-11`.

## References

- doc: .ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization-explore.md
- doc: .ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md
- doc: .ai-engineering/specs/spec-117-hx-04-harness-kernel-unification.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .ai-engineering/state/decision-store.json
- doc: .ai-engineering/state/framework-events.ndjson
- doc: src/ai_engineering/state/control_plane.py
- doc: src/ai_engineering/state/observability.py
- doc: src/ai_engineering/state/audit_chain.py
- doc: src/ai_engineering/state/agentsview.py
- doc: src/ai_engineering/state/models.py
- doc: src/ai_engineering/validator/categories/manifest_coherence.py
- doc: src/ai_engineering/policy/orchestrator.py
- doc: src/ai_engineering/policy/watch_residuals.py
- doc: src/ai_engineering/cli_commands/risk_cmd.py
- doc: src/ai_engineering/maintenance/report.py
- doc: src/ai_engineering/verify/service.py

## Open Questions

- Should task traces live directly in the canonical framework-events stream or as a regenerated projection over it plus ledger state?
- What is the compensating path for successful authoritative writes when audit append fails?
- Which scorecards, if any, merit persisted snapshots versus on-demand regeneration?
- When should `framework-capabilities.json` be cut over to an explicit derived view of the `HX-06` capability contract?
- Which learning-funnel promotions, if any, should become durable state instead of remaining funnel-owned residue under `HX-07`?
- Should future verification or eval reports join directly to canonical task traces, or to a later `HX-11` measurement projection built over them?
- Is strict sequencing enough for audit writers in the first cut, or is explicit locking required?