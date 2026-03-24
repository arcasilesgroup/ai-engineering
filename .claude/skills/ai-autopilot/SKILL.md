---
name: ai-autopilot
description: "Use when executing large approved specs autonomously: splits into focused sub-specs, explores deeply, implements with fresh-context agents, verifies anti-hallucination gates, and delivers via PR. Invocation IS approval."
effort: max
argument-hint: "'implement spec-NNN'|--resume|--no-watch"
tags: [orchestration, autonomous, multi-spec, pipeline, execution]
---


# Autopilot

## Purpose

Autonomous execution of large approved specs. Splits a spec with N work units into focused sub-specs, executes each sequentially with fresh-context agents, verifies every increment against anti-hallucination gates, and delivers the full changeset via PR. One invocation, zero interruptions.

## When to Use

- Spec has >5 tasks or touches >10 files
- After `/ai-brainstorm` approval and `/ai-plan` completion
- When manual `/ai-dispatch` would overflow context within a single session
- Multi-phase work that benefits from incremental verify gates

## When NOT to Use

- <5 tasks -- use `/ai-dispatch` directly
- Draft or unapproved spec -- run `/ai-brainstorm` first
- Need human review between phases -- use `/ai-dispatch` with manual checkpoints
- Cross-repo changes -- coordinate manually
- Data migrations with destructive DDL -- require explicit user approval per step

## Process

### Step 0: Load and Validate

1. Read `.ai-engineering/specs/spec.md` -- confirm it is not a placeholder
2. Read `.ai-engineering/specs/plan.md` -- confirm tasks exist
3. Read `.ai-engineering/state/decision-store.json` -- load constraints
4. If spec is placeholder or plan is empty: STOP. Report: "No approved spec. Run `/ai-brainstorm` first."

### Step 1: Split + Explore

Read `handlers/phase-split.md` and execute:

1. Decompose the spec into ordered sub-specs (one concern per sub-spec)
2. Write each to `.ai-engineering/specs/autopilot/sub-NNN.md` with: scope, inputs, outputs, verify checklist
3. Write execution manifest to `.ai-engineering/specs/autopilot/manifest.md`
4. Dispatch parallel Agent(Explore) to map codebase state relevant to each sub-spec
5. Collect findings into `.ai-engineering/specs/autopilot/exploration.md`
6. Update sub-specs with discovered file paths, patterns, and constraints

### Step 2: Execute Loop (sequential, per sub-spec)

For each sub-spec in manifest order:

**2a. Plan + Implement** -- Read `handlers/phase-execute.md` and execute:
- Read the sub-spec and relevant SKILL.md files
- Compose the build prompt with embedded context (file paths, patterns, constraints, acceptance criteria)
- Dispatch Agent(Build) with fresh context -- no carry-over from previous sub-specs
- Build agent receives: sub-spec scope, referenced files, stack standards, verify checklist

**2b. Verify** -- Read `handlers/phase-verify.md` and execute:
- Dispatch Agent(Verify) against the sub-spec's acceptance criteria
- Gate checklist: functional correctness, anti-hallucination (files/functions/imports exist), stack validation (linters/types), no regressions (existing tests pass)
- If verify passes: commit the increment, update manifest.md marking sub-spec complete
- If verify fails: retry implementation ONCE with the failure report embedded in the build prompt
- If second attempt also fails: **STOP the entire pipeline**. Report: what was attempted, what failed, the verify report, and rollback instructions

### Step 3: Final Verification

After all sub-specs complete:

1. Run full test suite: `pytest tests/ -v`
2. Run full lint pass: `ruff check` + `ruff format --check`
3. Run type check: `ty check src/`
4. Dispatch Agent(Verify) on the full changeset against the original spec
5. Confirm no regressions against main branch
6. If final verify fails: escalate -- do not attempt to fix at this stage

### Step 4: PR Pipeline

Read `handlers/phase-pr.md` and execute:

1. Follow `.claude/skills/ai-pr/SKILL.md` in full
2. PR body includes: summary of all sub-specs delivered, verify reports as evidence
3. Enable auto-complete with squash merge
4. Enter watch-and-fix loop (unless `--no-watch`)

