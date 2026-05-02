---
spec: spec-117-hx-06
title: Multi-Agent Capability Contracts
status: done
effort: large
---

# Spec 117 HX-06 - Multi-Agent Capability Contracts

## Summary

ai-engineering already has a real multi-agent execution topology, but its capability contract is split between manifest registry data, canonical skill and agent prose, provider-specific sync metadata, and shallow runtime projections. Write permissions, tool permissions, provider compatibility, delegation, and topology role are mostly described by convention rather than enforced in one machine-readable model. This feature adds explicit capability cards, write-scope taxonomy, tool-scope policy, topology classification, and deterministic integration gates so the system can block unsafe parallelism and invalid agent/task combinations while staying thin over the `HX-02` work plane and the `HX-03` mirror contract.

## Goals

- Define one machine-readable capability contract for first-class agents and skills.
- Model mutation authority explicitly across read, advise, spec-write, code-write, state-write, git-write, board-write, and telemetry-emit classes.
- Add a write-scope taxonomy and tool-scope policy strong enough to block invalid agent/task/tool combinations.
- Generalize provider compatibility and topology role into a cross-provider contract rather than prompt-only exceptions.
- Make task-packet acceptance deterministic by validating capability card, write scope, tool scope, dependency edges, and required handoffs against the `HX-02` work plane.
- Keep optimization heuristics advisory when they are important but not yet modeled explicitly.
- Preserve the public/internal boundary and mirror-local rules established by `HX-03` rather than redefining them.

## Non-Goals

- Replacing the `HX-02` task-ledger or work-plane contract.
- Owning mirror-family inventory, provenance, or public/internal mirror filtering from `HX-03`.
- Solving full kernel-wide retry, loop detection, or failure reporting from `HX-04`.
- Normalizing state-plane event vocabulary from `HX-05` beyond the minimum capability signals needed here.
- Turning every planning or token-efficiency heuristic into a hard gate before it is modeled clearly enough.

## Decisions

### D-117-30: Capability authority is explicit and machine-readable

`HX-06` introduces one capability card per first-class agent or skill. Capability cards become the authoritative contract for mutation class, tool scope, provider compatibility, topology role, handoff expectations, and escalation semantics.

**Rationale**: current capability meaning is spread across prompt prose, provider metadata, and stale projections, which prevents deterministic validation.

### D-117-31: Capability contracts extend the `HX-02` work plane; they do not replace it

The work plane continues to own ledger tasks, handoffs, evidence, current/history summaries, and active pointer state. `HX-06` adds the rule layer that decides whether a capability may accept a given task packet derived from that work plane.

**Rationale**: duplicating task-ledger semantics here would recreate the same split-authority problem that `HX-02` exists to remove.

### D-117-32: Mutation authority is modeled by plane and action class

The capability contract must distinguish at minimum read, advise, spec-write, code-write, state-write, git-write, board-write, and telemetry-emit authority, and it must express allowed artifact classes and write scopes in machine-readable form.

**Rationale**: the current repo conflates source-code writes, spec writes, state mutation, VCS mutation, and system-side telemetry emission.

### D-117-33: Tool scope, provider compatibility, and topology role are first-class contract fields

Capability cards must declare allowed tool categories, provider compatibility or degradation requirements, and topology role such as public-first-class, orchestrator, leaf, internal specialist, or system actor.

**Rationale**: today those signals exist, but they live in different surfaces and are not consistent enough to validate delegation or host compatibility safely.

### D-117-34: `HX-06` blocks invalid capability/task combinations deterministically and keeps broader heuristics advisory

The feature must block at least missing capability ownership, disallowed tool requests, illegal write classes, overlapping serialized write scopes, missing dependency or handoff edges, and provider-incompatible execution. Broader heuristics such as overly broad-but-legal scopes, semantic coupling risk, degraded host quality, or token posture remain advisory until modeled more explicitly.

**Rationale**: deterministic gates should protect correctness; softer planning heuristics should not masquerade as hard truth before the system can justify them.

### D-117-35: `HX-06` consumes the `HX-03` public/internal boundary rather than redefining mirrored surface ownership

Public versus internal status is a capability contract field, but mirror-family inventory, provenance, and provider-local mirror rendering remain owned by `HX-03`.

**Rationale**: `HX-03` already owns the mirror contract. `HX-06` should use that boundary to prevent orchestration drift, not create a second mirror-governance model.

## Risks

- **Provider-regression risk**: normalizing capability cards without preserving provider-specific enrichments could break current host-specific behavior. **Mitigation**: capture provider compatibility and degraded-mode semantics explicitly before cutover.
- **Authority duplication risk**: capability cards, task packets, and mirror/state ownership can drift if responsibilities overlap. **Mitigation**: keep `HX-06` thin over `HX-02` and `HX-03` and make derived projections downstream only.
- **Over-gating risk**: turning too many heuristics into hard blocks too early can stall useful work. **Mitigation**: keep only correctness-critical gates deterministic in this slice.
- **Compatibility-test risk**: current tests are shallow relative to the new contract. **Mitigation**: add compatibility shims and failing coverage before tightening runtime enforcement.
- **Topology drift risk**: public registry and effective execution graph differ today. **Mitigation**: declare topology role explicitly and keep internal specialists out of peer public capability counts.

