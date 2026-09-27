---
name: ai-git-cleanup
description: >-
  Evidence-gated cleanup of finished local git branches and worktrees. Runs the
  read-only analyzer, presents every delete recommendation with its evidence and
  exact command — plus the post-cleanup sync — in one approval view, and
  executes only what a person approves there — one explicit ask, never zero.
  Manual only: invoke by name when a feature is finished. Never touches remote
  branches, CI or protected branches, and never pushes.
disable-model-invocation: true
license: LicenseRef-Attributed
---

# ai-git-cleanup — remove finished local branches with proof

Runs only when the person invoked it by name. If nobody asked for a cleanup in
this conversation, stop: do not analyze, do not delete.

## What it produces

One view holding the full analysis table with its per-row command plan, the
fetch status and the `postSync` post-cleanup sync, and at most the removals
and sync commands that one approval releases: finished branches and worktrees
gone, the default branch pulled only when it is behind, every refusal visible,
nothing deleted that still holds the only copy of work, nothing pushed.

## Safety invariants

- **One explicit approval is the hard floor.** Exactly one `ask` precedes any
  change — deletion or `postSync` sync alike — never zero, never
  auto-deletion. Stop before it and the repository is untouched.
- **PROTECTED, the default branch and the current branch are never deletable.**
  The analyzer enforces this with a regex and by name. Any recommendation that
  names one of them is a bug: stop and report it.
- **Every delete recommendation carries named evidence** — the tip commit, the
  PR, the superseding branch. A category without evidence is not a
  recommendation; it goes to needs review.
- **Every refname and path is single-quoted in every command you emit.** Git
  refname rules allow `$(...)`, backticks, quotes, `;`, `|` and `&`; double
  quotes still execute the first two. An apostrophe escapes by closing and
  reopening: `'has'\''quote'`.
- **`git merge-base --is-ancestor` runs immediately before every `git branch -d`**
  (the entry's `verifyWith`), naming `refs/heads/<branch>` and the default
  branch — never a reported sha. Guard failure skips the delete and reports it.
- **A dirty worktree is refused**, never queued. It is removed only after the
  person explicitly acknowledges, in their own words, that the uncommitted
  changes are lost.
- **`unanalyzed` is always surfaced**, even when empty. A partial analysis must
  never read as a complete one.
- **Fail closed.** A refuted candidate, an unreachable refuter, a failed proof —
  all downgrade to needs review, never to deletable.
- **Deletions run only in the main session.** Analysis subagents are strictly
  read-only and never ask the person anything.

## Steps

1. **Analyze, read-only.** Run [scripts/analyze.mjs](scripts/analyze.mjs) with
   an optional repo path (`node scripts/analyze.mjs [repo-path]`, defaulting to
   the current directory). It prints one JSON document: `fetchStatus` (`ok`, or
   `failed: <first stderr line, trimmed>` after the best-effort
   `git fetch --prune origin`), `deleteCandidates`
   (reason, evidence, command, `verifyWith` for `SAFE_TO_DELETE`, and
   `worktreePath` when a linked worktree holds the branch), `needsReview`,
   `keep` (including `PROTECTED`), `worktrees` (path, branch, dirty, dirtyFiles,
   stale, and `command` when stale), `unanalyzed`, `defaultBranch`,
   `currentBranch`, and `postSync` — the post-cleanup sync, where each field
   appears only in its qualifying configuration: `prune` (`git worktree prune`)
   only when a worktree removal is queued, `upstream`, `ahead` and `behind`
   counts when the default branch tracks one, and `pull` (`git pull --ff-only`)
   only when `behind` is greater than zero — `ahead` is report-only, never a
   push; branch names that form a related group in any bucket also
   carry an informational `cluster`. An empty `defaultBranch` means no anchor
   was found: every branch fails closed to `unanalyzed` with reason
   `NO_DEFAULT_BRANCH`, never to a delete. It never mutates the repository.

2. **Investigate what git cannot prove, read-only.** Branches in `needsReview`
   or `unanalyzed`, and any squash-merged or superseded claim, go to read-only
   investigator subagents — at most five, spawned by the main session, **never
   nested**, and batched (one related group, one agent). They read
   [references/merge-evidence.md](references/merge-evidence.md) first and come
   back with a named PR or commit, or with nothing. Nothing? Needs review.

3. **Refute every non-`SAFE_TO_DELETE` delete claim.** Each claim (squash-merged,
   superseded) goes to one skeptic whose job is to find a commit the claim
   cannot account for — at most five, spawned by the main session, never
   nested, read-only. Refuted, unverified, missing a verdict, or lost to a
   failed agent: needs review. `SAFE_TO_DELETE` skips this only because step 5
   re-proves it with `merge-base` immediately before the delete.

4. **The gate — one view, then one `ask`.** Present everything in a single
   view, in execution order:

   - `fetchStatus` from the analysis run: `ok`, or `failed: <reason>`. A failed
     fetch means remote-derived states may be stale — classification already
     errs toward keep and needs review, but the failure must be visible on
     screen, never silent.
   - Every bucket as a table with evidence columns: delete candidates (reason,
     evidence, `verifyWith`), needs review, keep, worktrees (dirty, stale, dirty
     files), and `unanalyzed` — always, even when it is empty.
   - The exact command plan, row for row: worktree removals first
     (`git worktree remove '<path>'`), then each guard paired with its delete
     (`git merge-base --is-ancestor 'refs/heads/<branch>' '<default>' && git
     branch -d '<branch>'`). `SAFE_TO_DELETE` is pinned to `-d`; `-D` appears
     only for a claim that named its PR or commit and survived step 3, with
     that evidence on screen.
   - Then the post-cleanup sync from `postSync`, in execution order after the
     approved deletions: `git worktree prune` only when a removal is queued,
     then `git pull --ff-only '<remote>' '<branch>'` on the default branch
     only when `postSync.behind` is greater than zero (the upstream it syncs
     from is named in `postSync.upstream`), then the `postSync.ahead` count as
     a report — ahead is never a push.

   Then one `ask`: delete all recommended, pick, or stop. The one approval
   covers the whole plan above — deletions and sync alike. Nothing runs before
   that approval; any other answer stops the run with the repository untouched.

5. **Execute in the main session.** Run the plan yourself, in order: worktrees
   before branches, guard before every `-d`, skip and report any guard that
   fails; once the deletions are done, `git worktree prune` if a removal was
   queued, then the ff-only pull if the plan has one; report `ahead` without
   ever pushing. A subagent never executes a deletion and never asks the
   person anything.

## Out of scope

- Remote branches: no `git push origin --delete`, ever — and no plain
  `git push` either: an ahead default branch is reported in the plan, never
  pushed. Local git only.
- No reflog GC, no `git gc`, no CI, no auto-deletion: the one explicit approval
  is the hard floor, never zero.
- Not a branching model: this cleans up branches another process created.

## Lifecycle

Lane: any
Writes: nothing
Read by: the person approving the cleanup
Dies: after each run; the report is a snapshot of that moment
Next: none

Source: adapted from the Trail of Bits git-cleanup plugin
(https://github.com/trailofbits/skills/tree/main/plugins/git-cleanup), CC BY-SA 4.0.
