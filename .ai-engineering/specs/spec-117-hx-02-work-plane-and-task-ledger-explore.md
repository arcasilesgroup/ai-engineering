# HX-02 Explore - Work Plane and Task Ledger

This artifact captures the evidence gathered before writing the feature spec for `HX-02`.

## Scope

Feature: `HX-02` Work Plane and Task Ledger.

Question: what must change so ai-engineering stops treating the global `spec.md` and `plan.md` buffer as the real execution model and instead gains a resumable, spec-scoped work plane that later agents can trust without chat memory?

## Evidence Summary

### The Current Work Plane Is A Mixed Model, Not A Contract

- `.ai-engineering/specs/spec.md` is treated as the active spec buffer.
- `.ai-engineering/specs/plan.md` is treated as the active plan buffer.
- `.ai-engineering/specs/_history.md` is used as the coarse closure trail.
- Spec-specific artifacts such as `spec-117-hx-01-control-plane-normalization.md` and `plan-117-hx-01-control-plane-normalization.md` already exist, but they are not the runtime authority.
- Autonomous flows also carry resumable information in separate run-oriented artifacts.

The repo therefore already has multiple resumable-state models, but none of them is authoritative for the full feature lifecycle.

### Global Buffers Allow Undetected Drift

- The current repo already shows a real mismatch: `spec.md` points at `spec-117`, while `plan.md` still holds a completed `spec-116` plan.
- Current runtime checks accept that state because they do not prove that the plan belongs to the active spec.
- Idle vs active state is encoded partly through literal placeholder prose such as `No active spec` and `No active plan`, not through typed work-plane state.

This means the framework can report coherence while the active work context is actually inconsistent.

### Task State Is Not First-Class

- Progress is derived from markdown checkboxes and frontmatter counts.
- Closure is inferred from `_history.md` rows or `done.md` in spec directories.
- There is no authoritative task identity, dependency model, write-scope model, blocked state, handoff artifact, or evidence artifact.

The current plan surfaces answer `how many boxes are checked`, but not `what exact task is active, who owns it, what it may write, what it depends on, or what evidence proves it is done`.

### Runtime And Validation Paths Hard-Code The Singleton Buffer Model

- CLI flows in `src/ai_engineering/cli_commands/spec_cmd.py` assume one specs root plus one active `plan.md`.
- Reset and closure logic in `src/ai_engineering/maintenance/spec_reset.py` wipe or replace the singleton buffers instead of finalizing one spec-scoped work plane.
- `src/ai_engineering/verify/service.py`, `src/ai_engineering/policy/orchestrator.py`, `src/ai_engineering/policy/gate_cache.py`, `src/ai_engineering/state/observability.py`, `src/ai_engineering/state/audit.py`, validators, work-item sync, and PR description generation all assume the same global active-buffer shape.

`HX-02` is therefore not a documentation feature. It is the work-plane authority feature for CLI, runtime, validation, telemetry, and orchestration.

### The Reference Harness Confirms The Direction, Not The Literal Shape

Portable patterns from the reference harness:

- file-backed resumable state
- compact handoffs that point to artifacts instead of reusing chat as the source of truth
- explicit split between mutable current state and append-only history
- executable validation as proof of task state

Adaptations required for ai-engineering:

- spec-scoped work planes instead of one global ledger
- richer task metadata: owner role, dependencies, write scope, evidence refs, blocked reasons
- compatibility with existing spec CLI, work-item flows, and autonomous run surfaces
- a real topology for `explore`, `plan`, `build`, `review`, `verify`, and `guard`, not a simplified three-role model

### Build Readiness Must Become A Work-Plane Decision

- The current repo does not have one executable rule that says when a feature may move from planning to build.
- The user requirement for this refactor is stricter than the legacy runtime: every `HX` must complete `explore -> spec -> plan` before build is allowed.
- Because the program is portfolio-coupled, the first build wave also needs the broader roadmap and dependency chain to be explicit, not implied from chat or memory.

`HX-02` must therefore make build readiness derivable from durable work-plane artifacts rather than from conversational agreement.

## High-Signal Findings

1. The current active-buffer model is already unsound in production terms because spec and plan can diverge without detection.
2. A task ledger is necessary, but only as part of a wider work-plane contract: active pointer, current summary, history summary, handoffs, evidence, and compatibility views.
3. The runtime needs an active-work-plane resolver so callers stop hard-coding `spec.md` and `plan.md` as the only truth.
4. `HX-02` must preserve compatibility for install/bootstrap and CLI surfaces while replacing the authority model under them.
5. Build cannot start safely for this program until work-plane readiness is explicit at both feature level and portfolio sequencing level.

