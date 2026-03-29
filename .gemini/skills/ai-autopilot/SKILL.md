---
name: ai-autopilot
description: Use after /ai-brainstorm approval when a spec is large (3+ independent concerns or 10+ files) and needs autonomous end-to-end delivery. Decomposes into sub-specs, plans with parallel agents, builds a dependency DAG, implements in waves, runs quality convergence loops, and delivers via PR. Invocation is the approval gate — no further confirmation requested. Not for small tasks — use /ai-dispatch.
effort: max
argument-hint: "'implement spec-NNN'|--resume|--no-watch"
tags: [orchestration, autonomous, multi-spec, pipeline, execution, dag, transparency]
---



# Autopilot v2

## Purpose

Autonomous execution of large approved specs via a 6-phase pipeline. Decomposes a spec into N focused sub-specs, deep-plans each with parallel agents, orchestrates a dependency-aware execution DAG, implements in waves, converges on quality through iterative verify+guard+review loops, and delivers the full changeset via PR with a transparency report. One invocation, zero interruptions, full disclosure.

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

### Step 0: Load and Validate

1. Read `.ai-engineering/specs/spec.md` -- confirm it is not a placeholder
2. Read `.ai-engineering/state/decision-store.json` -- load constraints
3. If spec is placeholder: STOP. Report: "No approved spec. Run `/ai-brainstorm` first."
4. If `--resume` flag: read `specs/autopilot/manifest.md` and jump to the Resume Protocol (Phase 6 handler)
5. Note: plan.md is NOT required. Phase 2 agents generate their own plans (D7).

### Step 1: DECOMPOSE

Read `handlers/phase-decompose.md` and execute:

1. Extract N independent concerns from the spec
2. If N < 3: abort, recommend `/ai-dispatch`
3. Write sub-spec directories `specs/autopilot/sub-NNN/` with `spec.md` + `plan.md` shells
4. Write execution manifest to `specs/autopilot/manifest.md`

### Step 2: DEEP PLAN

Read `handlers/phase-deep-plan.md` and execute:

1. Dispatch the explore and plan agents in parallel (one per sub-spec)
2. Each agent deep-explores the codebase and enriches `sub-NNN/spec.md` (Exploration) and `sub-NNN/plan.md` (checkbox-formatted tasks with exports/imports declarations)
3. Gate: every sub-spec has enriched Exploration + Plan sections
4. Failed agents retry once, then mark `plan-failed`

### Step 3: ORCHESTRATE

Read `handlers/phase-orchestrate.md` and execute:

1. Analyze all N plans together
2. Build file-overlap matrix and import-chain graph
3. Construct execution DAG with wave assignments
4. Merge sub-specs with unresolvable conflicts

### Step 4: IMPLEMENT

Read `handlers/phase-implement.md` and execute:

1. For each wave in DAG order: dispatch the build agent per sub-spec (parallel within wave)
2. Each agent marks checkboxes `- [x]` in `sub-NNN/plan.md` as tasks complete, then writes a Self-Report (real/aspirational/stub/failing/invented/hallucinated) to `plan.md`
3. Commit per wave, update manifest
4. Cascade-block dependents of failed sub-specs

### Step 5: QUALITY LOOP

Read `handlers/phase-quality.md` and execute:

1. Dispatch the verify agent + the guard agent + the review agent in parallel on full changeset
2. Consolidate findings with unified severity mapping
3. If clean (0 blockers+criticals+highs): proceed to Phase 6
4. If issues remain and round < 3: dispatch fix agents, commit, repeat
5. If round = 3: blockers -> STOP; criticals/highs -> Phase 6 flagged

### Step 6: DELIVER

Read `handlers/phase-deliver.md` and execute:

1. Build Integrity Report from Self-Reports (in `sub-NNN/plan.md`) + quality audit
2. Follow `/ai-pr` SKILL.md in full
3. Cleanup: delete `specs/autopilot/` (all subdirectories), clear spec.md + plan.md, verify cleanup
4. Resume Protocol handles mid-pipeline re-entry via `--resume`

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| 1. Decompose | `handlers/phase-decompose.md` | Orchestrator (read-only analysis) |
| 2. Deep Plan | `handlers/phase-deep-plan.md` | Explore+Plan x N parallel |
| 3. Orchestrate | `handlers/phase-orchestrate.md` | Orchestrator (DAG construction) |
| 4. Implement | `handlers/phase-implement.md` | Build x N per wave (DAG-driven) |
| 5. Quality Loop | `handlers/phase-quality.md` | Verify + Guard + Review parallel, Build for fixes |
| 6. Deliver | `handlers/phase-deliver.md` | PR pipeline + cleanup |

