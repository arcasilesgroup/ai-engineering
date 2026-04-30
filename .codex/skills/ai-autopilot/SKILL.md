---
name: ai-autopilot
description: Use after /ai-brainstorm approval when a spec is large (3+ independent concerns or 10+ files) and needs autonomous end-to-end delivery. Decomposes into sub-specs, plans with parallel agents, builds a dependency DAG, implements in waves, runs quality convergence loops, and delivers via PR. Invocation is the approval gate — no further confirmation requested. Not for small tasks — use /ai-dispatch.
effort: max
argument-hint: "'implement spec-NNN'|--resume|--no-watch"
tags: [orchestration, autonomous, multi-spec, pipeline, execution, dag, transparency]
---


# Autopilot v2

## Purpose

Autonomous execution of large approved specs via a 6-phase pipeline. Decomposes a spec into N focused sub-specs, deep-plans each with parallel agents, orchestrates a dependency-aware execution DAG, implements in waves, converges on quality through iterative verify+guard+review loops, and delivers the full changeset via PR with a transparency report. Execution is not complete until sub-spec work converges into a final delivery PR against protected main. One invocation, zero interruptions, full disclosure.

## When to Use

- Spec has >= 3 independent concerns or touches >= 10 files
- After `/ai-brainstorm` approval (spec.md exists and is not a placeholder)
- When manual `/ai-dispatch` would overflow context within a single session
- Multi-concern work that benefits from parallel intelligence gathering and DAG-driven execution

## When NOT to Use

- < 3 concerns -- use `/ai-dispatch` directly (autopilot overhead not justified)
- Draft or unapproved spec -- run `/ai-brainstorm` first
- Need human review between phases -- use `/ai-dispatch` with manual checkpoints
- Cross-repo changes -- coordinate manually
- Data migrations with destructive DDL -- require explicit user approval per step

## Process

### Step 0: Validate

