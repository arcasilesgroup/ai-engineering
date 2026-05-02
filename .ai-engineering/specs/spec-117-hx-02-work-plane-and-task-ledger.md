---
spec: spec-117-hx-02
title: Work Plane and Task Ledger
status: done
effort: large
---

# Spec 117 HX-02 - Work Plane and Task Ledger

## Summary

ai-engineering currently uses a mixed work model: global `spec.md` and `plan.md` buffers, `_history.md`, `done.md`-style closure, spec-specific follow-on artifacts, and separate autonomous run state. That model is already incoherent in a live way because the active spec and active plan can diverge without detection. This feature replaces the singleton-buffer authority model with a spec-scoped work plane backed by an active pointer, a first-class task ledger, explicit handoff and evidence artifacts, and separate current/history summaries. The result is that later agents, validators, and runtime flows can resume work from disk alone, and build readiness becomes a durable, auditable decision rather than chat convention.

## Goals

- Define one spec-scoped work-plane contract with an authoritative active pointer.
- Introduce a first-class task ledger that records task identity, status, owner role, dependencies, write scope, handoffs, evidence, and blocked metadata.
- Separate mutable current state from append-only history and from raw evidence/log residue.
- Replace implicit build readiness with an explicit, durable, validator-friendly work-plane decision model.
- Give CLI, verify, validators, observability, audit, work-item sync, PR generation, and orchestrators one shared active-work-plane resolver.
- Preserve compatibility for install/bootstrap and existing `spec` CLI surfaces while the singleton buffers are demoted into compatibility or generated views.
- Keep source-repo and template-workspace work-plane behavior aligned during migration.

## Non-Goals

- Reworking control-plane constitutional authority from `HX-01`.
- Rewriting provider mirrors or public/internal agent surfaces from `HX-03`.
- Unifying the harness kernel or broader check engine from `HX-04`.
- Performing late runtime-core extractions from `HX-08`, `HX-09`, or `HX-10`.
- Using chat memory, conversational summaries, or human inference as authoritative task state.
- Adding optimistic parallelism without explicit dependencies and disjoint write scopes.

## Decisions

### D-117-17: The work plane is spec-scoped and resolved through one active pointer

Each active feature owns a spec-scoped work-plane root containing the artifacts needed to resume and validate that feature. The repository exposes one authoritative active pointer to resolve the currently active work plane.

**Rationale**: the current singleton-buffer model cannot express resumable feature-local state safely, and it already allows spec/plan drift.

**Current runtime contract**: during the compatibility migration, the authoritative pointer lives at `.ai-engineering/specs/active-work-plane.json` and stores a project-relative `specsDir` field naming the active work-plane root. When the pointer is missing or invalid, runtime consumers fall back to the legacy singleton buffer at `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/plan.md`.

Runtime now owns explicit pointer lifecycle seams as well as pointer resolution: `src/ai_engineering/maintenance/spec_activate.py` activates or selects a work-plane root and writes the pointer without overwriting real spec/plan content, while `src/ai_engineering/maintenance/spec_reset.py` restores the legacy compatibility buffer and clears the pointer on closeout.

### D-117-18: The task ledger is the authoritative execution-state contract

Execution status is no longer inferred primarily from markdown checkboxes, `_history.md`, or `done.md`. A first-class task ledger becomes the authoritative source for task identity, lifecycle state, dependencies, owner role, write scope, handoff refs, evidence refs, and blocked reasons.

**Current runtime contract**: the first machine-readable ledger surface is `task-ledger.json` at the active work-plane root. The initial schema is intentionally narrow: task id, title, lifecycle state, owner role, dependency refs, write scopes, handoff refs, evidence refs, and blocked reason when status is `blocked`.

**Rationale**: orchestration quality depends on knowing what exact unit of work is active, what it may change, and what evidence proves completion.

### D-117-19: Current state, history, and evidence are separate artifact classes

The work plane distinguishes:

- mutable current summary
- append-only history summary
- structured task ledger
- handoff artifacts
- evidence artifacts and raw logs

**Current runtime topology**: the active work-plane root now projects these artifact classes as `current-summary.md`, `history-summary.md`, `task-ledger.json`, `handoffs/`, and `evidence/` alongside the compatibility `spec.md` and `plan.md` views.

None of those surfaces should collapse into the others.

**Rationale**: resumability fails when current state, closure history, and raw output are mixed into one document family.

### D-117-20: Build readiness is a work-plane decision, not a conversational decision

A feature may move into build only when its own `explore -> spec -> plan` package exists and the work plane records that readiness explicitly. For this root-refactor program, the first implementation wave begins only after the full portfolio has a persisted and validated `explore -> spec -> plan` baseline or an explicit approved deferral for any later-wave feature.

