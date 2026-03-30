---
name: ai-run
description: Use when a backlog of work items should run autonomously end to end without waiting for human checkpoints after invocation. Supports GitHub Issues, Azure Boards, and local markdown task lists; plans safely, executes through ai-build, converges with review and verify, and delivers via PR.
effort: max
argument-hint: "github|azure|markdown <source> [--single|--batch] [--resume] [--no-watch]"
mode: agent
tags: [orchestration, autonomous, backlog, github, azure, delivery]
---


# Run

## Purpose

Autonomous backlog orchestration for approved no-HITL execution. `ai-run` takes a set of work items, normalizes them into a common run model, performs architecture-aware planning, executes through bounded `ai-build` packets, converges with `ai-review` and `ai-verify`, and delivers through the existing PR workflow.

This skill is intentionally thin. It owns sequence, state, branch topology, and resume. It does not replace `ai-build`, `ai-review`, `ai-verify`, `ai-pr`, or `ai-board-sync`.

## When to Use

- Backlog execution should continue without human approval after invocation.
- The source items come from GitHub Issues, Azure Boards, or a markdown task list.
- The work needs safe sequencing, explicit consolidation, and PR-based delivery.
- `/ai-dispatch` is too narrow because the input is a backlog, not a single approved task graph.

## When NOT to Use

- A single approved plan already exists and standard `/ai-dispatch` is enough.
- The work needs human sign-off between phases.
- The work requires destructive DDL, risky infra apply steps, or another action that already requires explicit approval.

## Run Model

`ai-run` operates in two delivery topologies:

| Mode | Use When | Integration Surface |
|------|----------|---------------------|
| `single-item` | One isolated item or batch overhead is unnecessary | worker branch -> PR |
| `multi-item` | Multiple items need safe consolidation | worker branches/worktrees -> `run/<run-id>` -> PR |

Invocation is the approval gate. All later gates are machine-enforced.

## Process

### Step 0: Validate

1. If `--resume` is present, read `.ai-engineering/runs/<run-id>/manifest.md` and jump to the Resume Protocol in `handlers/phase-deliver.md`.
2. Read the reference bundle:
   - `references/architecture.md`
   - `references/phases.md`
   - `references/run-manifest.md`
   - `references/provider-matrix.md`

### Step 1: Intake and Baseline Explore

Read `handlers/phase-intake.md` and execute:

1. Select the source provider (GitHub, Azure Boards, markdown).
2. Create or resume the run-state directory.
3. Perform mandatory repository-wide baseline exploration via `ai-explore` before any DAG or wave planning.
4. Normalize source items into the shared item schema in the run manifest.

### Step 2: Item Planning

Read `handlers/phase-item-plan.md` and execute:

1. Deepen ambiguous or risky items with scoped exploration.
2. Produce per-item `spec.md` and `plan.md` under `.ai-engineering/runs/<run-id>/items/<item-id>/`.
3. Define file boundaries, checks, acceptance criteria, and close policy per item.

### Step 3: DAG and Wave Planning

Read `handlers/phase-orchestrate.md` and execute:

1. Build the overlap matrix and dependency DAG from item plans plus architectural evidence.
2. Default to serialization when uncertainty is non-trivial.
3. Build bounded `ai-build` task packets for each ready item.

### Step 4: Execute and Promote

Read `handlers/phase-execute.md` and execute:

1. Dispatch `ai-build` per item with scoped context and explicit post-gates.
2. Run item-level `ai-review` and `ai-verify platform`.
3. Promote passing item branches locally into the integration surface.
4. Run integration gates after every promotion.

### Step 5: Deliver and Resume

Read `handlers/phase-deliver.md` and execute:

1. Delegate final PR creation and remote CI watch/fix to `ai-pr`.
2. Use `ai-board-sync` for lifecycle transitions where policy allows.
3. Use `ai-resolve-conflicts` when automated rebases or promotions hit conflicts.
4. Finalize the run manifest and cleanup after merge.

## Thin Orchestrator Principle

`ai-run` does not embed provider logic, build logic, review logic, or PR logic. It reads and reuses:

- `.github/agents/explore.agent.md`
- `.github/agents/build.agent.md`
- `.github/skills/ai-review/SKILL.md`
- `.github/skills/ai-verify/SKILL.md`
- `.github/skills/ai-pr/SKILL.md`
- `.github/skills/ai-board-sync/SKILL.md`
- `.github/skills/ai-resolve-conflicts/SKILL.md`

When those skills improve, `ai-run` inherits the improvement automatically.

## Governance

- `ai-build` remains the only write-capable implementation agent.
- `ai-run` never pushes directly to a protected branch.
- Multi-item execution is incomplete until changes converge locally on `run/<run-id>`.
- Review and verify are required at item, integration, and final delivery levels.
- Board sync is fail-open. Delivery and governance are fail-closed.

## Quick Reference

```text
/ai-run github "repo issues"
/ai-run azure "current sprint"
/ai-run markdown docs/mega-plan.md
/ai-run github "repo issues" --single
/ai-run github "repo issues" --resume
/ai-run azure "AB#120,AB#121" --no-watch
```

## Integration

- **Called by**: user directly when no-HITL backlog execution is desired.
- **Calls**: `ai-explore`, `ai-build`, `ai-review`, `ai-verify`, `ai-pr`, `ai-board-sync`, `ai-resolve-conflicts`
- **Writes state to**: `.ai-engineering/runs/<run-id>/`
- **Transitions to**: merged PR, blocker report, or deferred run state

## References

- `references/architecture.md`
- `references/phases.md`
- `references/run-manifest.md`
- `references/provider-matrix.md`

$ARGUMENTS
