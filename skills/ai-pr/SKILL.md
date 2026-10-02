---
name: ai-pr
description: >-
  The pull-request loop, opened from the local `main` with no worktree: cut the
  pull-request branch from the local `main`, push it, open the pull request
  against `main` with a body assembled from the merge commits the branch
  carries, watch CI and the review comments, fix only what is obvious in
  bounded iterations, then merge with auto-merge on by default. The human's verb
  decides how far the run goes: "open the pull request" opens it and stops,
  while "finish the PR", "land the PR", "merge it" or "run the full PR loop"
  carries the run through the merge — an ask that names neither is the open one.
  A session that is still building never pushes. Not for diagnosing non-CI
  failures — use ai-debug. Not for adding test coverage — use ai-verify.
license: Apache-2.0
---

# ai-pr — carry the local `main` to a reviewed pull request

This is the one place in the framework where a push is legitimate. Until then the
work sits in the local `main` as one merge commit per feature, and `origin/main`
has not moved. Run the phases below in order and report what each one did; the
verb the human used decides how far the run goes — open stops after Phase 3,
finish/land/merge it continues through Phase 6 (see The ask). Read `AGENTS.md`
and the commit/PR conventions
in `CONTRIBUTING.md` first — they own the branch model and the title/changeset
rules this skill assumes, and nothing here repeats them.

## The ask — the verb the human uses decides the run

- **The verb decides how far the run goes, and nothing else does.** Read the
  words before any command runs, and print the shape as the first line of the
  run:
  - **"open", "open the pull request", "make the PR"** — Phases 1-3 run and the
    run stops there: `ai-pr: opened <branch> — not merging.` Open the pull
    request only is the open mode, and it never merges — no merge command, no
    auto-merge, and no Phase 6.
  - **"finish", "land", "merge it", "get the PR merged", "run the full PR
    loop"** — the run carries the whole loop: cut, push, open, watch, fix, and
    through the merge. Print `ai-pr: finishing <branch> — open, watch, merge.`
- **An ambiguous ask is the open one.** When the words name neither shape, the
  run opens the pull request only and stops; the merge is the shape the human
  must name, never the one inferred.
- **A green pull request is not a request to merge it.** The merge happens
  because the human said finish, land or merge it — asking for this skill with a
  finish verb is the request to land the pull request — never because the checks
  came back green. Both the open ask and the ambiguous ask stop before Phase 6.
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

A re-run continues the same pull request. Before creating one, ask whether the
branch already has an open pull request and reuse it — the number every later
phase needs comes from that read, and the create below runs only when this finds
nothing:

```bash
gh pr view <branch> --json number,state
```

Only the message that no pull request was found for the branch means there is
none, and only then does the create run. A non-zero exit for any other reason — an
expired token, no network, an API error — is neither that case nor a pull request
state: report gh's message and stop, the same rule the merge follows, and never
read a failed read as "no pull request" and create a second one. An `<number>`
with state `OPEN` means skip the create and carry on with that pull request. Any
other state is reported and the run stops — that pull request is already closed
or merged.

The create path has no number yet: `gh pr create` prints the new pull request's
URL, so read `<number>` back from the branch with the same `gh pr view <branch>
--json number,state` once it succeeds — a successful create is the one case where
that read must find something, and the number it prints, not the URL text, is what
Phases 4-6 use.

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
them for this pull request. When the query itself fails — an unprotected branch,
a fork, or a token without admin rights — nothing gating that the run can verify
exists, so the run must not arm auto-merge: it waits for the human's explicit
word before Phase 6 and says the gating set could not be read. The rest of the
workflows only inform — a red one is worth reading, never a reason to hold the
merge. Treat a gate that is queued or still running as not passed. Read the
review comments as they arrive — a `CHANGES_REQUESTED` or a blocking comment is a
stop, not an iteration.

