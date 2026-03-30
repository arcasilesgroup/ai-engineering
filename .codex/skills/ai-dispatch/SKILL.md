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
3. **Guard advisory** -- before dispatching any build task, invoke the Guard agent (`ai-guard`) in `gate` mode for governance advisory. Fail-open: if guard is unavailable or errors, log warning and continue -- never block dispatch.
4. **Build DAG** -- parse task dependencies, identify parallel groups
5. **Execute phase by phase** -- for each phase:
   a. Dispatch one subagent per task (fresh context window)
   b. Each subagent receives: task description, file scope, boundaries, constraints
   c. Run two-stage review on deliverable (see below)
   d. Update task status in plan.md
   e. Check phase gate before advancing
6. **Track progress** -- update plan.md checkboxes after each task
7. **Quality check** -- read `handlers/quality.md` and execute: Verify+Review on full changeset, max 2 rounds
8. **Deliver** -- read `handlers/deliver.md` and execute: PR via ai-pr with quality report

## Task Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| `DONE` | Task completed, reviews passed | Check off, advance |
| `DONE_WITH_CONCERNS` | Completed but reviewer flagged issues | Check off, log concerns for follow-up |
| `NEEDS_CONTEXT` | Agent needs information not in the plan | Pause, ask user, then resume |
| `BLOCKED` | Cannot proceed (dependency, access, ambiguity) | STOP execution, re-plan |

## Two-Stage Review (Per-Task)

Every task deliverable goes through two reviews before marking DONE. This is the per-task quality check during Phase 4 execution. A separate full-changeset quality check runs in Phase 6 (see `handlers/quality.md`).

### Stage 1: Spec Compliance

- Does the deliverable match the task description?
- Does it satisfy the acceptance criteria from spec.md?
- Are all file scope boundaries respected (no out-of-scope changes)?

### Stage 2: Code Quality

- Stack validation passes (ruff, tsc, cargo check, etc.)
- No new lint warnings introduced
- Test coverage maintained or improved
- No governance advisory warnings from guard

If either stage fails: fix and re-review (max 2 retries per stage).

## DAG Construction

**Independent** (can run in parallel):
- Different file scopes with no overlap
- No producer-consumer relationship
- Different modules with no shared state

**Dependent** (must serialize):
- Task B reads files Task A creates
- Task B depends on Task A's output
- Both modify governance artifacts (`.ai-engineering/` must serialize)
- Plan explicitly orders them

## Subagent Context

Each subagent receives a focused context window:

```yaml
task: T-2.1
description: "Implement the parse_config function"
agent: ai-build
scope:
  files: ["src/config.py", "tests/test_config.py"]
  boundaries: ["Do NOT modify src/main.py", "Do NOT touch hooks/"]
constraints:
  - "Follow existing ConfigParser pattern in src/base_config.py"
  - "TDD: test files from T-2.0 are IMMUTABLE"
contexts:
  languages: [".ai-engineering/contexts/languages/python.md"]
  frameworks: [".ai-engineering/contexts/frameworks/backend-patterns.md"]
  team: [".ai-engineering/contexts/team/*.md"]
gate:
  post: ["ruff check", "pytest tests/test_config.py"]
```

### Context Injection

The dispatcher detects the stack from `providers.stacks` in `.ai-engineering/manifest.yml` and resolves applicable context file paths. These paths are included in the `contexts:` field of the subagent YAML. The subagent reads these files before executing its task. This acts as a safety net -- even if a skill lacks its own Step 0, contexts are injected by the dispatcher.

## Stuck Protocol

If a task fails after 2 retries:

1. Mark task as BLOCKED with reason
2. Check if other tasks in the phase can proceed independently
3. If phase is blocked entirely: STOP execution
4. Report to user: what failed, what was tried, options (re-plan, skip, manual fix)

Never loop silently. Never retry the same approach more than twice.

## Progress Tracking

Update plan.md in real-time:

```markdown
- [x] T-1.1: Create config module @ai-build -- DONE
- [x] T-1.2: Add validation logic @ai-build -- DONE_WITH_CONCERNS (perf warning)
- [ ] T-2.1: Write integration tests @ai-build -- IN PROGRESS
- [ ] T-2.2: Security scan @ai-verify -- PENDING
```

## Resume Protocol

When invoked with `--resume`, read `specs/plan.md` and determine re-entry point:

1. **Incomplete tasks remain**: resume at the first incomplete phase. Skip completed tasks.
2. **All tasks DONE but no quality check recorded**: resume at Phase 6 (Quality Check). Read `handlers/quality.md`.
3. **Quality passed but no PR created**: resume at Phase 7 (Deliver). Read `handlers/deliver.md`.
4. **PR exists but not merged**: resume at watch-and-fix loop per `handlers/deliver.md`.

## Handler Dispatch Table

| Phase | Handler | Agent Pattern |
|-------|---------|---------------|
| 6. Quality Check | `handlers/quality.md` | Verify + Review parallel |
| 7. Deliver | `handlers/deliver.md` | PR pipeline + cleanup |

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
- **Reads**: `ai-verify/SKILL.md`, `ai-review/SKILL.md`, `ai-pr/SKILL.md` (thin orchestrator, embedded at dispatch time)
- **Transitions to**: PR merge (after deliver), or back to `/ai-plan` (if re-plan needed)

$ARGUMENTS
