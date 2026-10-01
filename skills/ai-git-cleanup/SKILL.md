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
   (`git -C <path> symbolic-ref -q HEAD`) and what uncommitted content it holds,
   ignored files included
   (`git -C <path> status --porcelain --ignored --untracked-files=normal` — the
   option is required: a `status.showUntrackedFiles=no` in the repository or the
   global config makes the bare command print nothing at all, so the read must
   force the listing itself; `normal` keeps a wholly ignored directory collapsed
   to one `!! dir/` line, so the report stays bounded and matches the list's
   `dir/` entries literally). Remove
   it with `git worktree remove <path>` only when the HEAD check names a branch
   that is already merged into the local `main`, the status read printed no
   warning, **and** every status entry is
   either absent or an ignored path on the regenerable list below. Otherwise skip
   it and report it kept with the reason:
   - **No branch (detached HEAD).** `git worktree remove` exits 0 on a clean
     detached worktree and the commits it holds become unreachable from every
     ref, so the pass never removes one: report it kept as "detached, no branch
     to prove".
   - **Uncommitted content that is not regenerable.** Tracked and untracked
     content always keeps the worktree, and so does any ignored path outside the
     list below — the removal is never forced, and git destroys ignored content
     silently (a `.env`, ignored screenshots). Report it kept and say what the
     status listed.
   - **Unreadable status.** `git status` exits 0 while warning on stderr when it
     cannot read a subdirectory or a path, so a read that warned is not a clean
     worktree: keep it and report the warning. The doubt is resolved by keeping,
     never by removing what the read did not see.
   - **Ignored content that is all regenerable.** Two groups, and nothing else:
     the paths this framework rebuilds — `node_modules/`, `dist/`, `coverage/`,
     `.stryker-tmp/`, `reports/`, `.ai-engineering/receipts/`,
     `.ai-engineering/cache/`, `.ai-engineering/workflow/playwright/` — plus the
     system and editor noise this repository already ignores in `.gitignore`:
     `*.bun-build`, `.claude/reviews/`, and `*.DS_Store` (macOS writes a
     `.DS_Store` into every directory a Finder window or an app touches, so a
     merged worktree whose only ignored content is one must still be removed).
     They are build, runtime, and machine output, never data, so they do not keep
     a worktree: remove it and name every ignored path dropped. The ceiling is
     that list — it is exactly what this framework regenerates and what the
     repository ignores as noise, so anything else ignored is treated as data and
     keeps the worktree.
     A match is anchored to the worktree root, never a substring or a bare name:
     the printed path must be the entry itself, or sit inside a listed directory,
     so a listed directory is taken whole (`dist/` covers `dist/out.js`, and
     `node_modules/` covers everything under it). A lookalike is not the entry:
     `packages/x/dist/out.js` is not `dist/`, and `reports-archive/` is not
     `reports/`. The two `*`-prefixed entries are the exception to the whole-path
     rule — they are suffix patterns matched against the path's last component at
     any depth, so `*.DS_Store` matches `sub/.DS_Store` and `*.bun-build` matches
     `app.bun-build`. The read collapses a wholly ignored directory to one
     `!! dir/` line, so the report names the directories it drops; the ceiling is
     that a listed directory goes whole — a hand-written file inside `dist/` is
     dropped with it, unlisted, and only the paths git prints are ever seen.
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
- **Uncommitted content keeps its worktree — except regenerable output and
  ignored noise.** Tracked, untracked, and ignored-but-not-regenerable content
  all keep it; only the named build/runtime paths and the system/editor noise the
  repository already ignores may be dropped, and every dropped path is reported.
- **`ai-eng worktree rm` is the explicit human path.** A person typed it, or the
  close ran it after the merge landed, so it removes what this pass keeps — a
  worktree holding ignored content is deleted by the verb, not by this pass — and
  it prints the ignored paths it drops. The pass is the automatic path and errs
  on keeping; the verb answers a named worktree its caller asked to remove.
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
