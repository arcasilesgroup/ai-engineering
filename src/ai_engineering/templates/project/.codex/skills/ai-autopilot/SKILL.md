---
name: ai-autopilot
description: "Delivers large multi-concern specs and backlog runs autonomously: decomposes specs into sub-specs (or normalizes work items into a backlog DAG), deep-plans with parallel agents, builds a dependency DAG, implements in waves, runs quality convergence loops (verify+guard+review), delivers via PR. Trigger for 'implement spec-NNN end to end', 'autopilot this', 'autonomous delivery', 'decompose and ship', 'run the backlog', 'execute these GitHub issues', 'process the sprint backlog'. Invocation is the approval gate. Not for small or single-concern tasks; use /ai-build instead. Not for ambiguous requirements; use /ai-brainstorm first."
effort: max
argument-hint: "'implement spec-NNN'|--backlog --source <github|ado|local>|--resume|--no-watch"
tags: [orchestration, autonomous, multi-spec, backlog, pipeline, execution, dag, transparency]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-autopilot/SKILL.md
edit_policy: generated-do-not-edit
---


# Autopilot v2

## Purpose

Autonomous execution of large approved specs via a 6-phase pipeline. Decomposes a spec into N focused sub-specs, deep-plans each with parallel agents, orchestrates a dependency-aware execution DAG, implements in waves, converges on quality through iterative verify+guard+review loops, and delivers the full changeset via PR with a transparency report. Execution is not complete until sub-spec work converges into a final delivery PR against protected main. One invocation, zero interruptions, full disclosure.

## When to Use

- Spec has >= 3 independent concerns or touches >= 10 files
- After `/ai-brainstorm` approval (spec.md exists and is not a placeholder)
- Backlog runs with `--backlog --source <github|ado|local>` to absorb GitHub issues, Azure Boards items, or markdown task lists into the DAG (D-127-12; replaces the legacy `/ai-run` skill)
- When manual `/ai-build` would overflow context within a single session
- Multi-concern work that benefits from parallel intelligence gathering and DAG-driven execution

## When NOT to Use

- < 3 concerns -- use `/ai-build` directly (autopilot overhead not justified)
- Draft or unapproved spec -- run `/ai-brainstorm` first
- Need human review between phases -- use `/ai-build` with manual checkpoints
- Cross-repo changes -- coordinate manually
- Data migrations with destructive DDL -- require explicit user approval per step

## Process

**Step 0 — Validate**: confirm `.ai-engineering/specs/spec.md` is not a placeholder (else STOP and report `/ai-brainstorm`). On `--resume`, read `.ai-engineering/runtime/autopilot/manifest.md` and re-enter at the Resume Protocol. Load contexts per `.ai-engineering/contexts/stack-context.md` and pass paths (not content) to subagents. plan.md is not required — Phase 2 agents generate their own.

**Step 1 — DECOMPOSE** (`handlers/phase-decompose.md`): extract N independent concerns; abort if N<3 (recommend `/ai-build`); write sub-spec dirs and the execution manifest.

**Step 2 — DEEP PLAN** (`handlers/phase-deep-plan.md`): dispatch explore+plan agents in parallel; each enriches `sub-NNN/spec.md` (Exploration) + `plan.md` (checkbox tasks with exports/imports). Failed agents retry once → mark `plan-failed`.

**Step 3 — ORCHESTRATE** (`handlers/phase-orchestrate.md`): build the file-overlap matrix and import-chain graph from Phase-2 evidence (never from spec text alone); construct the wave-assigned DAG; merge unresolvable conflicts.

**Step 4 — IMPLEMENT** (`handlers/phase-implement.md`): per-wave kernel from `.codex/skills/_shared/execution-kernel.md`. Dispatch build agents per sub-spec in parallel within a wave; run build-verify-review per task; collect Self-Reports + per-wave commits. Cascade-block dependents of failed sub-specs.

**Step 5 — QUALITY LOOP** (`handlers/phase-quality.md`): read ai-verify / ai-review / ai-governance SKILL.md once at loop entry; dispatch verify+guard+review in parallel on the full changeset; consolidate findings (unified severity). Clean → Phase 6. Blockers + round<3 → fix and re-assess. Round=3: blockers STOP, criticals/highs flag and proceed.

**Step 6 — DELIVER** (`handlers/phase-deliver.md`): build the Integrity Report; follow `/ai-pr` SKILL.md; cleanup runtime dir; clear spec.md + plan.md; verify cleanup. `--resume` handles mid-pipeline re-entry.

