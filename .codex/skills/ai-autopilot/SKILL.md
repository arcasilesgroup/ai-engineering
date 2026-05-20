---
name: ai-autopilot
description: "Delivers large multi-concern specs and backlog runs autonomously: decomposes specs into sub-specs (or normalizes work items into a backlog DAG), deep-plans with parallel agents, builds a dependency DAG, implements in waves, runs a single final quality loop with one bounded quality-remediation pass (verify+guard+review on full changeset), delivers via PR. Trigger for 'implement spec-NNN end to end', 'autopilot this', 'autonomous delivery', 'decompose and ship', 'run the backlog', 'execute these GitHub issues', 'process the sprint backlog'. Invocation is the approval gate. Not for small or single-concern tasks; use /ai-build instead. Not for ambiguous requirements; use /ai-brainstorm first."
effort: high
argument-hint: "'implement spec-NNN'|--backlog --source <github|ado|local>|--resume|--no-watch"
tags: [orchestration, autonomous, multi-spec, backlog, pipeline, execution, dag, transparency]
model_tier: opus
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-autopilot/SKILL.md
edit_policy: generated-do-not-edit
---


# Autopilot v2

## Purpose

Autonomous execution of large approved specs via a 6-phase pipeline. Decomposes a spec into N focused sub-specs, deep-plans each with parallel agents, orchestrates a dependency-aware execution DAG, implements in waves, runs a single final verify+guard+review pass with one bounded quality-remediation pass on the full changeset, and delivers the full changeset via PR with a transparency report. Execution is not complete until sub-spec work converges into a final delivery PR against protected main. One invocation, zero interruptions, full disclosure.

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

**Step 0 — Validate**: confirm `.ai-engineering/specs/spec.md` is not a placeholder (else STOP and report `/ai-brainstorm`). On `--resume`, read `.ai-engineering/runtime/autopilot/manifest.md` and re-enter at the Resume Protocol. Load stack contexts (manifest `providers.stacks` + `.ai-engineering/overrides/<stack>/conventions.md`) and pass paths (not content) to subagents. plan.md is not required — Phase 2 agents generate their own. `ai-eng host probe` is diagnostic/advisory only; `ok_to_dispatch` is not a standard-flow execution gate and cannot block `/ai-autopilot`.

**Step 1 — DECOMPOSE** (`handlers/phase-decompose.md`): extract N independent concerns; abort if N<3 (recommend `/ai-build`); write sub-spec dirs and the execution manifest.

**Step 2 — DEEP PLAN** (`handlers/phase-deep-plan.md`): dispatch explore+plan agents in parallel; each enriches `sub-NNN/spec.md` (Exploration) + `plan.md` (checkbox tasks with exports/imports). Failed agents retry once → mark `plan-failed`.

**Step 3 — ORCHESTRATE** (`handlers/phase-orchestrate.md`): build the file-overlap matrix and import-chain graph from Phase-2 evidence (never from spec text alone); construct the wave-assigned DAG; merge unresolvable conflicts.

**Step 4 — IMPLEMENT** (`handlers/phase-implement.md`): per-wave kernel from `.codex/skills/_shared/execution-kernel.md`. Dispatch build agents per sub-spec in parallel within a wave; each task self-validates via TDD; wave-end guard advisory remains for governance. Collect Self-Reports + per-wave commits. Cascade-block dependents of failed sub-specs.

**Step 5 — QUALITY LOOP** (`handlers/phase-quality.md`): read ai-verify / ai-review / ai-governance SKILL.md once at loop entry; dispatch verify+guard+review in parallel on the full changeset; consolidate findings (unified severity). Clean → Phase 6. Blocker/critical/high findings enter Phase 5b only if the one bounded quality-remediation pass is unused and the fixes are finding-scoped. Remaining blocker/critical/high findings after final reassessment → STOP + escalate to user.

**Phase 5b — BOUNDED REMEDIATION** (`handlers/phase-quality.md`): persist `quality_remediation.max_attempts: 1` in the autopilot manifest, map each finding to `sub-NNN`, `integration`, or `shared`, run cross-platform focal reproducers, and then return to Step 5 final reassessment. No re-decompose, no re-plan, no second remediation pass.

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

## Examples

See `references/examples.md` for the three canonical autopilot
invocations (end-to-end delivery, `--resume` after interruption,
`--backlog --source github` lane). Failure-recovery rows + telemetry
event taxonomy live in the same reference file. Common mistakes
checklist (do not run on draft specs, never cross repos, never carry
context across sub-specs, never hand-edit mirrors) is documented
there.

## Integration

Called by: user directly post-`/ai-brainstorm` approval (or with `--backlog` for backlog runs). Reads: `_shared/execution-kernel.md`, `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-governance/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`. Delegates to: `ai-explore`, `ai-build`, `ai-verify`, `ai-advise`, `ai-review` agents. Transitions to: `/ai-branch-cleanup`. See also: `/ai-build` (smaller scope), `/ai-board sync` (lifecycle transitions for backlog mode), `references/examples.md`.

$ARGUMENTS
