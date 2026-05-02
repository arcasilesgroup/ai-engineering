spec: spec-117
title: Harness Engineering Root Refactor Program
status: done
effort: large
---

# Spec 117 - Harness Engineering Root Refactor Program

## Summary

ai-engineering needs more than cleanup. The current framework has good seams, but its control surfaces, task state, mirrors, runtime services, validators, telemetry, and docs have grown into an accidental architecture: two constitutions in active circulation, two gate/control planes, duplicated hook/runtime logic, stale mirror references, a flat state directory that mixes durable truth with residue, and oversized modules/tests that obscure ownership. This spec turns spec-117 into a full-program root refactor of the whole framework through a harness-engineering lens.

The target is a production-ready local-first agent harness for the full ai-engineering repo: every durable file has a reason to exist, canonical surfaces are few and explicit, multi-agent work is resumable and file-backed, deterministic controls are authoritative, mirrors are generated and provider-local, and large runtime packages are rewritten only after new seams and tests are in place.

## Closure Status

Spec 117 is closed. `HX-01` through `HX-12` are complete in the task ledger, the deferred guard reviews were reconciled in the final end-of-implementation review pass on 2026-05-02, and the remaining stale plan/spec metadata has been normalized to the terminal `done` status.

## Goals

- Reframe the entire repository around explicit harness layers, not only instruction cleanup.
- Define a target artifact model that separates control plane, work plane, durable state, runtime residue, and learning funnel.
- Make it safe to delete, merge, or rewrite any accidental surface once parity and verification exist.
- Establish one authoritative harness kernel for checks, gate artifacts, failure output, and loop handling.
- Add a spec-scoped task ledger and handoff system that supports multi-session and multi-agent execution.
- Rewrite the instruction and mirror system so provider surfaces are generated, concise, and free of provider-cross references.
- Codify clean code, clean architecture, SOLID, DRY, KISS, YAGNI, TDD, SDD, and harness-engineering principles in canonical framework docs and review checklists.
- Reduce context tax while increasing quality, determinism, and production readiness.

## Non-Goals

- No production implementation happens in this spec.
- No blind big-bang cutover of the whole framework in one rewrite.
- No cosmetic file splitting or doc slimming without stronger architectural boundaries or better controls.
- No weakening of spec-driven development, TDD, dual-plane security, generated mirrors, or audit-chain guarantees.
- No external SaaS-first orchestration, vector-store dependency, or service mesh requirement in v1.
- No manual maintenance of provider mirrors or duplicate governance surfaces after the refactor lands.

## Decisions

### D-117-01: Run a seam-guided root refactor, not a conservative tidy-up

The program explicitly allows selective rewrites, deletions, and relocations across runtime, skills, agents, state, docs, and templates when the current shape is accidental and replacement seams are clearer.

**Rationale**: exploration found good foundations but also structural duplication: dual constitutions, dual gate engines, template/runtime logic duplication, stale mirror references, and flat state sprawl.

### D-117-02: Preserve only the seams already proven useful

The following seams are worth carrying forward unless later evidence disproves them:

- CLI bootstrap and presentation boundary.
- VCS protocol and provider adapters.
- Release orchestration service shape.
- Phase/pipeline execution contract from installer/doctor.
- Manifest as machine-readable control source.
- Append-only event stream as audit substrate.

**Rationale**: these are the few areas where the codebase already shows coherent abstractions instead of accidental accumulation.

### D-117-03: Introduce explicit artifact planes

The refactor will classify durable artifacts into five planes:

- Control plane: constitution, manifest, ownership rules, canonical overlays.
- Work plane: spec-scoped spec/plan/task ledger/handoffs/evidence.
- Durable state plane: decisions, audit/event stream, install/runtime state that must survive.
- Runtime residue plane: caches, last-run findings, generated diagnostics, temporary operational residue.
- Learning funnel: lessons, instincts, proposals, optional notes.

**Rationale**: the current repo mixes all five lifecycles inside flat top-level directories, which hides ownership and complicates cleanup.

