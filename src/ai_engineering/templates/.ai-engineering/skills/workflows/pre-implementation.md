# Pre-Implementation Workflow

## Purpose

Execute branch hygiene before starting any new implementation work. Ensures the local repository is clean, up-to-date, and free of stale branches before creating a new feature branch.

## Trigger

- Context: AI agent begins implementation of a spec, feature, or task.
- Timing: runs automatically at the start of any governed implementation session.
- Also callable manually: `ai-eng maintenance branch-cleanup`.

## Procedure

### Phase 1: Sync

1. **Identify base branch** — determine the base branch (`main` or `master`) from the repository.
2. **Switch to base** — `git checkout <base-branch>`. If working tree is dirty, stash or warn.
3. **Pull latest** — `git pull --ff-only` on the base branch.

### Phase 2: Prune

4. **Fetch and prune** — `git fetch --prune` to remove stale remote-tracking references.
5. **List merged branches** — `git branch --merged <base>` to find branches that have been fully merged.

### Phase 3: Cleanup

6. **Delete merged branches** — `git branch -d <branch>` for each merged branch, excluding:
   - Protected branches (`main`, `master`).
   - The currently checked-out branch.
7. **Report results** — display summary of deleted branches, skipped branches, and any errors.

### Phase 4: Proceed

8. **Create feature branch** — `git checkout -b <branch-name>` for the new work.
9. **Confirm ready** — display confirmation that the workspace is clean and ready for implementation.

## Output Contract

- Summary showing: branches deleted, branches skipped, remote refs pruned.
- Any errors encountered during cleanup.
- Confirmation that the repository is ready for new work.

## Governance Notes

- Protected branches are never deleted. This is enforced at the code level.
- Only merged branches are deleted with safe delete (`-d`). Unmerged branches require explicit `--force`.
- Network failures during fetch/prune are non-fatal warnings; cleanup proceeds with local state.
- This workflow is advisory when run automatically — it does not block implementation if cleanup fails.

## References

- `standards/framework/core.md` — non-negotiables and branch protection rules.
- `skills/workflows/commit.md` — commit flow that happens after implementation.
- `skills/lifecycle/create-spec.md` — spec creation that precedes implementation.
