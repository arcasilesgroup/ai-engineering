# Execution Kernel (shared)

## Kernel: dispatch agent per task -> build-verify-review loop -> artifact collection -> board sync

Canonical inner loop reused by `/ai-dispatch`, `/ai-autopilot`, and `/ai-run`. Each consumer wraps the kernel with its own pre/post logic (single-task vs multi-spec waves vs backlog packets) but the per-task execution pattern is identical.

This file is read by an orchestrator at task time. It is NOT a skill (no frontmatter, not user-invocable) and does NOT replace consumer-specific governance, telemetry, or delivery sections.

---

## Sub-flow 1: Dispatch agent per task (fresh context)

For each task ready to run, dispatch ONE specialized agent in a fresh context window. Never let an agent carry context across tasks -- isolation is the point.

Required scope payload to the agent:

```yaml
task: <task-id>            # e.g. T-2.1 (dispatch), wave-3 sub-spec build (autopilot), item-7 (run)
description: <one-line>    # spec-derived, unambiguous
agent: ai-build|ai-verify|ai-review|ai-explore   # only ai-build writes code
scope:
  files: ["<path1>", "<path2>"]    # explicit scope, no codebase-wide reads
  boundaries: ["Do NOT modify <path>", "Do NOT touch hooks/"]
constraints:
  - "Follow existing pattern in <ref-file>"
  - "TDD: test files from earlier RED phase are IMMUTABLE"
contexts:
  languages: [".ai-engineering/contexts/languages/<lang>.md"]
  frameworks: [".ai-engineering/contexts/frameworks/<fw>.md"]
  team: [".ai-engineering/contexts/team/*.md"]
gate:
  post: ["ruff check", "pytest <file>"]   # stack-specific deterministic linters
```

Context injection: read `providers.stacks` from `.ai-engineering/manifest.yml`, resolve applicable context paths, pass paths (not content) so the subagent reads on demand. This is a safety net even when a skill omits its own Step 0.

DAG construction (independent vs dependent):
- Independent: different file scopes, no producer-consumer, no shared `.ai-engineering/` writes -> parallelize within a wave.
- Dependent: B reads files A creates, both touch governance artifacts, plan explicitly orders -> serialize.

---

## Sub-flow 2: Build-verify-review loop (per task)

After the dispatched agent completes, run two-stage review on the deliverable BEFORE marking the task DONE.

### Stage 1 -- Spec compliance
- Deliverable matches the task description?
- Acceptance criteria from `spec.md` satisfied?
- File-scope boundaries respected (no out-of-scope changes)?

### Stage 2 -- Code quality
- Stack validation passes (`ruff`, `tsc`, `cargo check`, `dotnet build`, etc.)
- No new lint warnings introduced
- Test coverage maintained or improved
- No governance advisory warnings from `ai-guard`
- Lint findings emitted as structured envelopes per `.ai-engineering/schemas/lint-violation.schema.json` (spec-119 D-119-05) -- prose violation labels are deprecated.

If any stage fails: dispatch a fix attempt and re-review. Max 2 retries per stage. After 2 failed retries, mark task BLOCKED and STOP execution -- never loop silently, never retry the same approach more than twice.

Task statuses (all consumers honor the same vocabulary):

| Status | Meaning | Action |
|--------|---------|--------|
| `DONE` | Task completed, both review stages passed | Check off, advance |
| `DONE_WITH_CONCERNS` | Completed but reviewer flagged non-blocking issues | Check off, log concerns |
| `NEEDS_CONTEXT` | Agent needs information not in the plan | Pause, ask user, then resume |
| `BLOCKED` | Cannot proceed (dependency, access, ambiguity) | STOP execution, escalate |

---

## Sub-flow 3: Artifact collection

Each task contributes artifacts that the next phase or consumer-specific quality loop reads:

- **Code changes** -- staged in working tree, batched by consumer (per-task for dispatch, per-wave for autopilot, per-item for run).
- **Self-Report** -- the agent writes a real/aspirational/stub/failing/invented/hallucinated classification for what it produced. Stored alongside the task deliverable (e.g., `sub-NNN/plan.md` for autopilot, `items/<id>/plan.md` for run, inline checkbox notes for dispatch).
- **Telemetry events** -- emitted via the hook system at phase transitions (e.g., `subspec_complete`, `quality_round`, `subspec_failed`). Never recorded only in agent memory.
- **Progress** -- update `plan.md` checkboxes in real time so the user can see current state at a glance. The moment a task reaches a terminal state (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`), write that status to disk before dispatching the next task. Never batch checkbox/status updates at phase end, quality time, or only after the whole spec finishes:

```markdown
- [x] T-1.1: Create config module @ai-build -- DONE
- [x] T-1.2: Add validation @ai-build -- DONE_WITH_CONCERNS (perf warning)
- [ ] T-2.1: Write integration tests @ai-build -- IN PROGRESS
- [ ] T-2.2: Security scan @ai-verify -- PENDING
```

Artifacts persist to disk so any phase can be audited post-hoc and so `--resume` can re-enter at the correct state.

---

## Sub-flow 4: Board sync

For each work-item reference in `.ai-engineering/specs/spec.md` frontmatter `refs` whose hierarchy rule is NOT `never_close` (i.e., user_stories, tasks, bugs, issues), invoke `/ai-board-sync` with the appropriate state transition (`in_progress` at task start, terminal state at task close).

Board sync is **fail-open**: do NOT block execution if the provider is unreachable, the credential is missing, or the work item type is read-only at the configured hierarchy. Log a warning and continue. Delivery and governance gates remain fail-closed; only board sync is fail-open.

Rationale: provider readiness should never gate local execution. The user can reconcile board state later via `/ai-board-sync --resume` once the provider is reachable.

---

## Stuck protocol

If a task fails after 2 retries:

1. Mark the task as `BLOCKED` with reason.
2. Check if other tasks in the current wave/phase can proceed independently -- continue them.
3. If the current wave/phase is blocked entirely, STOP execution and surface to the user: what failed, what was tried, options (re-plan, skip, manual fix).

Never loop silently. Never retry the same approach more than twice. Cascade-blocking dependents is mandatory when a producer task is BLOCKED.

---

## Consumers

This kernel is consumed by:

- `.claude/skills/ai-dispatch/SKILL.md` -- single-plan execution; consumer wraps the kernel per-task and runs Phase 5 quality + Phase 6 deliver after the loop completes.
- `.claude/skills/ai-autopilot/SKILL.md` -- multi-spec autonomous execution; consumer wraps the kernel per-wave (parallel sub-specs within a wave, DAG-driven across waves) before Phase 5 quality loop and Phase 6 deliver.
- `.claude/skills/ai-run/SKILL.md` -- backlog execution; consumer wraps the kernel per-item with bounded `ai-build` packets, integration gates after every promotion, and `ai-pr` for delivery.

When this kernel improves, all three orchestrators inherit the improvement automatically.