## Deferred Cleanup From HX-02

- `HX-02` now gives task packets one authoritative ledger with dependencies, handoffs, evidence, and write scopes, but it does not decide whether a capability may accept that task. Deterministic capability validation, illegal mutation-class blocking, and tool-scope enforcement remain work for `HX-06`.
- Transitional capability projections such as `framework-capabilities.json` remain advisory until `HX-06` formalizes capability cards and derived projections. This follow-on cleanup must make the relationship explicit so the work plane does not inherit a second capability authority by accident.
- The compatibility `spec.md` and `plan.md` views preserved by `HX-02` should remain inputs to task-packet derivation, not parallel capability authorities. `HX-06` must consume the work plane contract rather than duplicating it.

## Deferred Cleanup From HX-03

- `HX-03` now enforces provider compatibility, public/internal topology boundaries, and generated/manual surface distinctions through mirror metadata and helper logic. `HX-06` still needs to lift those policy signals into machine-readable capability contracts so agent/task validation can reason about mirror-mutating work without depending on mirror-specific prompt conventions.
- Any task-packet gate for agents that edit generated overlays, manual instruction families, or provider-local mirrors must consume the `HX-03` mirror contract rather than recreating a second surface inventory here.

## Deferred Cleanup From HX-01

- `HX-01` explicitly reclassified `framework-capabilities.json` as a derived projection but left it in place as a transitional capability view. `HX-06` owns the capability-card cutover that decides whether that projection is regenerated, renamed, or retired.
- `HX-01` also stops at manifest and validator ownership rules for constitutional, workspace-charter, and generated control-plane surfaces. `HX-06` owns any machine-readable capability policy that determines which agents or skills may mutate those surfaces and under what write-scope or tool-scope constraints.

## Capability Cutover Status

- `framework-capabilities.json` is now regenerated from manifest metadata plus the canonical capability-card builder, including `capabilityCards` for first-class skills and agents.
- `manifest-coherence` validates the committed framework-capabilities projection against the builder, validates capability-card coverage for manifest skills and first-class agents, and validates active task packets against capability authority.
- Task packets consume `HX-02` work-plane fields for owner, write scope, dependencies, handoffs, and optional execution metadata such as `mutationClasses`, `toolRequests`, and `provider`.
- Specialist reviewer and verifier agents remain internal runtime participants. Generated mirrors carry provenance and live under provider-local `internal/` roots; leaked specialist names classify as non-public `internal-specialist` capabilities that cannot accept task packets.

## Deferred Policy Envelope

- `HX-04` still owns kernel-wide retry loops, failure reporting, loop detection, and recovery semantics. `HX-06` only rejects invalid capability/task packets before execution begins.
- `HX-05` still owns canonical event vocabulary, reducer semantics, and deeper observability lifecycle normalization. `HX-06` only models the minimum capability signals needed for task acceptance and projection checks.
- `HX-07` owns context-budget enforcement, token posture scoring, and learning-loop refinement. `HX-06` keeps token posture and broad-but-legal scope warnings advisory.
- Worktree isolation remains deferred until a later scheduler or execution-kernel slice can model concurrent write ownership precisely. `HX-06` blocks explicit illegal write classes and duplicate active write scopes but does not create isolated worktrees.
- Semantic coupling risk remains advisory until a later planning slice has a reliable dependency graph that can distinguish legitimate broad coordination from accidental coupling.

## References

- doc: .ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts-explore.md
- doc: .ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md
- doc: .ai-engineering/specs/spec-117-hx-03-mirror-local-reference-model.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-refactor-roadmap.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-feature-portfolio.md
- doc: .ai-engineering/specs/spec-117-harness-engineering-task-catalog.md
- doc: .ai-engineering/manifest.yml
- doc: scripts/sync_command_mirrors.py
- doc: docs/copilot-subagents.md
- doc: src/ai_engineering/skills/service.py
- doc: src/ai_engineering/cli_commands/skills.py
- doc: src/ai_engineering/validator/categories/skill_frontmatter.py
- doc: src/ai_engineering/state/observability.py
- doc: .github/hooks/hooks.json

## Open Questions

- Should worktree isolation become a hard requirement for all concurrent write tasks or only for high-collision runtime families?
- How granular should the write-scope taxonomy be before it becomes too expensive to maintain?
- Which provider features are minimum required for compatible execution versus only degraded execution?
- Should any token-budget rule become deterministic in `HX-06`, or should all token posture stay advisory until `HX-07`?
- Should artifact ownership live only in capability cards and task packets, or also in a shared registry reused by later state or mirror slices?