Poll the check every 30 seconds while it stays queued or in progress, up to a
total budget of 30 minutes. At the cap, declare the check stuck and stop — never
wait forever. A stuck check is an end state the run reports: name the check still
queued or in progress, its last run state, and how long it was watched. The run
continues only from a poll that succeeded and shows the check no longer queued or
in progress:

```bash
gh run list --branch <branch> --limit 1 --json databaseId,status,conclusion
gh pr checks <number>
gh pr view <number> --comments
```

A poll can fail as well: when any of those commands exits non-zero — an expired
token, no network, an API error — that is not a finished check. Report gh's
message and the check it was reading, and stop; never read a failed poll as a
passing check, and never as a stuck one.

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

Once the ask was finish or land and the gating checks are green with no review
blocking, arm auto-merge so the pull request lands by itself. Skip this phase
entirely when the ask was open (or ambiguous), and never arm auto-merge when
Phase 4 could not read the gating set — there the merge waits for the human's
explicit word.

The merge method is a **merge commit**, `gh pr merge --merge` — never squash. The
local `main` is the integration trunk, and the merge commit is the only method
that leaves the local trunk in `origin/main`'s ancestry: a squash puts an
unrelated commit on `origin/main` and strands the local trunk, so Phase 7's
fast-forward could never run. If the repository does not allow merge commits,
stop and report it — no other method leaves the local trunk healthy, and the
skill does not pick a second strategy on its own. Never let `gh pr merge` prompt:

```bash
gh api repos/{owner}/{repo} \
  --jq '{squash:.allow_squash_merge,merge:.allow_merge_commit,rebase:.allow_rebase_merge}'
gh pr merge <number> --merge --auto
```

A rejected merge is reported, not retried. When `gh pr merge` fails with a
non-zero exit code — a conflict, a method the repository denies at merge time, or
a protection rule the API query above did not surface — report gh's message,
leave the pull request open and stop; never retry the merge blindly, and never
force it through.

**Switching auto-merge off.** If the human wants to review before it lands, do not
arm it: run `gh pr merge <number> --merge` only on an explicit go. An already-
armed merge is disarmed with `gh pr merge --disable-auto`. Auto-merge is the
default, not a requirement.

Then report the outcome the brainstorm fixes as success: the merged pull request
and its number, or the open pull request and the stated reason it did not merge.

## Phase 7 — level the local `main` with the remote

Run this only after the pull request reports merged. First fetch and verify the
merge landed as an ancestor, so the local `main` can be fast-forwarded rather
than overwritten:

```bash
git fetch origin
git merge-base --is-ancestor main origin/main
```

When that exits non-zero, the local `main` is not in `origin/main`'s ancestry —
the pull request did not land as a merge commit, or a session merged after it —
so stop and report; never force the local `main` level. When it exits zero, level
with a fast-forward-only update, never a hard reset:

```bash
git switch main
git merge --ff-only origin/main
```

The fast-forward moves the local `main` forward to `origin/main` and nothing
else, so a feature another session merged after the pull request was cut is kept,
never discarded, and the batch history survives — the merge commit put the local
trunk in `origin/main`'s ancestry. This is the one place the local `main` is
levelled.

## Rules that are never bent

- **Never delete a remote branch.** Not on merge, not after it. No branch-deletion
  flag on the merge command, and never the remote-deleting form of push.
- **Never merge outside the ask.** Only the words finish, land or merge it carry
  the run through the merge; the open ask and the ambiguous ask stop before
  Phase 6, and a run that only opened a pull request never merges one.
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
  levelled with `origin/main` — or the fast-forward was refused and that is
  reported for the human to level, or
- A non-obvious failure or a blocking review is reported with evidence and the
  pull request is left open, or
- CI is declared stuck when the 30-minute poll budget runs out, with the check
  still queued or in progress named and its last run state reported, or
- The 5-iteration cap is exhausted and the last state is reported.

## Lifecycle

Lane: light
Writes: nothing
Read by: the person who asked for the pull request
Dies: on completion
Next: none — the merge lands on `origin/main` and the human takes it from there

Source: ai-engineering (own), Apache-2.0.
