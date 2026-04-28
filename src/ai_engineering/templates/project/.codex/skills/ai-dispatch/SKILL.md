---
name: ai-dispatch
description: Use when an approved plan.md exists and execution should begin. Trigger for 'go', 'start building', 'execute the plan', 'implement it', 'let's do this', 'run the plan', 'resume', or 'continue' after interruption. Not without an approved plan — run /ai-plan first. Orchestrates subagents per task with two-stage review, progress tracking, and automated delivery.
effort: high
argument-hint: "[spec-NNN or --resume]"
---



# Dispatch

## Purpose

Execution engine for approved plans. Reads plan.md and tasks.md, dispatches one subagent per task (fresh context), runs two-stage review on each deliverable, and tracks progress. If stuck: STOP and re-plan.

## When to Use

- After `/ai-plan` produces an approved plan
- To resume execution: `/ai-dispatch --resume`
- Never without an approved plan (run `/ai-plan` first)

## Process

1. **Board sync (in_progress)** -- read `specs/spec.md` frontmatter `refs`; for each work item ref where the hierarchy rule is not `never_close` (i.e., user_stories, tasks, bugs, issues), invoke `/ai-board-sync in_progress <work-item-ref>`. Fail-open: do not block DAG construction if this fails.
2. **Guard advisory** -- before dispatching any build task, invoke the Guard agent (`ai-guard`) in `gate` mode for governance advisory. Fail-open: if guard is unavailable or errors, log warning and continue -- never block dispatch.
3. **Execute kernel**: see `.codex/skills/_shared/execution-kernel.md`. Dispatch wraps each task with the kernel (Sub-flow 1 dispatch -> Sub-flow 2 build-verify-review -> Sub-flow 3 artifact collection -> Sub-flow 4 board sync). The pre/post wrappers above and below remain dispatch-specific.
4. **Quality check** -- read `handlers/quality.md` and execute: Verify+Review on full changeset, max 2 rounds.
5. **Deliver** -- read `handlers/deliver.md` and execute: PR via ai-pr with quality report.

## Resume Protocol

When invoked with `--resume`, read `specs/plan.md` and determine re-entry point:

1. **Incomplete tasks remain**: resume at the first incomplete phase. Skip completed tasks.
2. **All tasks DONE but no quality check recorded**: resume at the Quality Check step. Read `handlers/quality.md`.
3. **Quality passed but no PR created**: resume at the Deliver step. Read `handlers/deliver.md`.
4. **PR exists but not merged**: resume at watch-and-fix loop per `handlers/deliver.md`.

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| Quality Check | `handlers/quality.md` | Verify + Review parallel |
| Deliver | `handlers/deliver.md` | PR pipeline + cleanup |

## Common Mistakes

- Dispatching without an approved plan.
- Giving subagents the entire codebase context (scope them tightly).
- Skipping the two-stage review.
- Continuing past a BLOCKED task without user input.
- Modifying test files from a RED phase during a GREEN phase task.
- Skipping the quality check after task execution.

## Integration

- **Called by**: user directly (after `/ai-plan` approval)
- **Calls**: `ai-build` (build tasks), `ai-verify` (scan tasks, quality check), `ai-review` (quality check), `ai-pr` (deliver), `/ai-board-sync` (in_progress transition)
- **Reads**: `.codex/skills/_shared/execution-kernel.md` (per-task loop), `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-pr/SKILL.md` (thin orchestrator, embedded at dispatch time)
- **Transitions to**: PR merge (after deliver), or back to `/ai-plan` (if re-plan needed)

$ARGUMENTS
