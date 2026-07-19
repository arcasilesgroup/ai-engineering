---
name: ai-build
description: "Canonical implementation gateway: reads approved plan.md, resolves stack from manifest, deterministic-routes each task to its adapter, dispatches the build agent in an isolated worktree, runs TDD self-validation per task, then a single final quality loop with one bounded quality-remediation pass on the full changeset before /ai-pr. Trigger for 'go', 'start building', 'execute the plan', 'implement it', 'lets do this', 'build the plan', 'resume', 'continue'. Not without an approved plan; run /ai-plan first. Not for multi-concern specs needing decomposition; use /ai-autopilot instead. Not for a single function or subcomponent; use /ai-code."
effort: cheap
argument-hint: "[spec-NNN | --resume | --no-hitl]"
---

# Build

Execution engine for approved plans: reads plan.md, dispatches one subagent per task (fresh context, TDD self-validation), then runs a single final quality loop with one bounded remediation pass on the full changeset before `/ai-pr`. Requires an approved plan (run `/ai-plan` first; resume with `/ai-build --resume`); route multi-concern plans (≥ 3 concerns or ≥ 10 files) to `/ai-autopilot` instead, and STOP to re-plan if stuck.

## Workflow

Principles: §10.5 TDD (per-task RED/GREEN/REFACTOR self-validation), §10.4 DRY (plan patch-hunks unlock cheap-tier execution downstream).

0. **Preflight** — verify `.ai-engineering/specs/plan.md`, `.claude/skills/_shared/execution-kernel.md`, `handlers/quality.md`, `handlers/deliver.md` exist. Any missing → STOP and report the exact path(s). Never improvise missing orchestration.
0b. **Executor route gate** (spec-145) — read plan frontmatter `status` + `execution_route.executor`. `status` ≠ `approved` → STOP for approval. `executor: autopilot` → refuse this run, print `execution_route.safe_next_command` (normally `/ai-autopilot`), STOP. Route metadata absent → legacy behavior.
1. **Board sync (in_progress)** — read `.ai-engineering/specs/spec.md` frontmatter `refs`; for each ref whose hierarchy rule ≠ `never_close` (user_stories/tasks/bugs/issues), `/ai-board sync in_progress <ref>` (fail-open). Then read `<spec_id>` from `spec.md` `spec:` and `python .ai-engineering/scripts/spec_lifecycle.py start <spec_id>` (APPROVED→IN_PROGRESS; mirrors `status: in-progress`; fail-open — non-zero exit does NOT block DAG construction).
2. **Advise advisory** — invoke the `ai-advise` agent in `gate` mode before dispatching any build task (fail-open: log + continue, never block dispatch).
2b. **Stack routing** (D-127-06 / sub-008, spec-128 D-128-01) — per task, call `tools.skill_app.deterministic_router.resolve_adapter(task_path, spec_stack)` for the overrides dir `.ai-engineering/overrides/<stack>/`; pass it to the build agent to load `conventions.md`, `tdd_harness.md`, `security_floor.md`, `examples/` before writing code. `spec_stack` precedence: spec frontmatter `stack:` over file-extension inference. `UnknownStackError` halts the task ("no overrides for this stack").
2c. **Model dispatch** (D-131-08 / sub-003, §10.4 DRY) — per task, inspect the plan.md block:
    - `Patch (deterministic):` present AND no synthesis hint → `effort=cheap` (mechanical).
    - patch absent OR synthesis hint present → `effort=mid` (judgment).
    - operator `--max-effort` OR task tagged `architecture: true` → `effort=high` (deep-architecture override).
    Log via `emit_agent_dispatched(..., metadata={"effort": <effort>, "patch_present": <bool>})`. Investing in `/ai-plan` (exhaustive patch-ready output) is what unlocks cheap-tier execution downstream (D-131-08).
2d. **No-HITL contract** (D-134-03) — if `--no-hitl` is set, read `handlers/no-hitl.md` and apply: single-concern gate, `NEEDS_CONTEXT → BLOCKED` promotion, `quality_loop_blocked → exit 78`, `--no-watch` implied for delivery, no auto-retry. Absent flag → default behavior unchanged.
3. **Execute kernel** — `.claude/skills/_shared/execution-kernel.md`. Wrap each task (Sub-flow 1 dispatch → 2 build self-validation TDD RED/GREEN/REFACTOR → 3 artifact collection → 4 board sync). As each task reaches a terminal state, update `.ai-engineering/specs/plan.md` immediately before dispatching the next task. Do not defer checkbox/status writes to the end of the phase or the end of the spec.
4. **Quality check** — read `handlers/quality.md`: Verify+Review on the full changeset, single round, fail-loud with ONE bounded quality-remediation pass. Blocker/critical/high findings may be fixed once when scoped to quality-loop evidence; remaining blocker/critical/high findings → STOP + escalate (no second remediation pass).
5. **Deliver** — read `handlers/deliver.md`: PR via `/ai-pr` with quality report. The deliver/quality handlers render the operator report through the value block (`value-lens.md`).

## Resume Protocol

`--resume` uses observable evidence only — never guess hidden state. The build skill is the canonical implementation gateway (D-127-11).

1. **Missing/placeholder plan**: `plan.md` missing or still `# No active plan` → STOP, run `/ai-plan`.
2. **Incomplete tasks**: unchecked checkboxes → resume at the first incomplete phase; skip completed tasks.
3. **Quality evidence missing**: all tasks checked but no `## Quality Outcome` section → resume at Quality Check (`handlers/quality.md`).
4. **Quality evidence present**: resume at Deliver; `handlers/deliver.md` detects an existing open PR and enters watch-and-fix or creates/updates the PR.
5. **Conflicting evidence**: choose the earliest safe step and log why. Safety over convenience.

## Handler Dispatch Table

| Phase         | Handler               | Agent Pattern                       |
| ------------- | --------------------- | ----------------------------------- |
| Quality Check | `handlers/quality.md` | Verify + Review parallel            |
| Deliver       | `handlers/deliver.md` | PR pipeline + cleanup               |
| No-HITL       | `handlers/no-hitl.md` | deterministic / single-concern only |

## Common Mistakes

- Giving subagents the whole codebase — scope tightly.
- Continuing past a BLOCKED task without user input.
- Batch-updating `plan.md` at the end instead of per task close.
- Modifying RED-phase test files during a GREEN-phase task.
- Invoking `--no-hitl` on a multi-concern plan — use `/ai-autopilot`.

## Examples

User: "the plan is approved, go"

```
/ai-build
```

Reads `plan.md`, dispatches one agent per task with fresh context; each task self-validates via TDD; the final quality loop verifies the full changeset and may consume one bounded quality-remediation pass before handing off to `/ai-pr`.

## Integration

Called by: user directly post-`/ai-plan` approval. Calls: `ai-build` agent, `ai-verify`, `ai-review`, `/ai-pr`, `/ai-board sync`. Reads: `_shared/execution-kernel.md`. Transitions to: PR merge, or back to `/ai-plan`. See also: `/ai-autopilot` (multi-concern + `--backlog`), `/ai-resolve-conflicts`.

$ARGUMENTS