## Flags

| Flag         | Behavior                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `--resume`   | Read `.ai-engineering/runtime/autopilot/manifest.md`, determine pipeline state, re-enter at the correct phase/wave. Never re-executes completed phases. |
| `--no-watch` | Create PR without the watch-and-fix loop. Useful for draft delivery or when CI is managed externally.                                 |
| `--backlog --source <github|ado|local>` | Backlog mode (D-127-12, absorbs the legacy `/ai-run` skill). Normalizes work items from the named source into the run model: `github` (Issues + GitHub Projects v2), `ado` (Azure Boards work items), `local` (a markdown task list path). The 6-phase pipeline still runs; Phase 1 DECOMPOSE is replaced by intake + per-item planning, Phase 4 IMPLEMENT dispatches one bounded build per item. |

Thin orchestrator: phases READ other skills' SKILL.md and EMBED instructions into subagent prompts (no inline implementation). When those skills improve, autopilot inherits the improvement.

## Dispatch threshold

Dispatch the `ai-autopilot` agent when the work matches the "When to Use" criteria above (≥3 concerns, ≥10 files, post-`/ai-brainstorm` approval, or any backlog with `--backlog`). For smaller scope, hand off to `/ai-build` directly. The agent file (`.codex/agents/ai-autopilot.md`) is the orchestrator handle; the procedural contract lives in this SKILL.md.

## Governance

DEC-023: invocation is the single approval gate; internal gates (sub-spec validation, DAG verification, quality convergence) are automatic and cannot be bypassed. The consolidation path is mandatory: sub-spec branch/worktree → wave or integration commits → final PR → protected main. State transitions live on disk in `.ai-engineering/runtime/autopilot/manifest.md`, never in agent memory.

## Failure Recovery & Telemetry

| Scenario | Recovery |
| --- | --- |
| Phase 2 agent fails | Retry once → mark `plan-failed`; evaluate subset viability. |
| Build agent fails in Phase 4 | Mark sub-spec `blocked`; cascade-block dependents; continue wave. |
| Quality loop exhausted with blockers | STOP. Do NOT create PR. Escalate to user. |
| Quality loop exhausted with only criticals/highs | Phase 6 with PR flagged; Integrity Report documents issues. |
| Mid-pipeline crash | Run `/ai-autopilot --resume`. |
| Final cleanup fails | Warn but do not block — PR is already delivered. |

Rollback: `git reset --soft HEAD~N` where N = wave + quality-fix commits. Telemetry events fire per phase transition: `autopilot.{started,decompose_complete,deep_plan_complete,dag_built,subspec_complete,quality_round,subspec_failed,final_verify,pr_created,done}`.

## Common Mistakes

Do not run on draft or under-scoped specs, cross repositories, carry context between sub-specs, hand-edit mirrors, or keep patching after the quality loop says escalate.

## Examples

### Example 1 — autonomous end-to-end delivery

User: "implement spec-127 end to end"

```
/ai-autopilot "implement spec-127"
```

Phase 1 decompose into sub-specs, Phase 2 deep-plan in parallel, Phase 3 build DAG, Phase 4 implement in waves, Phase 5 quality loop (verify+guard+review max 3 rounds), Phase 6 deliver via PR.

### Example 2 — resume after interruption

User: "resume the autopilot run that crashed yesterday"

```
/ai-autopilot --resume
```

Reads the manifest, identifies the last completed phase, re-enters at the correct state without re-doing finished work.

### Example 3 — backlog run from GitHub Issues

User: "run all open issues with the ready-to-work label, no human checkpoints"

```
/ai-autopilot --backlog --source github "label:ready-to-work is:open"
```

Normalizes issues into the run model, performs baseline `ai-explore` of the repo, builds an overlap-aware DAG, dispatches bounded `ai-build` packets per item, runs item + integration gates, delivers via `ai-pr` (D-127-12; replaces `/ai-run`).

## Integration

Called by: user directly post-`/ai-brainstorm` approval (or with `--backlog` for backlog runs). Reads: `_shared/execution-kernel.md`, `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-governance/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`. Delegates to: `ai-explore`, `ai-build`, `ai-verify`, `ai-guard`, `ai-review` agents. Transitions to: `/ai-cleanup`. See also: `/ai-build` (smaller scope), `/ai-board sync` (lifecycle transitions for backlog mode).

$ARGUMENTS