## Flags

| Flag | Behavior |
|------|----------|
| `--resume` | Read `specs/autopilot/manifest.md`, determine pipeline state, re-enter at the correct phase/wave. Never re-executes completed phases. See Resume Protocol in phase-deliver handler. |
| `--no-watch` | Create PR without the watch-and-fix loop. Useful for draft delivery or when CI is managed externally. |

## Thin Orchestrator Principle

This skill READS other skills' SKILL.md files and EMBEDS their instructions into subagent prompts. It does NOT contain implementation logic. The phases delegate to:

- `.gemini/skills/ai-verify/SKILL.md` for quality gates (Phase 5)
- `.gemini/skills/ai-review/SKILL.md` for code review (Phase 5)
- `.gemini/skills/ai-pr/SKILL.md` for pull request creation and delivery (Phase 6)
- `.gemini/skills/ai-commit/SKILL.md` for incremental commit protocol (Phase 4, 5)

When those skills improve, autopilot benefits automatically. No duplication, no drift.

## Governance

DEC-023: User invocation of `/ai-autopilot` is the single approval gate. All internal gates (sub-spec validation, DAG verification, quality convergence) are automatic and cannot be bypassed.

State transitions are recorded on disk in `specs/autopilot/manifest.md` -- never in agent memory. Any phase can be audited post-hoc.

D7: plan.md is not required. Phase 2 agents generate their own detailed plans per sub-spec.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Phase 2 agent fails (timeout, crash) | Retry once. If second attempt fails: mark sub-spec `plan-failed`. Evaluate subset viability. |
| Build agent fails in Phase 4 | Mark sub-spec `blocked`. Cascade-block dependents. Continue with remaining sub-specs in wave. |
| Quality loop exhausted (3 rounds) with blockers | STOP. Do NOT create PR. Report blockers and escalate to user. |
| Quality loop exhausted with only criticals/highs | Proceed to Phase 6. PR created but flagged. Integrity Report documents remaining issues. |
| Mid-pipeline crash | Run `/ai-autopilot --resume`. Reads manifest, continues from last incomplete phase/wave. |
| Final cleanup fails | Warn but do not block -- PR is already delivered. |

Rollback: `git reset --soft HEAD~N` where N = number of wave + quality-fix commits. Included in failure reports.

## Telemetry

Events emitted at each phase transition via hook system:

| Event | Trigger |
|-------|---------|
| `autopilot.started` | Step 0 completes |
| `autopilot.decompose_complete` | Phase 1 completes |
| `autopilot.deep_plan_complete` | Phase 2 completes |
| `autopilot.dag_built` | Phase 3 completes |
| `autopilot.subspec_complete` | Each sub-spec passes implementation |
| `autopilot.quality_round` | Each quality loop round completes |
| `autopilot.subspec_failed` | Sub-spec blocked or cascade-blocked |
| `autopilot.final_verify` | Phase 5 completes (pass or exhausted) |
| `autopilot.pr_created` | Phase 6 PR created |
| `autopilot.done` | Phase 6 cleanup completes |

## Quick Reference

```
/ai-autopilot "implement spec-065"     # full 6-phase pipeline
/ai-autopilot --resume                  # continue from failure point
/ai-autopilot "spec" --no-watch         # skip PR watch loop
```

## Common Mistakes

- Running on draft or unapproved specs -- brainstorm approval is a hard prerequisite.
- Running on specs with < 3 concerns -- use `/ai-dispatch` instead, autopilot overhead is not justified.
- Cross-repo work -- autopilot operates within a single repository.
- Expecting plan.md to exist -- v2 does NOT require it. Phase 2 agents plan independently.
- Carrying context between sub-specs -- each build agent gets fresh context by design.
- Attempting to fix failures after quality loop exhaustion with blockers -- escalate, do not compound errors.
- Hand-editing mirrors instead of running `sync_command_mirrors.py` after changes.

## Integration

- **Called by**: user directly (after `/ai-brainstorm` approval)
- **Reads**: `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`
- **Delegates to**: the explore agent for research, the build agent for implementation, the verify agent for gates, the guard agent for governance advisory, the review agent for code review
- **Transitions to**: `/ai-cleanup` after merge, or back to user on failure

$ARGUMENTS
