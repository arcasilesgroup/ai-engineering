---
name: ai-git-cleanup
description: >-
  Action-first cleanup of finished local git branches and worktrees — one
  question lists every removal, the answer runs it, the report says what
  happened. Auto-invoked by "tidy up", "tidy up these branches", "tidy
  branches", "sync to main", "delete old branches", "start fresh", "limpieza
  de branches", "limpia branches", "sincroniza a main", or by naming
  ai-git-cleanup. Phase 0 migrates to the default branch by itself (auto-stash,
  switch, ff-only pull), the analysis is read-only, every delete is guarded and
  single-quoted, and nothing is ever pushed.
license: LicenseRef-Attributed
---

# ai-git-cleanup — remove finished local branches with proof

Say the cleanup phrase and the run takes over: it gets the repository ready by
itself, shows one list of what it will remove, asks you once, then removes it
and tells you what happened to every branch. Four phases in order — migrate
(automatic and reversible), analyze (read-only), ask (the only confirmation),
execute and report. No deletion starts before that one answer, and none
happens without it.

## What it produces

One JSON document on stdout from [scripts/analyze.mjs](scripts/analyze.mjs)
(never mutates the repository), with sections scoped by the mode flag:

- `fetchStatus` (`ok`, or `failed: <first stderr line, trimmed>` after the
  best-effort `git fetch --prune origin` — a failed fetch must show on screen,
  never silent) and `defaultBranch` (from `origin/HEAD` with a main fallback,
  never from HEAD; an empty default fails every branch closed to `unanalyzed`
  with reason `NO_DEFAULT_BRANCH`).
- `migration` (absent with `--branches`): `previousBranch` (the pre-migration
  branch, for the report) and the steps in execution order — `stash` and `pop`
  only when the working tree is dirty, `switch` when a default exists, `pull`
  only when the default is behind its live upstream — each step carrying its
  exact command and a WARN-and-continue annotation for its failure.
- `batch` (absent with `--sync`): the ONE array the ask renders. Every entry
  carries `branch`, `category`, `action` (`-d` or `-D`), `evidence`, the exact
  single-quoted `command` (the `-d` command bundles the merge-base guard), an
  optional `worktreePath` back-link to the holding worktree, and an
  informational `cluster` when the name groups with a sibling.
- `keep` (branch, reason, evidence, optional cluster — never a command) and
  `unanalyzed` (always present, even empty: a partial analysis must never read
  as a complete one).
- `worktrees` (path, branch, dirty, dirtyFiles, `requiresAcknowledgment` on
  dirty ones, stale, and `command` only when a clean removal is queued) and
  `postCleanup` (`prune` only when a removal is queued).
- `report` (absent with `--sync`): `previousBranch`, `stashState` (this run's
  auto-stash message, or `none`), and one row per branch — `branch`, `action`,
  `reason`, `upstream`, `ahead`, `behind` (counts report-only).

## Flags

The mode flag mirrors the invocation. Arguments: a mode plus an optional repo
path (default: the current directory).

- `--all` — the default: everything, phases 0-3.
- `--sync` — phase 0 only: migrate to the default branch, then stop. No
  analysis, no ask, no deletion.
- `--branches` — phases 1-3: analyze, ask, execute, report — migration stays
  out, HEAD never moves.

```sh
node scripts/analyze.mjs                    # --all: phases 0-3 (the default)
node scripts/analyze.mjs --sync             # phase 0 only: get ready, stop
node scripts/analyze.mjs --branches <repo>  # phases 1-3: no migration
```

The phrase picks the flag: "sync to main" → `--sync`; "tidy up", "delete old
branches" → the default `--all`; stay on the current checkout → `--branches`.

## Safety invariants

- **One ask per delete batch is the hard floor — never zero.** Exactly one
  `ask` precedes any deletion; nothing destructive runs before it. Phase 0's
  stash/switch/pull already ran, because they are reversible — say so at the
  ask.
- **PROTECTED names, the default branch and the checked-out branch are never
  deletable.** One guard sits at the single classification choke point every
  categorization path funnels through (a regex plus explicit names, before any
  triage) — no per-path exceptions. A recommendation that names one of them is
  a bug: stop and report it.
- **Every batch entry carries named evidence** — its category plus the tip sha,
  empty diff or `[gone]` state behind it. A category without evidence is not a
  recommendation; it goes to keep.
- **Every refname and path is single-quoted in every command you emit.** Git
  refname rules allow `$(...)`, backticks, quotes, `;`, `|` and `&`; double
  quotes still execute the first two. An apostrophe escapes by closing and
  reopening: `'has'\''quote'`.
- **The guard runs immediately before every `git branch -d`** — the entry's
  command bundles `git merge-base --is-ancestor 'refs/heads/<branch>'
  '<default>'` ahead of the delete, naming refs and the default branch, never
  a reported sha. Guard failure skips the delete and reports it.
