---
name: ai-pr
description: >-
  The full pull-request loop, run end to end once the human decides to publish
  what the local `main` already holds: cut the pull-request branch from the
  local `main` with no worktree, push it, open the pull request against `main`
  with a body assembled from the merge commits the branch carries, watch CI and
  the review comments, fix only what is obvious in bounded iterations, then
  merge with auto-merge on by default. Running this skill is the human's request
  to finish the pull request — open, watch and merge; a human who says "open the
  pull request only" gets the open pull request and no merge. A session that is
  still building never pushes. Trigger for "get the PR merged", "finish the PR",
  "run the full PR loop", or by naming ai-pr. Not for diagnosing non-CI failures
  — use ai-debug. Not for adding test coverage — use ai-verify.
license: Apache-2.0
---

# ai-pr — carry the local `main` to a reviewed pull request

This is the one place in the framework where a push is legitimate. Until then the
work sits in the local `main` as one merge commit per feature, and `origin/main`
has not moved. When the human says open the pull request, run the phases below in
order and report what each one did. Read `AGENTS.md` and the commit/PR conventions
in `CONTRIBUTING.md` first — they own the branch model and the title/changeset
rules this skill assumes, and nothing here repeats them.

## The ask — who decides what

- **Running this skill is the human's request to finish the pull request** —
  cut, push, open, watch, fix, merge. Print that as the first line of the run, so
  the human sees what was asked before anything moves:
  `ai-pr: finishing <branch> — open, watch, merge.`
- **Open the pull request only.** When the human's words are open the pull
  request only, phases 1-3 run, the run states it stops before merging, and it
  never merges — no merge command, no auto-merge. The ask was to open, not to land.
- **A session that is still building never pushes.** Only this step, the one the
  human triggered, pushes, and only after every session has closed into the local
  `main`.

## Preconditions — refuse before touching anything

- **No session is still building.** A session that has not closed (its branch not
  yet merged into the local `main`, its worktree not yet removed) never pushes.
  If a worktree or an unmerged `feat/*` branch is still open, stop and name it.
- **You are in the primary checkout, on a clean tree.** The pull request is cut
  here, never inside a worktree. A dirty tree is a stop, not a stash: name the
  changed files and refuse.
- **Fetch first, then check the ground.** `origin/main` is a cached ref, so every
  range and count below is a lie without this:

  ```bash
  git fetch origin
  git rev-list --left-right --count origin/main...main
  ```

  Read `<left> <right>` as commits on `origin/main` only, then on the local `main`
  only:
  - left 0, right >0 — normal: the local `main` carries the batch and
    `origin/main` is behind it. That gap is the whole change.
  - left >0, right 0 — nothing to publish: the local `main` is behind
    `origin/main`; stop.
  - both >0 — the branches diverged: stop and report, because a pull request
    opened now would misstate what the branch carries.

## Phase 1 — cut the branch from the local `main`

Name the batch `<branch>`, then handle the three states a run will meet before
cutting:

- **The branch already exists** (a re-run): do not recut. `git switch <branch>`
  reuses it — after the fetch it tracks `origin/<branch>` when the branch was
  pushed, so a second run adds to the same pull request instead of a second one.
- **The primary tree is dirty**: refuse and name the files; never stash or check
  out over someone's edit.
- **The local `main` is behind or diverged**: the Preconditions already stopped;
  re-run them once the human has levelled the branch.

Create the pull-request branch from the local `main`, without a worktree, in the
primary checkout:

```bash
git switch main
git switch -c <branch> main
```

Confirm what the branch carries — the merge commits that `origin/main` does not
have:

```bash
git log --merges --oneline origin/main..HEAD
```

Each line is one feature that landed. If the list is empty, there is nothing to
publish: stop.

## Phase 2 — push it

```bash
git push -u origin <branch>
```

Never force. A rejected push (the remote moved since the fetch) means re-read the
divergence with `git fetch` and `git log --oneline origin/main..HEAD`, then
report — do not overwrite.

## Phase 3 — open the pull request against `main`

Fill the body from the merge commits the branch carries, so a pull request that
bundles several features reads as a list of what landed, never as a diff dump.
Build it once into a file and pass it with `--body-file`:

```bash
gh pr create --base main --head <branch> \
  --title "<area>: <imperative summary>" \
  --body-file <body-file>
```

The title shape and the changeset duty come from `CONTRIBUTING.md`; do not invent
them here. The body has three parts:

1. **What landed** — one bullet per merge commit from Phase 1: the commit subject
   and the feature it names, in order. This is the list a reviewer reads first.
2. **Evidence** — for each checkpoint the batch closed, the command that proved it
   and what it printed (the gate's check, the test run, the typecheck, the lint,
   the build). Quote the command and its result, not a summary. Use the checkpoint
   ledger (`.ai-engineering/workflow/checkpoints/<slug>.json`) as the source, so
   the claim and the command that backs it travel together.