### Step 5: Cleanup

After PR merges (or immediately if `--no-watch`):

1. Delete `.ai-engineering/specs/autopilot/` directory
2. Clear `specs/spec.md` with placeholder
3. Clear `specs/plan.md` with placeholder
4. Run `/ai-cleanup --all`

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| Split + Explore | `handlers/phase-split.md` | Explore x N parallel |
| Execute | `handlers/phase-execute.md` | Plan + Build per sub-spec |
| Verify | `handlers/phase-verify.md` | Verify per sub-spec |
| PR + Deliver | `handlers/phase-pr.md` | PR pipeline |

## Flags

| Flag | Behavior |
|------|----------|
| `--resume` | Read `specs/autopilot/manifest.md`, find last incomplete sub-spec, continue from there. Skip already-completed sub-specs. |
| `--no-watch` | Create PR without the watch-and-fix loop (step 14 of ai-pr). Useful for draft delivery or when CI is managed externally. |

## Thin Orchestrator Principle

This skill READS other skills' SKILL.md files and EMBEDS their instructions into subagent prompts. It does NOT contain implementation logic. The phases delegate to:

- `/ai-dispatch` patterns for task execution
- `/ai-verify` for anti-hallucination gates
- `/ai-pr` for pull request creation and delivery
- `/ai-commit` for incremental commit protocol

When those skills improve, autopilot benefits automatically. No duplication, no drift.

## Governance

DEC-023: User invocation of `/ai-autopilot` is the single approval gate. All internal gates (spec validation, sub-spec review, verify gates) are automatic and cannot be bypassed.

State transitions are recorded on disk in `specs/autopilot/manifest.md` -- never in agent memory. Any phase can be audited post-hoc.

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| Verify fails 2x on a sub-spec | Pipeline halts. Report includes: sub-spec, attempts, verify reports, rollback command. |
| Mid-pipeline crash | Run `/ai-autopilot --resume`. Reads manifest.md, continues from last incomplete sub-spec. |
| Final verify fails | Escalate to user. Do not attempt fixes on the assembled changeset. |
| PR watch loop fails 3x | Escalate per ai-pr handler protocol. |

Rollback: `git reset --soft HEAD~N` where N = number of sub-spec commits. Included in failure reports.

## Telemetry

Events emitted at each phase transition via hook system:

| Event | Trigger |
|-------|---------|
| `autopilot.started` | Step 0 completes |
| `autopilot.split_complete` | Step 1 completes |
| `autopilot.subspec_complete` | Each sub-spec passes verify |
| `autopilot.subspec_failed` | Sub-spec fails verify 2x |
| `autopilot.final_verify` | Step 3 completes |
| `autopilot.pr_created` | Step 4 completes |
| `autopilot.done` | Step 5 completes |

## Quick Reference

```
/ai-autopilot "implement spec-062"     # full pipeline
/ai-autopilot --resume                  # continue from failure
/ai-autopilot "spec" --no-watch         # skip PR watch loop
```

## Common Mistakes

- Running on draft or unapproved specs -- brainstorm approval is a hard prerequisite.
- Running on specs with <5 tasks -- use `/ai-dispatch` instead, autopilot overhead is not justified.
- Cross-repo work -- autopilot operates within a single repository.
- Skipping the verify gate -- every sub-spec MUST pass verify before the next begins.
- Carrying context between sub-specs -- each build agent gets fresh context by design.
- Attempting to fix failures after final verify -- escalate, do not compound errors.

## Integration

- **Called by**: user directly (after `/ai-brainstorm` + `/ai-plan` approval)
- **Reads**: `ai-dispatch/SKILL.md`, `ai-verify/SKILL.md`, `ai-pr/SKILL.md`, `ai-commit/SKILL.md`
- **Delegates to**: Agent(Explore) for research, Agent(Build) for implementation, Agent(Verify) for gates
- **Transitions to**: `/ai-cleanup` after merge, or back to user on failure

$ARGUMENTS