- **The sync target is pinned:** the pull names the default branch as its
  destination and runs with HEAD already switched there — never a
  HEAD-ambiguous pull.
- **A dirty worktree is never removed without the person acknowledging the
  data loss in their own words, per worktree.** Without that acknowledgment it
  is refused and its branch stays keep (`WORKTREE_HELD`); the refusal
  outranks any ordering.
- **`unanalyzed` is always surfaced, and uncertainty fails closed.** A broken
  inventory, a missing default, a failed diff — each lands in keep or
  `unanalyzed` with its reason, visible in the report, never in the batch.
- **Deletions run only in the main session.** Analysis subagents are strictly
  read-only and never ask the person anything.
- **No push, no reflog GC, no `git gc`, no CI, no remote deletion, ever.**
  Ahead/behind counts are report-only.

## Phases

### Phase 0 — get ready (automatic, no ask)

Runs with HEAD on the default branch — the invariant that keeps the pull's
target unambiguous. From `migration`, in execution order:

1. The default is already detected (`defaultBranch`); record `previousBranch`
   — the branch to return to, and the report's "previous branch".
2. Dirty working tree → run `stash` (`git stash push -m
   cleanup-auto-stash-<ts>`). A failed stash push WARNs: secure the
   uncommitted work manually before anything moves the checkout.
3. Run `switch` (`git switch '<default>'`). A failure WARNs and leaves HEAD
   where it is: resolve the checkout before continuing.
4. `pull` appears in the plan only when the default is behind its upstream:
   run `git pull --ff-only '<remote>' '<default>'`, with HEAD already on the
   default so the destination is pinned by name. A failure WARNs: skip the
   pull and continue the cleanup against the local default — cleanup does not
   need a synced default.
5. Stashed? Run `pop` (`git stash pop`). A conflict WARNs: the stash is left
   in place (inspect with `git stash list`), continue the cleanup, and the
   report's `stashState` names it.

None of this asks — it is all reversible. With `--sync`, phase 0 is the whole
run: execute it, show what migrated, stop.

### Phase 1 — analyze (read-only)

Run [scripts/analyze.mjs](scripts/analyze.mjs) with the mode flag that mirrors
the invocation (see Flags). It prints the one JSON document described above and
never mutates the repository.

### Phase 2 — the one ask (the only confirmation)

Present, in execution order:

- `fetchStatus` — `ok` or `failed: <reason>`; a failed fetch is visible, never
  silent.
- The batch table: branch, category, evidence, exact command — with the
  worktree removals that precede deletions at the top (each batch entry's
  `worktreePath` names the worktree that must go first).
- Dirty-worktree warnings: the `requiresAcknowledgment` worktrees and where
  their branches went — NOT in the batch, they sit in keep as
  `WORKTREE_HELD`. Each removal needs its own explicit data-loss
  acknowledgment; until then, refused.
- `postCleanup` — `git worktree prune`, present only when a removal is queued.

The report is deliberately not previewed here — it comes after execution
(phase 3). Then ONE `ask`: delete all, pick, or stop. Nothing destructive has
run before this answer; phase 0 already ran and was reversible (say so). Any
other answer stops the run with the batch untouched.

### Phase 3 — execute in the main session, then report

1. Worktree removals first: every queued `git worktree remove '<path>'`.
2. Then the batch, entry by entry: run the exact command as emitted — for
   `-d` that means the guard, then the delete; a guard failure skips that
   branch and shows up in the report as kept, never as a forced delete. `-D`
   entries run as their own evidence-backed command.
3. `git worktree prune` only when a removal actually happened (`postCleanup`
   is in the document exactly then). Never a push — ahead/behind stay
   report-only.
4. Print the report from `report`: the default branch, the previous
   (pre-migration) branch, `stashState`, then one row per branch — action,
   reason, upstream, ahead/behind as report-only counts. Skipped guards appear
   as kept rows with their reason.

Deletions run only in the main session; a subagent never executes a deletion
and never asks the person anything.

## Out of scope

- Remote branches: no `git push origin --delete`, ever — and no plain
  `git push` either: an ahead default branch is reported, never pushed.
  Local git only.
- No reflog GC, no `git gc`, no CI, no auto-deletion: the one ask is the hard
  floor, never zero.
- Not a branching model: this cleans up branches another process created.

## Lifecycle

Lane: any
Writes: nothing
Read by: the person approving the cleanup
Dies: after each run; the report is a snapshot of that moment
Next: none

Source: adapted from the Trail of Bits git-cleanup plugin
(https://github.com/trailofbits/skills/tree/main/plugins/git-cleanup), CC BY-SA 4.0.