### D-117-04: Build one authoritative harness kernel

Gate orchestration, mode resolution, check registration, artifact schemas, failure output, retry policy, and loop detection must converge on one kernel contract.

**Rationale**: today the repo splits verification authority across legacy gates, the newer orchestrator, validator categories, verify services, hooks, and CI. Strong coverage exists, but authority is diffuse.

### D-117-05: Make the work plane file-backed and resumable

Spec execution will use a spec-scoped task ledger, predictable handoff files, history/current summaries, and evidence artifacts.

**Rationale**: this is the highest-leverage import from the reference harness and the prerequisite for safe multi-agent work.

### D-117-06: Rewrite the instruction and mirror system around local references and generated provenance

Canonical surfaces stay singular; generated mirrors must carry explicit provenance and cannot depend on `.claude`-specific paths from non-Claude runtimes.

**Rationale**: exploration found stale counts, broken cross-links, and provider-local mirror files that still reference Claude-only paths.

### D-117-07: Codify engineering principles as contracts, not slogans

Clean Code, Clean Architecture, SOLID, DRY, KISS, YAGNI, TDD, SDD, and harness engineering will be written into canonical docs, review rubrics, and where practical deterministic checks.

**Rationale**: the user explicitly wants these standards written down, and they only matter if later agents can apply them consistently.

### D-117-08: Parallelism is governed by write ownership and topology, not optimism

Tasks may run in parallel only when write scopes are disjoint and dependency edges are explicit; otherwise they serialize.

**Rationale**: the repo already has multiple orchestrators and specialist agents. What it lacks is a machine-readable collision model.

### D-117-09: Replacement first, deletion second

Legacy surfaces may be deleted only after the replacement path has parity, tests, and rollback clarity.

**Rationale**: the goal is a cleaner and stronger framework, not a smaller but weaker one.

### D-117-10: Keep v1 local-first and repo-native

The root refactor uses local files, local git, existing CLI entry points, and IDE-host subscriptions before any optional external adapters.

**Rationale**: this matches the Constitution and keeps the new harness testable and adoptable.

## Engineering Principles

- Clean Architecture: core contracts must depend inward; CLI, hooks, templates, and provider adapters stay at the edge.
- Clean Code: small explicit units, one reason to change, obvious ownership, and no hidden shadow contracts.
- SOLID: especially single responsibility, interface segregation, and dependency inversion across runtime services and adapters.
- DRY and KISS: remove duplicated control planes and duplicated runtime/template logic before adding new abstractions.
- YAGNI: do not add new registries, docs, or orchestration modes without a concrete gap and a runtime or validation consumer.
- TDD: runtime behavior changes start from failing tests in the owned contract slice.
- SDD: every implementation spec must preserve clear traceability from spec to plan to task ledger to evidence.
- Harness Engineering: repeated failures become structural controls, not prompt folklore.

## Risks

- **Program breadth**: the refactor touches runtime, state, mirrors, docs, validators, tests, and orchestration. **Mitigation**: split into follow-on specs with disjoint write scopes and hard exit gates.
- **Big-bang temptation**: a rewrite mindset could destroy stable seams that should be preserved. **Mitigation**: force replacement-by-slice and keep preserved seams explicit.
- **Premature runtime cleanup**: splitting files before control-plane and work-plane contracts exist would be cosmetic. **Mitigation**: runtime rewrites are later-wave and blocked on task ledger, kernel, and state normalization.
- **Mirror/provider regressions**: non-Claude installs can break if provider-local references are not fixed early. **Mitigation**: repair mirror-local references, generated provenance, and provider-only install tests before large instruction cleanup.
- **Validation sequencing races**: mirror validation and event-chain validation can produce false failures when run in the wrong order. **Mitigation**: mirror sync completes before mirror validation, and event-emitting validations run sequentially to protect the audit chain.
- **Documentation drift**: docs can become a second source of truth again if rewritten too early. **Mitigation**: docs and migration surfaces trail implemented contracts and generated inventories.
- **User-change collision**: the worktree already contains unrelated user or automation changes. **Mitigation**: later implementation specs must inspect dirty state before editing shared surfaces.

