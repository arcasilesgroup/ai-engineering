# HX-07 Explore - Context Packs and Learning Funnel

This artifact captures the evidence gathered before writing the feature spec for `HX-07`.

## Scope

Feature: `HX-07` Context Packs and Learning Funnel.

Question: what must change so multi-agent work resumes from deterministic context packs and compact handoffs instead of chat reconstruction, while lessons, instincts, proposals, and notes remain a governed funnel rather than a second source of truth?

## Evidence Summary

### Current Context Surfaces Are Split Across Several Memory Types

- Working memory is still effectively the shared `spec.md` and `plan.md` buffer model.
- Episodic memory is split across `_history.md`, framework events, instinct observations, and session residue such as strategic compact files.
- Semantic memory is spread across decision store, lessons, contexts, and optional notes.
- Procedural memory lives in constitutions, agent and skill contracts, and shared execution-kernel prompts.
- Additional run-oriented file-backed models already exist in `ai-run` and `ai-autopilot` flows.

The repo therefore has many memory-like surfaces, but not one deterministic context-pack contract.

### Bootstrap Context Exists, But Task Context Selection Is Mostly Convention

- Session bootstrap is partly explicit through manifest-configured context files and `ai-start`.
- After bootstrap, task context is reconstructed by convention per skill or agent rather than by a single pack generator.
- Observability can record declared context sets, but that is not equivalent to generating one canonical task pack.

This means the system can say what should have been loaded without owning one reproducible bundle of what actually must be loaded.

### Handoff Rules Exist, But They Are Fragmented And Mostly Advisory

- Shared execution-kernel instructions already push artifact-based handoffs.
- `ai-run` and `ai-autopilot` require file-backed phase handoff in practice.
- Strategic compacting exists as a hook-based advisory signal.
- The spec-117 task catalog already defines handoff and compaction expectations, but there is no single enforced schema.

The repo therefore has the right direction, but not one enforced handoff sufficiency contract.

### The Learning Funnel Exists, But Its Lifecycle Is Not Yet Tied To The Work Plane

- Knowledge placement rules exist.
- Skills such as `ai-instinct`, `ai-learn`, `ai-note`, and `ai-create` already consume or produce learning artifacts.
- Lessons, instincts, proposals, and notes exist, but their promotion rules are not tied directly to task packets, task evidence, or context-pack generation.

Without stronger boundaries, the funnel can become a soft second source of truth instead of a governed promotion path.

### `HX-07` Must Consume `HX-02`, `HX-05`, And `HX-06`, Not Replace Them

- `HX-02` owns task identity, lifecycle state, dependencies, handoffs, evidence, and current/history summaries.
- `HX-05` owns event vocabulary, audit chain, and task traces.
- `HX-06` owns capability cards, tool scopes, write scopes, and topology rules.
- `HX-07` should consume those surfaces and generate deterministic context packs and learning-funnel transitions from them.

If `HX-07` redefines task state, traces, or capability scope, it will recreate the same split-authority problem this program is eliminating.

## High-Signal Findings

1. The highest-value boundary for `HX-07` is `task packet in, deterministic context pack out`.
2. Prior context packs should be convenience artifacts at most, never authority for future packs.
3. Learning artifacts must stay advisory or promotable until they are moved into a canonical home.
4. Compaction must be reference-first: large outputs should be linked, not copied inline.
5. Handoff sufficiency should be deterministic enough that a later agent can resume from disk alone.

## Recommended Decision Direction

### Preferred Context-Pack Direction

- Generate context packs deterministically from authoritative control-plane and work-plane inputs.
- Classify pack inputs explicitly as authoritative, derived, optional advisory, or excluded residue.
- Persist packs under the owning work plane as spec-local artifacts or regeneration outputs.
- Do not let packs depend on chat memory or on prior packs for correctness.

### Preferred Handoff Direction

- Define one minimum sufficiency contract: task id, exact objective, authoritative refs, unresolved blockers or next action, and evidence or verification refs.
- Enforce reference-first compaction and bounded inline content.
- Validate that handoffs reference the active work plane rather than duplicating task state fields.

### Preferred Learning-Funnel Direction

- Keep lessons, instincts, proposals, and notes classified as advisory or promotable artifacts.
- Make promotion one-way into canonical homes with provenance/backlinks.
- Keep decision store reserved for formal decisions and live risks, not generic learnings.

## Migration Hazards

- Shared-buffer context reconstruction can keep appearing to work even while semantically drifting, as already shown by active spec/plan mismatch.
- Learning artifacts can silently become active runtime guidance if promotion rules remain soft.
- Persisted packs can become stale peer authorities if regeneration and classification rules are weak.
- If `HX-07` absorbs task-state or trace ownership, it will duplicate `HX-02` or `HX-05`.
- Token-efficiency guidance will remain folklore if it is not grounded in pack and handoff structure.

## Scope Boundaries For HX-07

In scope:

- deterministic context-pack generation
- pack-manifest and source classification rules
- handoff compaction and sufficiency contract
- learning-funnel lifecycle and promotion boundaries
- validation hooks for pack reproducibility and handoff quality

Out of scope:

- task-state authority from `HX-02`
- event vocabulary and trace ownership from `HX-05`
- capability and tool-scope authority from `HX-06`
- broader eval architecture from `HX-11`

## Open Questions

- What exact pack-manifest schema and storage location should become canonical?
- Should trace slices enter packs directly or only as referenced provenance?
- Should hard token budgets become blocking in this slice, or only structural ceilings such as item count and inline size?
- What is the compensating path when pack generation succeeds but trace append fails?
- Can notes promote directly, or only through proposal or lesson stages?

## Source Artifacts Consulted

- `.ai-engineering/specs/spec.md`
- `.ai-engineering/specs/plan.md`
- `.ai-engineering/specs/_history.md`
- `.ai-engineering/state/framework-events.ndjson`
- `.ai-engineering/state/instinct-observations.ndjson`
- `.ai-engineering/state/strategic-compact.json`
- `.ai-engineering/state/decision-store.json`
- `.ai-engineering/LESSONS.md`
- `.ai-engineering/instincts/**`
- `.ai-engineering/contexts/knowledge-placement.md`
- `src/ai_engineering/cli_commands/spec_cmd.py`
- `src/ai_engineering/maintenance/spec_reset.py`
- `src/ai_engineering/state/observability.py`
- `.github/skills/ai-start/SKILL.md`
- `.github/skills/ai-dispatch/SKILL.md`
- `.github/skills/ai-instinct/SKILL.md`
- `.github/skills/ai-learn/SKILL.md`
- `.github/skills/ai-note/SKILL.md`
- `.github/skills/_shared/execution-kernel.md`
- `.github/skills/ai-run/**`
- `.claude/agents/ai-autopilot.md`
- `.ai-engineering/specs/spec-117-hx-02-work-plane-and-task-ledger.md`
- `.ai-engineering/specs/spec-117-hx-05-state-plane-and-observability-normalization.md`
- `.ai-engineering/specs/spec-117-hx-06-multi-agent-capability-contracts.md`