---
name: ai-pr
description: >-
  The full pull-request loop, run end to end once the human decides to publish
  what the local `main` already holds: cut the pull-request branch from the
  local `main` with no worktree, push it, open the pull request against `main`
  with a body assembled from the merge commits the branch carries, watch CI and
  the review comments, fix only what is obvious in bounded iterations, then
  merge with auto-merge on by default. Trigger for "open a PR", "make the pull
  request", "push this", "get the PR merged", or by naming ai-pr. Never opens or
  merges a pull request unless the human asked for it, and a session that is
  still building never pushes. Not for diagnosing non-CI failures — use
  ai-debug. Not for adding test coverage — use ai-verify.
license: Apache-2.0
---

# ai-pr — carry the local `main` to a reviewed pull request

This is the one place in the framework where a push is legitimate, and it runs
only because a person asked for it. Until then the work sits in the local `main`
as one merge commit per feature, and `origin/main` has not moved. When the human
says open the pull request, run the phases below in order and report what each
one did. Read `AGENTS.md` and the commit/PR conventions in `CONTRIBUTING.md`
first — they own the branch model and the title/changeset rules this skill
assumes, and nothing here repeats them.

## Preconditions — refuse before touching anything

- **The human asked.** No explicit request, no pull request: stop and say so. A
  merge on the agent's own initiative is the one thing this skill exists to
  prevent.
- **No session is still building.** A session that has not closed (its branch not
  yet merged into the local `main`, its worktree not yet removed) never pushes.
  If a worktree or an unmerged `feat/*` branch is still open, stop and name it.
- **You are in the primary checkout, on a clean tree.** The pull request is cut
  here, never inside a worktree.
- The merges are already in the local `main`: the branch you are about to cut
  carries them, and `origin/main` is behind it. That gap is the whole change.

## Phase 1 — cut the branch from the local `main`

Create the pull-request branch from the local `main`, without a worktree, in the
primary checkout:

```bash
git switch main
git switch -c <branch> main
```

`<branch>` is the human's name for the batch. Confirm what the branch carries —
the merge commits that `origin/main` does not have:

```bash
git log --merges --oneline origin/main..HEAD
```

Each line is one feature that landed. If the list is empty, there is nothing to
publish: stop.

## Phase 2 — push it

```bash
git push -u origin <branch>
```

Never force. A rejected push (the remote moved) means re-read the divergence with
`git log --oneline origin/main..HEAD` and `git fetch`, then report — do not
overwrite.

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

## Phase 4 — watch CI and the reviews

Poll the checks the pull request is subject to, and the conversation on it:

```bash
gh pr checks <number>
gh run list --branch <branch>
gh pr view <number> --comments
```

Distinguish the workflows that gate the merge from the ones that only inform:
wait for a gate to reach a conclusion before acting on it, and treat a still-running
or not-yet-reported gate as not passed. Read the review comments as they arrive —
a `CHANGES_REQUESTED` or a blocking comment is a stop, not an iteration.

## Phase 5 — fix only what is obvious, in bounded iterations

An **obvious** failure is mechanical: lint, formatting, a missing import, an
unused variable, a type mismatch. Everything else — a wrong test expectation, a
broken behaviour, a flaky or infrastructure failure, an ambiguous log — is **not
obvious**: report it with the failing job, the lines that matter and why the fix
is not mechanical, and stop. Never guess a root cause to fill an iteration.

Loop: read the failure (for a CI run, the failed logs; for a review comment, the
thread), apply the minimal edit, commit with a `fix: ci` subject, push, and poll
again. The stated cap is **5 iterations** — a hard ceiling. At the cap, stop and
report the last state even if the next fix still looks obvious.

While fixing, do not refactor, do not touch tests to make them pass, and do not
re-run the whole suite locally to replace CI.

## Phase 6 — merge, auto-merge on by default

Once the gating checks are green and no review is blocking, arm auto-merge so the
pull request lands by itself:

```bash
gh pr merge <number> --auto
```

Pick the merge strategy the repository allows; `gh` reports a rejection from
branch protection rather than doing the wrong thing, so read its answer.

**Switching auto-merge off.** If the human wants to review before it lands, do not
arm it: merge only on an explicit go, with the same command without `--auto`. An
already-armed merge is disarmed with `gh pr merge --disable-auto`. Auto-merge is
the default, not a requirement.

Then report the outcome the brainstorm fixes as success: the merged pull request
and its number, or the open pull request and the stated reason it did not merge.

## Rules that are never bent

- **Never delete a remote branch.** Not on merge, not after it. Do not pass the
  branch-deletion flag to `gh pr merge`, and never run the remote-deleting form of
  push.
- **Never open or merge a pull request unless the human asked for it.** A green
  pull request is not a request to merge one.
- **A session that is still building never pushes.** Only the pull-request step the
  human triggered pushes, and only after every session has closed into the local
  `main`.
- **Never force-push and never overwrite a remote that moved.** A rejection is
  reported, not forced.
- **No secret, token or credential-bearing log leaves the machine.** Redact it.

## What this is not

- Not `ai-debug`: this handles failures CI already diagnosed; an undiagnosed
  failure routes to ai-debug first.
- Not `ai-verify`: it does not add or repair test coverage.
- Not a release: it merges; it never publishes, tags or dispatches a release.

## Done when

- The pull request is merged, with its number reported, or
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