1. Confirm `specs/spec.md` is not a placeholder. If it is: STOP. Report: "No approved spec. Run `/ai-brainstorm` first."
2. If `--resume` flag: read `specs/autopilot/manifest.md` and jump to the Resume Protocol (Phase 6 handler).
3. Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`; resolve paths into `context_paths` and pass paths (not content) to subagent prompts.
4. Note: plan.md is NOT required. Phase 2 agents generate their own plans (D7).

### Step 1: DECOMPOSE

Read `handlers/phase-decompose.md` and execute. Extract N independent concerns; abort if N < 3 (recommend `/ai-dispatch`); write sub-spec dirs `specs/autopilot/sub-NNN/` with `spec.md` + `plan.md` shells; write execution manifest to `specs/autopilot/manifest.md`.

### Step 2: DEEP PLAN

Read `handlers/phase-deep-plan.md` and execute. Dispatch explore + plan agents in parallel (one per sub-spec); each agent enriches `sub-NNN/spec.md` (Exploration) and `sub-NNN/plan.md` (checkbox tasks with exports/imports declarations). Do not infer overlap, exports/imports, or wave boundaries from spec text alone; Phase 2 must gather exploration evidence first. Failed agents retry once then mark `plan-failed`.

### Step 3: ORCHESTRATE

Read `handlers/phase-orchestrate.md` and execute. Build file-overlap matrix and import-chain graph from the Phase 2 exploration + plan artifacts; never build the execution DAG from spec text alone. Construct execution DAG with wave assignments; merge sub-specs with unresolvable conflicts.

### Step 4: IMPLEMENT

Read `handlers/phase-implement.md` and execute. **Per-wave kernel**: see `.codex/skills/_shared/execution-kernel.md`. Autopilot wraps the kernel per-wave -- dispatch the build agent per sub-spec in parallel within a wave (Sub-flow 1), run the build-verify-review loop per task (Sub-flow 2), collect Self-Reports + per-wave commits (Sub-flow 3), advance board state (Sub-flow 4). Cascade-block dependents of failed sub-specs.

### Step 5: QUALITY LOOP

Read `handlers/phase-quality.md` and execute:

1. Read skill files once at loop entry: ai-verify, ai-review, ai-governance SKILL.md. Compute `git diff main...HEAD` once. Read Self-Reports once. Reused across rounds -- not re-read per round.
2. Dispatch verify + guard + review agents in parallel on full changeset (1 round by default).
3. Consolidate findings with unified severity mapping.
4. If clean (0 blockers): proceed to Phase 6. Critical/high findings flagged in PR but do not trigger additional rounds.
5. If blockers found and round < 3: dispatch fix agents, commit, re-assess.
6. If round = 3: blockers -> STOP; criticals/highs -> Phase 6 flagged.

### Step 6: DELIVER

Read `handlers/phase-deliver.md` and execute. Build Integrity Report from Self-Reports + quality audit; follow `/ai-pr` SKILL.md in full; cleanup `specs/autopilot/`; clear spec.md + plan.md; verify cleanup. Resume Protocol handles mid-pipeline re-entry via `--resume`.

Handler dispatch per phase: see Steps 1-6 above (each cites its `handlers/phase-*.md`). Agent pattern per phase: 1=orchestrator, 2=explore+plan x N parallel, 3=orchestrator, 4=build x N per wave, 5=verify+guard+review parallel (build for fixes), 6=PR pipeline + cleanup.

## Flags

| Flag         | Behavior                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `--resume`   | Read `specs/autopilot/manifest.md`, determine pipeline state, re-enter at the correct phase/wave. Never re-executes completed phases. |
| `--no-watch` | Create PR without the watch-and-fix loop. Useful for draft delivery or when CI is managed externally.                                 |

Thin orchestrator: phases READ other skills' SKILL.md and EMBED instructions into subagent prompts (no inline implementation). When those skills improve, autopilot inherits the improvement.

## Governance

DEC-023: User invocation of `/ai-autopilot` is the single approval gate. All internal gates (sub-spec validation, DAG verification, quality convergence) are automatic and cannot be bypassed.

The consolidation path is mandatory: sub-spec branch/worktree -> wave or integration commits -> final PR -> protected main.

State transitions are recorded on disk in `specs/autopilot/manifest.md` -- never in agent memory. Any phase can be audited post-hoc.

D7: plan.md is not required. Phase 2 agents generate their own detailed plans per sub-spec.

## Failure Recovery

| Scenario                                         | Recovery                                                                                     |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Phase 2 agent fails                              | Retry once. If second attempt fails: mark sub-spec `plan-failed`. Evaluate subset viability. |
| Build agent fails in Phase 4                     | Mark sub-spec `blocked`. Cascade-block dependents. Continue remaining sub-specs in wave.     |
| Quality loop exhausted (3 rounds) with blockers  | STOP. Do NOT create PR. Escalate to user.                                                    |
| Quality loop exhausted with only criticals/highs | Proceed to Phase 6. PR created but flagged. Integrity Report documents remaining issues.     |
| Mid-pipeline crash                               | Run `/ai-autopilot --resume`. Reads manifest, continues from last incomplete phase/wave.     |
| Final cleanup fails                              | Warn but do not block -- PR is already delivered.                                            |

Rollback: `git reset --soft HEAD~N` where N = number of wave + quality-fix commits. Included in failure reports.

## Telemetry

Events emitted at each phase transition via hook system: `autopilot.started`, `autopilot.decompose_complete`, `autopilot.deep_plan_complete`, `autopilot.dag_built`, `autopilot.subspec_complete`, `autopilot.quality_round`, `autopilot.subspec_failed`, `autopilot.final_verify`, `autopilot.pr_created`, `autopilot.done`.

## Quick Reference

```
/ai-autopilot "implement spec-065"     # full 6-phase pipeline
/ai-autopilot --resume                  # continue from failure point
/ai-autopilot "spec" --no-watch         # skip PR watch loop
```

## Common Mistakes

- Running on draft or unapproved specs -- brainstorm approval is a hard prerequisite.
- Running on specs with < 3 concerns -- use `/ai-dispatch` instead.
- Cross-repo work -- autopilot operates within a single repository.
- Expecting plan.md to exist -- v2 does NOT require it.
- Carrying context between sub-specs -- each build agent gets fresh context by design.
- Attempting to fix failures after quality loop exhaustion with blockers -- escalate, do not compound errors.
- Hand-editing mirrors instead of running `sync_command_mirrors.py` after changes.

## Integration

- **Called by**: user directly (after `/ai-brainstorm` approval)
- **Reads**: `.codex/skills/_shared/execution-kernel.md`, `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-governance/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`
- **Delegates to**: explore agent (research), build agent (implementation), verify agent (gates), guard agent (governance advisory), review agent (code review)
- **Transitions to**: `/ai-cleanup` after merge, or back to user on failure

$ARGUMENTS
