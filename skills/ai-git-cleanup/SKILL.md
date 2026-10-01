---
name: ai-git-cleanup
description: >-
  Removes finished local git work in one automatic pass, with no question and
  no name to type: dead worktrees first (`git worktree remove`, then `git
  worktree prune`), then branches already merged into the local `main`.
  Trigger for "tidy up", "tidy up these branches", "tidy branches", "delete
  old branches", "start fresh", "limpieza de branches", "limpia branches", or
  by naming ai-git-cleanup. A branch that is not merged into `main` is left
  alone: the pass never force-deletes and no name is ever asked. Not for
  pushing, not for remote branches, not for opening a pull request.
license: Apache-2.0
---

# ai-git-cleanup — remove finished local work in one pass

Say a cleanup phrase and the pass runs itself. It deletes only work that is
finished — worktrees whose branch is merged into the local `main`, and those
merged branches — and it never asks a question and never takes a name. Anything
unfinished is left exactly where it is. Run the steps in order, from the
primary checkout, and report what each one did.

## The pass

1. **Remove the dead worktrees.** For every worktree whose branch is already
   merged into the local `main`, run `git worktree remove <path>`. A dirty
   worktree is left in place: the removal is never forced, so an uncommitted
   change keeps its worktree.
2. **Prune the stale ones.** Run `git worktree prune` to drop registrations
   whose directory is already gone. It removes no live worktree.
3. **Delete the merged branches.** Run `git branch --delete-merged refs/heads/main` — it deletes only branches whose upstream is the local
   `main` and that are fully merged into it, and never the branch checked out
   here.
4. **Fall back for a merged branch without that upstream.** List them with
   `git branch --merged main`, then delete each listed branch with
   `git branch -d <branch>`. The delete refuses any branch that is not fully
   merged, so an unmerged branch survives and its work is preserved.

## Safety invariants

- **Never force-delete anything.** No forced branch delete and no forced
  worktree removal: a refusal is the correct outcome and is reported as kept,
  never retried with force.
- **An unmerged branch is never deleted.** Both the delete-merged pass and the
  fallback delete only what is already merged into `main`; a branch with work
  not in `main` is left alone.
- **No name is ever asked, and there is no interactive question.** The pass
  decides from git state alone; it never prompts for a branch or worktree name.
- **The local `main` is the only destination that matters.** No remote is
  read for the merge decision and nothing is ever pushed.
- **No deletion starts before the worktrees holding a merged branch are
  gone.** A branch checked out in a worktree cannot be deleted; removing that
  worktree first is what lets the pass finish.

## Lifecycle

Lane: any
Writes: nothing
Read by: the person who asked for the cleanup
Dies: after each pass; the report is a snapshot of that moment
Next: none