3. **Risk / scope** — anything the human should decide before merging: an open
   question, a deliberately deferred item, a behaviour change a consumer will
   notice.

Never paste secrets, tokens, API keys or logs carrying credentials into the body
or into any later comment. Redact to `<redacted>` and say where the value came
from instead.

## Phase 4 — watch the gate, not the noise

Read the gating set from branch protection, never guess it:

```bash
gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks.contexts'
```

Exactly those contexts gate the merge; `gh pr checks <number> --required` lists
them for this pull request. The rest of the workflows only inform — a red one is
worth reading, never a reason to hold the merge. Treat a gate that is queued or
still running as not passed. Read the review comments as they arrive — a
`CHANGES_REQUESTED` or a blocking comment is a stop, not an iteration.

Poll at most 3 times while a check stays queued or in progress, then declare CI
stuck and stop — never wait forever:

```bash
gh run list --branch <branch> --limit 1 --json databaseId,status,conclusion
gh pr checks <number>
gh pr view <number> --comments
```

## Phase 5 — fix only what is obvious, in bounded iterations

An **obvious** failure is mechanical: lint, formatting, a missing import, an
unused variable, a type mismatch. Everything else — a wrong test expectation, a
broken behaviour, a flaky or infrastructure failure, an ambiguous log — is **not
obvious**: report it with the failing job, the lines that matter and why the fix
is not mechanical, and stop.

Read the failure before typing a fix. For a CI run that is
`gh run view <run-id> --log-failed` — scan for the first actionable error, because
the rest are usually cascades; for a review comment it is the thread. Classify it:
obvious → fix; logic or infrastructure → report and stop. Never guess a root cause
to fill an iteration.

Loop: apply the minimal edit, commit with a `fix: ci` subject, push, and poll
again. The stated cap is **5 iterations** — a hard ceiling. At the cap, stop and
report the last state even if the next fix still looks obvious.

While fixing, do not refactor, do not touch tests to make them pass, and do not
re-run the whole suite locally to replace CI.

## Phase 6 — merge, auto-merge on by default

Once the gating checks are green and no review is blocking, arm auto-merge so the
pull request lands by itself. Skip this phase entirely when the ask was open the
pull request only.

Name the strategy; never let `gh pr merge` prompt for it. The rule: `main`
history decides — no merge commits on `main` means `--squash`. Read the methods
the repository actually allows, and follow that set when it disagrees with the
rule:

```bash
gh api repos/{owner}/{repo} \
  --jq '{squash:.allow_squash_merge,merge:.allow_merge_commit,rebase:.allow_rebase_merge}'
gh pr merge <number> --squash --auto
```

**Switching auto-merge off.** If the human wants to review before it lands, do not
arm it: run `gh pr merge <number> --squash` only on an explicit go. An already-
armed merge is disarmed with `gh pr merge --disable-auto`. Auto-merge is the
default, not a requirement.

Then report the outcome the brainstorm fixes as success: the merged pull request
and its number, or the open pull request and the stated reason it did not merge.

## Phase 7 — level the local `main` with the remote

```bash
git fetch origin
git switch main
git reset --hard origin/main
```

A squash merge lands the batch on `origin/main` as one new commit and leaves the
local `main` carrying the original merge commits, so the two diverge and the next
run's precondition — a local `main` that `origin/main` is behind — is false until
they are levelled. Run this only after the pull request reports merged, and only
when the local `main` is exactly the batch that just landed; otherwise report and
leave the local `main` alone. This is the one place that reset is legitimate.

## Rules that are never bent

- **Never delete a remote branch.** Not on merge, not after it. No branch-deletion
  flag on the merge command, and never the remote-deleting form of push.
- **Never merge outside the ask.** Running this skill is the human's request to
  finish the pull request, merge included; the open-only ask stops before Phase 6,
  and a run that only opened a pull request never merges one.
- **A session that is still building never pushes.** Only the pull-request step
  the human triggered pushes, and only after every session has closed into the
  local `main`.
- **Never force-push and never overwrite a remote that moved.** A rejection is
  reported, not forced.
- **No secret, token or credential-bearing log leaves the machine.** Redact it.

## What this is not

- Not `ai-debug`: this handles failures CI already diagnosed; an undiagnosed
  failure routes to ai-debug first.
- Not `ai-verify`: it does not add or repair test coverage.
- Not a release: it merges; it never publishes, tags or dispatches a release.

## Done when

- The pull request is merged, with its number reported, and the local `main` is
  level with `origin/main` again, or
- A non-obvious failure or a blocking review is reported with evidence and the
  pull request is left open, or
- The 5-iteration cap is exhausted and the last state is reported.

## Lifecycle

Lane: light
Writes: nothing
Read by: the person who asked for the pull request
Dies: on completion
Next: none — the merge lands on `origin/main` and the human takes it from there

Source: ai-engineering (own), Apache-2.0.
