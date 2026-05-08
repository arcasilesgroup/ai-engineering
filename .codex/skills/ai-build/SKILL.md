---
name: ai-build
description: "Canonical implementation gateway: reads approved plan.md, resolves stack from manifest, deterministic-routes each task to its adapter, dispatches the build agent in an isolated worktree, runs verify+review per task, and chains commit+pr after the last. Trigger for 'go', 'start building', 'execute the plan', 'implement it', 'lets do this', 'build the plan', 'resume', 'continue'. Not without an approved plan; run /ai-plan first. Not for multi-concern specs needing decomposition; use /ai-autopilot instead."
effort: high
argument-hint: "[spec-NNN or --resume]"
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-build/SKILL.md
edit_policy: generated-do-not-edit
---


# Build

## Purpose

Execution engine for approved plans. Reads plan.md and tasks.md, dispatches one subagent per task (fresh context), runs two-stage review on each deliverable, and tracks progress. If stuck: STOP and re-plan.

## When to Use

- After `/ai-plan` produces an approved plan
- To resume execution: `/ai-build --resume`
- Never without an approved plan (run `/ai-plan` first)

## Process

0. **Preflight dependencies** -- verify `.ai-engineering/specs/plan.md`, `.codex/skills/_shared/execution-kernel.md`, `.codex/skills/ai-build/handlers/quality.md`, and `.codex/skills/ai-build/handlers/deliver.md` exist. If any are missing: STOP and report the exact missing path(s). Never improvise missing orchestration logic.
1. **Board sync (in_progress)** -- read `.ai-engineering/specs/spec.md` frontmatter `refs`; for each work item ref where the hierarchy rule is not `never_close` (i.e., user_stories, tasks, bugs, issues), invoke `/ai-board sync in_progress <work-item-ref>`. Fail-open: do not block DAG construction if this fails.
2. **Guard advisory** -- before dispatching any build task, invoke the Guard agent (`ai-guard`) in `gate` mode for governance advisory. Fail-open: if guard is unavailable or errors, log warning and continue -- never block dispatch.
2b. **Stack adapter routing (D-127-06 / sub-008)** -- per task, call `tools.skill_app.deterministic_router.resolve_adapter(task_path, spec_stack)` to obtain the adapter directory under `.ai-engineering/adapters/<stack>/`. Pass the resolved adapter path to the build agent so it loads `conventions.md`, `tdd_harness.md`, `security_floor.md`, and `examples/` into context before writing code. `spec_stack` precedence: spec frontmatter `stack:` field over file-extension inference. `UnknownStackError` halts the task with a clear "no adapter for this stack" message.
3. **Execute kernel**: see `.codex/skills/_shared/execution-kernel.md`. Build wraps each task with the kernel (Sub-flow 1 dispatch -> Sub-flow 2 build-verify-review -> Sub-flow 3 artifact collection -> Sub-flow 4 board sync). As each task reaches a terminal state, update `.ai-engineering/specs/plan.md` immediately before dispatching the next task. Do not defer checkbox/status writes to the end of the phase or the end of the spec. The pre/post wrappers above and below remain build-specific.
4. **Quality check** -- read `handlers/quality.md` and execute: Verify+Review on full changeset, max 2 rounds.
5. **Deliver** -- read `handlers/deliver.md` and execute: PR via ai-pr with quality report.

## Resume Protocol

When invoked with `--resume`, use observable evidence only. Never guess hidden state. The build skill is the canonical implementation gateway (D-127-11) — replaces the legacy `/ai-build` slash command:

1. **Missing or placeholder plan**: if `.ai-engineering/specs/plan.md` is missing or still contains the placeholder `# No active plan`, STOP and run `/ai-plan`.
2. **Incomplete task execution**: if `.ai-engineering/specs/plan.md` still has unchecked task checkboxes, resume at the first incomplete phase. Skip completed tasks.
3. **Quality evidence missing**: if all task checkboxes are complete but `.ai-engineering/specs/plan.md` does not contain a `## Quality Rounds` section, resume at the Quality Check step. Read `handlers/quality.md`.
4. **Quality evidence present**: resume at the Deliver step. `handlers/deliver.md` is responsible for detecting whether an open PR already exists and either entering the watch-and-fix loop or creating/updating the PR.
5. **Conflicting evidence**: choose the earliest safe step and log why. Safety wins over convenience.

## Handler Dispatch Table

| Phase         | Handler               | Agent Pattern            |
| ------------- | --------------------- | ------------------------ |
| Quality Check | `handlers/quality.md` | Verify + Review parallel |
| Deliver       | `handlers/deliver.md` | PR pipeline + cleanup    |

## Common Mistakes

- Dispatching without an approved plan.
- Giving subagents the entire codebase context (scope them tightly).
- Skipping the two-stage review.
- Continuing past a BLOCKED task without user input.
- Batch-updating `plan.md` only at the end instead of updating it when each task closes.
- Modifying test files from a RED phase during a GREEN phase task.
- Skipping the quality check after task execution.

## Examples

### Example 1 — start fresh execution

User: "the plan is approved, go"

```
/ai-build
```

Reads `plan.md`, dispatches one agent per task with fresh context, runs two-stage review per deliverable, updates `plan.md` checkboxes, transitions board state, hands off to `/ai-pr` for delivery.

### Example 2 — resume after interruption

User: "resume the build from where we crashed"

```
/ai-build --resume
```

Reads `plan.md`, identifies the next un-checked task, re-enters at the correct state.

## Integration

Called by: user directly post-`/ai-plan` approval. Calls: `ai-build` agent, `ai-verify`, `ai-review`, `/ai-pr`, `/ai-board sync`. Reads: `_shared/execution-kernel.md`. Transitions to: PR merge, or back to `/ai-plan`. See also: `/ai-autopilot` (multi-concern + `--backlog` for backlog), `/ai-resolve-conflicts`.

$ARGUMENTS
