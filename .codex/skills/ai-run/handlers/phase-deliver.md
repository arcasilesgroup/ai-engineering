# Handler: Phase 5 -- DELIVERY, WATCH/FIX, AND RESUME

## Purpose

Deliver the integrated run through the existing PR workflow, keep board lifecycle in sync, and support crash-safe resume from run-state artifacts.

## Procedure

### Step 1 -- Choose delivery branch

- `single-item` mode -> deliver the worker branch directly
- `multi-item` mode -> deliver `run/<run-id>`

Never push directly to the protected default branch.

### Step 2 -- Final local gate

Before any push:

1. Run required local checks.
2. Run final `ai-review`.
3. Run final `ai-verify platform`.

If the local gate fails, fix locally before invoking `ai-pr`.

### Step 3 -- Delegate PR delivery

Read `.codex/skills/ai-pr/SKILL.md` and delegate the final PR flow.

`ai-run` must not reimplement:

- pre-push gates
- PR creation or update
- auto-complete
- remote CI watch/fix
- merge detection

### Step 4 -- Board lifecycle

Where hierarchy policy allows:

- mark active items `in_review` on PR creation via `ai-board-sync`
- let merge closure follow provider rules
- never auto-close `feature` refs

### Step 5 -- Resume protocol

Resume is state-driven from `.ai-engineering/runs/<run-id>/manifest.md`.

Re-entry rules:

- no item plans -> resume at Phase 2
- no DAG -> resume at Phase 3
- runnable items remain -> resume at Phase 4
- delivery branch exists but PR missing -> resume at Phase 5 Step 3
- PR exists and is open -> delegate to `ai-pr` watch/fix
- PR merged -> finalize and cleanup

### Step 6 -- Finalize

After merge:

- finalize run status
- record final delivery URL and merge commit
- cleanup item branches/worktrees where safe
- cleanup `run/<run-id>` where safe

## Completion States

| State | Meaning |
|-------|---------|
| `completed` | Merged into the protected default branch |
| `blocked` | Stopped on a true blocker with evidence |
| `deferred` | Valid item left intentionally for a later run or dependency |

## Failure Modes

| Condition | Action |
|-----------|--------|
| PR creation fails | Stop and report. Preserve the delivery branch. |
| Same CI check fails 3 times in watch/fix | Stop per `ai-pr` protocol. |
| Conflict resolution becomes unsafe | Stop and report conflicting files and why automation stopped. |