**Rationale**: the user requirement for this program is stricter than the legacy runtime. The work plane must carry the decision so later agents do not rely on chat memory or oral tradition.

### D-117-21: Runtime and validation consumers must share one active-work-plane resolver

CLI commands, maintenance/reset flows, verify, validators, observability, audit, policy gating, work-item sync, and PR generation must resolve active work through one shared contract instead of hard-coded `spec.md` and `plan.md` paths.

**Rationale**: the current authority problem is distributed across many readers. Replacing only one surface would leave the work plane split.

### D-117-22: Singleton buffers remain only as compatibility or generated views during migration

`spec.md`, `plan.md`, and related install/bootstrap expectations may remain during migration, but they are compatibility shims or generated projections of the spec-scoped work plane, not peer authorities.

**Rationale**: users, templates, tests, and CLI flows still depend on these paths, but keeping them as coequal truth sources would preserve the core bug.

### D-117-23: Parallel execution is allowed only through explicit dependencies and disjoint write scopes

The task ledger must declare dependency edges and write scopes strongly enough that orchestrators can reject unsafe parallel work.

**Rationale**: ai-engineering already has many agents and orchestrators. `HX-02` must give them a collision model before implementation volume increases.

## Risks

- **Compatibility drag**: keeping `spec.md` and `plan.md` as shims too long can preserve ambiguity. **Mitigation**: mark them as derived views and add explicit resolver-based validation.
- **Schema overreach**: an over-complex ledger could slow adoption and duplicate later kernel/state work. **Mitigation**: keep the ledger focused on execution truth and artifact refs, not verbose prose.
- **Consumer skew**: CLI, validators, telemetry, and PR/work-item flows can drift if migrated separately. **Mitigation**: move all readers behind a shared resolver before tightening invariants.
- **Cache staleness**: existing gate-cache logic may ignore new work-plane inputs and replay stale results. **Mitigation**: treat active pointer, ledger, summaries, and handoff/evidence refs as cache inputs where relevant.
- **Template divergence**: source repo and installed workspace can split again if templates lag. **Mitigation**: update live and template work-plane assets in one feature slice.

## Deferred Cleanup Routed To Later Features

- `HX-04`: `HX-02` intentionally stops short of defining one authoritative kernel result envelope, blocked-disposition semantics, retry ceilings, or hook and CLI adapter convergence. Any tightening of how kernel outcomes mutate task state must land under `HX-04` and then be consumed by the `HX-02` work plane rather than redefined here.
- `HX-05`: the compatibility `spec.md` and `plan.md` views remain migration shims, and `HX-02` only adds the minimum resolver-aware audit context needed for the cutover. Broader event vocabulary normalization, task traces, scorecards, residue classification, and any future relocation of active-pointer or work-plane state into a wider state plane remain deferred to `HX-05`.
- `HX-06`: `HX-02` now records write scope, dependencies, handoffs, and evidence in the task ledger, but it does not yet enforce capability cards, tool scope, provider compatibility, topology role, or illegal mutation classes. Transitional capability projections such as `framework-capabilities.json` remain advisory until `HX-06` formalizes them as derived views of the capability contract.

## References

- doc: .ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger-explore.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .ai-engineering/specs/spec-117-orchestrator-operating-prompt.md
- doc: .ai-engineering/specs/spec.md
- doc: .ai-engineering/specs/plan.md
- doc: src/ai_engineering/cli_commands/spec_cmd.py
- doc: src/ai_engineering/maintenance/spec_activate.py
- doc: src/ai_engineering/maintenance/spec_reset.py
- doc: src/ai_engineering/verify/service.py
- doc: src/ai_engineering/policy/orchestrator.py
- doc: src/ai_engineering/policy/gate_cache.py
- doc: src/ai_engineering/state/observability.py
- doc: src/ai_engineering/state/audit.py
- doc: src/ai_engineering/work_items/service.py
- doc: src/ai_engineering/vcs/pr_description.py

## Open Questions

- Should the authoritative ledger live in one machine-readable file or a small directory of structured files?
- Which compatibility surfaces should be generated first: `spec.md`, `plan.md`, `done.md`, or status summaries for CLI/UI views?
- Should portfolio-wide build-start gating live fully in validator logic, orchestration logic, or a split contract between both?
- Which event vocabulary additions belong in `HX-02` vs `HX-05`?
- What minimal task states are needed for v1: `planned`, `in_progress`, `blocked`, `review`, `verify`, `done`, or a narrower set?