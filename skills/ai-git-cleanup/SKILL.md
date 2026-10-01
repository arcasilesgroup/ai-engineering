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
unfinished, unprovable, or detached is left exactly where it is. Run the steps
in order, from the primary checkout, and report what each one did.

## The pass

1. **Remove the dead worktrees.** For each worktree, read two facts before
   touching it: whether its HEAD is on a branch
   (`git -C <path> symbolic-ref -q HEAD`) and whether it holds any uncommitted
   content, ignored files included
   (`git -C <path> status --porcelain --ignored`). Remove it with
   `git worktree remove <path>` only when the HEAD check names a branch that is
   already merged into the local `main` **and** the status output is empty.
   Otherwise skip it and report it kept with the reason:
   - **No branch (detached HEAD).** `git worktree remove` exits 0 on a clean
     detached worktree and the commits it holds become unreachable from every
     ref, so the pass never removes one: report it kept as "detached, no branch
     to prove".
   - **Any uncommitted content.** The removal is never forced, and a worktree
     whose only content is gitignored (a `.env`, ignored screenshots) is removed
     without force and that content destroyed — so any non-empty status, tracked,
     untracked, or ignored, keeps the worktree: report it kept and say what the
     status listed.
   Never force a removal.
2. **Prune the stale ones.** Run `git worktree prune` to drop registrations
   whose directory is already gone. It removes no live worktree.
3. **Delete the merged branches** (needs git ≥ 2.56.0). Run `git branch --delete-merged refs/heads/main` — it deletes only branches whose upstream is
   the local `main` and that are fully merged into it, and never the branch
   checked out here. The option exists only from git 2.56.0: on any older git it
   fails with an `unknown option` error, and that is not a pass failure — steps 1
   and 2 have already run — so report it and continue to step 4 for every merged
   branch.
4. **Fall back for a merged branch without that upstream.** List the candidates
   with `git branch --merged main`, then drop the current branch and any branch
   checked out in another worktree (the lines decorated `*` or `+`) and read each
   remaining name without its decoration. Delete each with
   `git branch -d <branch>`. A refusal is a keep, and it is never retried: `-d`
   tests the branch against its own upstream, so a branch merged into `main`
   whose upstream points elsewhere (a lagging `origin/main`, a
   `refs/heads/behind`) is refused — report that branch kept and name the
   upstream mismatch as the reason.

## Safety invariants

- **Never force-delete anything.** No forced branch delete and no forced
  worktree removal: a refusal is the correct outcome and is reported as kept,
  never retried with force.
- **An unmerged branch is never deleted.** Both the delete-merged pass and the
  fallback delete only what is already merged into `main`; a branch with work
  not in `main` is left alone.
- **A worktree with no branch is never removed.** A detached HEAD has no branch
  to prove merged, so the pass keeps that worktree and reports it as detached:
  its commits never lose their only ref.
- **Uncommitted content keeps its worktree.** Tracked, untracked, or ignored —
  the status check covers all three, and a non-empty status is a keep.
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