## References

- doc: .ai-engineering/specs/spec-117-harness-engineering-context-pack.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: https://notebooklm.google.com/notebook/858dc737-739f-4026-a900-6ab641be936b
- doc: /Users/soydachi/repos/ejemplo-harness-subagentes
- doc: CONSTITUTION.md
- doc: AGENTS.md
- doc: .ai-engineering/manifest.yml
- doc: .ai-engineering/state/decision-store.json
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/contexts/knowledge-placement.md
- doc: .ai-engineering/contexts/operational-principles.md
- doc: .ai-engineering/specs/spec-115-cross-ide-entry-point-governance-and-engineering-principles-standard.md
- doc: .ai-engineering/specs/spec-116-framework-knowledge-consolidation-canonical-placement-and-governance-cleanup.md

## Open Questions

- Should the workspace-level `.ai-engineering/CONSTITUTION.md` be deleted, renamed, or reduced to a non-constitutional project-charter role?
- Should worktree isolation be mandatory for build tasks touching shared runtime surfaces, or only for high-collision slices?
- Do we want strict numeric budgets for instruction surfaces, or score-based budgets with explicit waivers?
- Should the first implementation wave be shipped as one combined control-plane/work-plane spec, or as two back-to-back specs?
- Which early runtime extractions deserve protection as stable contracts: manifest repository, reconciler engine, thin CLI adapters, or asset/runtime split?

## Approach Options

### Approach A: Seam-Guided Root Refactor

Create a new target artifact model and harness kernel, migrate subsystems toward it in bounded slices, then delete replaced surfaces.

- **Pros**: deep enough to fix the real problems while preserving proven seams.
- **Cons**: requires discipline to avoid carrying both old and new systems too long.
- **Effort**: very large.
- **Risk**: medium.

### Approach B: Big-Bang New Framework

Build a new harness core and port the whole repo to it in one program cutover.

- **Pros**: maximum conceptual cleanliness.
- **Cons**: highest migration risk, hardest rollback, easiest way to lose operational knowledge.
- **Effort**: extreme.
- **Risk**: very high.

### Approach C: Conservative Incremental Hardening

Keep current boundaries, add more validators and docs, and avoid structural rewrites.

- **Pros**: lowest near-term disruption.
- **Cons**: leaves the accidental architecture largely intact and underdelivers on the user's goal.
- **Effort**: large.
- **Risk**: medium because it risks cosmetic success with structural failure.

## Recommendation

Adopt Approach A. This is a full-framework root refactor, but it should be seam-guided, evidence-driven, and sliced into follow-on implementation specs. The program should start by fixing artifact/control/work planes, then unify the harness kernel, then rewrite runtime subsystems behind those new contracts, and only then remove legacy surfaces aggressively.

## Roadmap Summary

The detailed feature/task breakdown lives in `.ai-engineering/specs/spec-117-harness-engineering-task-catalog.md`, and the future implementation-spec portfolio lives in `.ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md`. At program level, the refactor has eight tracks:

1. **Control plane normalization**: constitutions, manifest ownership, artifact taxonomy, canonical/derived separation.
2. **Work plane normalization**: spec-scoped directories, task ledger, handoffs, evidence, current/history summaries.
3. **Instruction and mirror architecture rewrite**: slimmer roots, local references, generated provenance, public/internal agent split.
4. **Harness kernel unification**: one gate engine, one failure contract, one retry/loop model, one harness-check command.
5. **State and observability normalization**: durable state vs residue, unified event vocabulary, task traces, scorecards.
6. **Multi-agent execution and context system**: capability cards, tool scopes, topology classification, context packs, memory lifecycle.
7. **Runtime core extraction and selective rewrites**: manifest/state repository, reconciler engine, thin CLI adapters, asset/runtime split, large module splits.
8. **Verification, standards, docs, and deletion**: eval scenario packs, test reshape, engineering-principles canon, migration docs, legacy removal.
