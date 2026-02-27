---
name: cleanup
description: "Full repository hygiene: status snapshot, sync, prune, branch cleanup, and spec lifecycle reset."
version: 2.0.0
category: workflows
tags: [git, branch, cleanup, hygiene, spec, status]
metadata:
  ai-engineering:
    requires:
      bins: [git]
    scope: read-write
    token_estimate: 1200
---

# Repository Cleanup Workflow

## Purpose

Execute full repository hygiene — branch cleanup, remote status assessment, and spec lifecycle reset. The single session-start primitive for the framework. Replaces the former `/pre-implementation` flow (which was absorbed into `/cleanup` + `/create-spec`).

## Trigger

- Command: `/cleanup`.
- Context: after merging a pull request, between tasks, at session start, or when preparing for `/create-spec`.

## Procedure

### Phase 0: Status

1. **Repository health snapshot** — run `ai-eng maintenance repo-status` or equivalent logic.
   - Remote branches: list with ahead/behind relative to default branch.
   - Open PRs: list via `gh pr list` (graceful fallback if `gh` unavailable).
   - Stale branches: branches with no commits in >30 days.
   - Cleanup candidates: merged + stale branches.
2. **Display status** — render the snapshot as a Markdown summary.
3. **Informational only** — this phase does not block subsequent phases.

### Phase 1: Sync

4. **Identify base branch** — determine the default branch (`main` or `master`).
5. **Check working tree** — if dirty, warn and stop. Do not stash automatically.
6. **Switch to base** — `git checkout <base-branch>`.
7. **Pull latest** — `git pull --ff-only origin <base-branch>`.

### Phase 2: Prune

8. **Fetch and prune** — `git fetch --prune origin` to remove stale remote-tracking references.

### Phase 3: Cleanup

9. **Delete merged branches** — identify branches fully merged into the base branch.
   - `git branch --merged <base>` excluding protected branches (`main`, `master`).
   - Delete each with `git branch -d <branch>`.

10. **Delete squash-merged branches** — identify branches whose remote tracking branch is gone.
    - `git branch -v` and filter for `[gone]` status.
    - Delete each with `git branch -D <branch>`.
    - These are branches merged via squash merge on the remote, where `--merged` detection fails.

11. **Report summary** — display results.
    - Branches deleted (merged).
    - Branches deleted (squash-merged / gone).
    - Remote refs pruned.
    - Branches skipped (if any).

### Phase 4: Spec Reset

12. **Check active spec** — read `_active.md` frontmatter to determine the current active spec.
    - If it points to a completed spec (has `done.md` or `tasks.md` with `completed == total`), flag for reset.
13. **Find orphan specs** — scan `context/specs/` for completed specs outside `archive/`.
    - Detection: has `done.md`, or `tasks.md` with `completed == total`.
14. **Archive completed specs** — move completed spec directories to `specs/archive/`.
15. **Reset `_active.md`** — write clean frontmatter with `active: null` and "No active spec — ready for `/create-spec`".
16. **Report spec reset** — display: specs archived, active reset, ready state.

## Output Contract

- Terminal output showing each phase result.
- Phase 0: repository status snapshot (remote branches, PRs, stale, candidates).
- Phase 3: branch cleanup summary (deleted count, pruned count, skipped count).
- Phase 4: spec reset summary (specs archived, active cleared, orphans).
- Final confirmation: current branch and status.

## Governance Notes

- Protected branches (`main`, `master`) are never deleted.
- Only `git branch -d` (safe delete) for merged branches; `git branch -D` (force) only for `[gone]` branches whose remote was already deleted.
- No destructive git operations beyond branch deletion.
- No `--no-verify` usage.
- If `git pull --ff-only` fails (diverged history), warn and stop — do not force-pull.
- Spec archival is a move operation, not a delete — completed specs are preserved in `archive/`.
- If `_active.md` points to an in-progress spec (not completed), it is left unchanged.

## References

- `skills/govern/create-spec/SKILL.md` — spec creation that composes `/cleanup` before branch creation.
- `skills/dev/references/git-helpers.md` — git helper patterns (protected branch check, default branch detection).
- `standards/framework/core.md` — protected branch rules and enforcement.