## Recommended Decision Direction

### Preferred Work-Plane Direction

- Introduce one spec-scoped work-plane root per active feature.
- Add one authoritative active pointer that resolves the currently active work plane.
- Treat global `spec.md` and `plan.md` as compatibility or generated views during migration, not as the durable source of execution truth.

### Preferred Task Direction

- Create a first-class task ledger with task id, status, owner role, dependencies, write scope, handoff refs, evidence refs, and blocked metadata.
- Keep long logs and raw command output outside the task ledger; the ledger should reference evidence, not absorb it.
- Separate mutable current summary from append-only history summary.
- The first concrete runtime artifact layout can stay intentionally small: `task-ledger.json`, `current-summary.md`, `history-summary.md`, `handoffs/`, and `evidence/` under the active work-plane root.

### Preferred Runtime Direction

- Introduce a shared active-work-plane resolver used by CLI, verify, observability, audit, work-items, PR generation, validators, and policy gating.
- Make build readiness and plan/spec coherence derive from the resolver and task ledger rather than from placeholder prose or checkbox summaries.
- Expand cache invalidation and validator inputs so ledger, summaries, and active-pointer state are part of the authority model.

## Migration Hazards

- Preserving legacy `spec.md` and `plan.md` behavior too long can leave competing truths alive.
- Removing the singleton buffers too early will break install/bootstrap, tests, and user-facing CLI flows.
- Over-designing the ledger can create a second accidental architecture if schema, templates, and runtime consumers do not converge on one contract.
- Wiring orchestrators before validator coverage exists can create false confidence and stale cache reuse.
- Updating runtime consumers without template parity will split source-repo and installed-workspace behavior again.

## Scope Boundaries For HX-02

In scope:

- spec-scoped work-plane contract
- active pointer and active-work-plane resolver
- task-ledger schema and lifecycle model
- handoff, evidence, current, and history artifact model
- compatibility views for `spec.md` and `plan.md`
- validator, CLI, cache, observability, work-item, and PR integration for the new contract
- explicit build-readiness contract for this refactor program

Out of scope:

- control-plane authority normalization from `HX-01`
- mirror-local reference cleanup from `HX-03`
- harness kernel unification from `HX-04`
- event vocabulary normalization from `HX-05` beyond the minimum work-plane hooks needed here
- runtime-core extractions from `HX-08`, `HX-09`, or `HX-10`

## Open Questions

- Should the authoritative task ledger be YAML, JSON, or another machine-readable format layered under markdown compatibility views?
- Should `done.md` survive as a generated closure view, or be retired entirely once current/history summaries and evidence refs exist?
- `HX-02` now anchors the active pointer at `.ai-engineering/specs/active-work-plane.json` with a project-relative `specsDir` field; the remaining question is whether `HX-05` should relocate that state under a wider work-plane/state surface while preserving compatibility.
- The first compatibility CLI seams now exist for activation, `spec list`, `spec verify`, and reset/close; the remaining question is which work-item and PR-generation surfaces should move next.
- What exact portfolio-wide build-start rule should be encoded as a deterministic validator versus a documented orchestration rule?

## Source Artifacts Consulted

- `.ai-engineering/specs/spec.md`
- `.ai-engineering/specs/plan.md`
- `.ai-engineering/specs/_history.md`
- `.ai-engineering/specs/spec-117-hx-01-control-plane-normalization.md`
- `.ai-engineering/specs/plan-117-hx-01-control-plane-normalization.md`
- `.ai-engineering/specs/spec-117-harness-engineering-task-catalog.md`
- `.ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md`
- `.ai-engineering/specs/spec-117-orchestrator-operating-prompt.md`
- `src/ai_engineering/cli_commands/spec_cmd.py`
- `src/ai_engineering/maintenance/spec_reset.py`
- `src/ai_engineering/verify/service.py`
- `src/ai_engineering/policy/orchestrator.py`
- `src/ai_engineering/policy/gate_cache.py`
- `src/ai_engineering/state/observability.py`
- `src/ai_engineering/state/audit.py`
- `src/ai_engineering/validator/categories/file_existence.py`
- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `src/ai_engineering/work_items/service.py`
- `src/ai_engineering/vcs/pr_description.py`
- `/Users/soydachi/repos/ejemplo-harness-subagentes`