---
name: cleanup
version: 1.0.0
category: workflows
tags: [git, branch, cleanup, hygiene]
requires:
  bins: [git]
---

# Branch Cleanup Workflow

## Purpose

Execute branch cleanup after merging a PR or at the start of a new session. Switches to the base branch, pulls latest, prunes stale remote-tracking references, and deletes local branches that have been merged or squash-merged. Standalone counterpart to the cleanup phases of `/pre-implementation` — without creating a new branch.

## Trigger

- Command: `/cleanup`.
- Context: after merging a pull request, between tasks, or when starting a session to clear stale branches.

## Procedure

### Phase 1: Sync

1. **Identify base branch** — determine the default branch (`main` or `master`).
2. **Check working tree** — if dirty, warn and stop. Do not stash automatically.
3. **Switch to base** — `git checkout <base-branch>`.
4. **Pull latest** — `git pull --ff-only origin <base-branch>`.

### Phase 2: Prune

5. **Fetch and prune** — `git fetch --prune origin` to remove stale remote-tracking references.

### Phase 3: Cleanup

6. **Delete merged branches** — identify branches fully merged into the base branch.
   - `git branch --merged <base>` excluding protected branches (`main`, `master`).
   - Delete each with `git branch -d <branch>`.

7. **Delete squash-merged branches** — identify branches whose remote tracking branch is gone.
   - `git branch -v` and filter for `[gone]` status.
   - Delete each with `git branch -D <branch>`.
   - These are branches merged via squash merge on the remote, where `--merged` detection fails.

8. **Report summary** — display results.
   - Branches deleted (merged).
   - Branches deleted (squash-merged / gone).
   - Remote refs pruned.
   - Branches skipped (if any).

## Output Contract

- Terminal output showing each phase result.
- Summary table: deleted count, pruned count, skipped count.
- Final confirmation: current branch and status.

## Governance Notes

- Protected branches (`main`, `master`) are never deleted.
- Only `git branch -d` (safe delete) for merged branches; `git branch -D` (force) only for `[gone]` branches whose remote was already deleted.
- No destructive git operations beyond branch deletion.
- No `--no-verify` usage.
- If `git pull --ff-only` fails (diverged history), warn and stop — do not force-pull.

## References

- `skills/workflows/pre-implementation.md` — full pre-implementation flow that includes cleanup + branch creation.
- `skills/utils/git-helpers.md` — git helper patterns (protected branch check, default branch detection).
- `standards/framework/core.md` — protected branch rules and enforcement.
