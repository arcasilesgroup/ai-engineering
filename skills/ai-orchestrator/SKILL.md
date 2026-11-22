---
name: ai-orchestrator
description: Build a whole feature end-to-end through subagents. It plans gated checkpoints, then one resumed builder writes the tests, implements, and runs verify. One fresh reviewer checks the diff. A UI gate runs only when the checkpoint has one. The human reviews the app at the end. Use when the user says "build X", "orchestrate X", "/ai-orchestrator <feature>", or asks to resume an orchestrated feature.
license: MIT
---

# Orchestrator

You coordinate. The builder is one resumed subagent. The reviewer is a different agent. Your context stays the checkpoint file and their short returns.

**Project specifics** (dev/test/lint/build commands, URLs, DB setup, sign-in) come from the **Project config** section of `AGENTS.md`. Pass the relevant values into every worker prompt so workers don't have to hunt for them.

## Approval stops

On a fresh run, the human approves the brainstorm before Phase 0 and reviews the app
in Phase 4. A new plan backed by that approved brainstorm opens in the viewer and
continues to Phase 2 without another plan-approval question. Only a resumed legacy
plan with `phase: awaiting-plan-approval` and `plan_approval: pending` keeps the
Phase 1 checkpoint-review stop.

Everywhere else, decide and keep going:
- **Ambiguity:** choose the option most consistent with `.ai-engineering/PRD.html`, `.ai-engineering/brainstorm.html`, `DECISIONS.md` and the existing code, and log it as an `assumptions` entry in the checkpoint JSON. The human sees those at the next review. The brainstorm gate, below, refuses a missing, stale, or unrelated interview before any of this runs.
- **Failures:** the builder gets one fix. If verify still fails, stop and tell the human (see Phase 2).
- Never pause for permission to run tests, start servers, or fix code.
- A passed checkpoint ends the turn. A failed fix is the only failure stop.

## Context rules (non-negotiable)

- **You do not read source, diffs, test logs, or screenshots.** The builder returns the receipt: PASS or FAIL, the files it changed, and one line per verify command. A hook denial is the instruction. Do not open `src/guards/checkpoint.ts` or the lease implementation.
- **Checkpoint progress lives on disk** in `.ai-engineering/workflow/checkpoints/<slug>.json`; that file is the source of truth for checkpoint status. Phase 0's read-only `ai-eng worktree list` reports registered worktrees and their lifecycle status; the current checkout may also be the selected feature checkout. Change the checkpoint file only with Edit or Write, never through Bash. The same hook validates every write to it: no gate can be passed out of order, no checkpoint can be marked passed with a gate still open, and no checkpoint can be touched while an earlier one is open. Update it after every step, so `/ai-orchestrator resume <slug>` can pick up after a crash or `/clear`.
- **Every subagent prompt:**
  - in Phase 2 and later, **starts with the gate marker** `[checkpoint <slug>#<id> <stage>]`, where `<slug>` is the feature slug you were asked to build and `<stage>` is one of `tests`, `implement`, `behavior`, `ui`, `review` or `fix`. The TypeScript checkpoint guard (`src/guards/checkpoint.ts`, in the chain) reads it and blocks the call if:
    - an earlier checkpoint hasn't passed;
    - this checkpoint has already passed;
    - or the gate before this one hasn't passed.

    **If the hook blocks you, never work around it.** The denial text names the fix: finish the earlier gate, or reopen the checkpoint. Do not open the guard source to interpret it;
  - carries this checkpoint only: its `goal`, `tasks`, `files`, `acceptance`, and `verify`. Do not paste the rest of the plan;
  - pastes the Rules whose ids this checkpoint names. The worker does not open `docs/history/learnings-log.md`;
  - tells the worker to call `codegraph_explore` once for the symbols in the slice before grepping the tree;
  - ends with: *"Return at most 15 lines: result, files changed, failures. No code, no logs."*
- **Subagents can't spawn subagents.** When a prompt points a worker at a skill that says "launch a subagent", add: *"You are already a subagent. Do those steps yourself."* Anything that needs parallel subagents (prototypes, test writers, UI reviewers), you launch directly, several `Agent` calls in one message.
- **One builder, one reviewer.** Resume the builder with SendMessage for tests, implementation, verify, the next checkpoint, and the one fix. The reviewer is a new agent. The builder never reviews its own diff. A builder that does not return gets one fresh replacement with the same slice; do not wait on it.

## Direct rhythm

Use the Direct rhythm for a bug, spike, or one-session change that does not alter an interface other work depends on. It stays in the current checkout and uses the smallest relevant checks. It has no brainstorm or worktree step; this orchestrator is for the multi-session feature ceremony.

## Commits: one per checkpoint

A passed checkpoint ends with one commit on the selected feature branch, which need not follow a `feat/<slug>` naming convention. The checkpoint file is what resume reads; the commit is the record of that slice. You make the commits yourself with Bash; the output is small.

- **Tree and branch:** Work in the current checkout by default. Use a worktree when requested or another feature is active here. Prefer the host's native worktree (`claude -w <branch>` or Cursor `/worktree`); if unavailable, `ai-eng worktree new <branch>` starts it from the current `HEAD`. On resume, use its exact Git-listed path and continue the feature's own changes without stashing or resetting them; leave foreign files untouched. Never derive a path or switch branches. Everything is committed on the selected feature branch, and `ai-eng worktree merge <slug>` makes one `--no-ff` merge against the detected base after app review.
- **Stage explicit paths only.** Never use `git add -A` or `git add .`. The selected checkout may contain other work, so a loose stage could sweep unrelated edits; an explicit list keeps each commit the slice it claims. Stage the step's `changed_files`, its test files, `.ai-engineering/workflow/checkpoints/<slug>.json`, `.ai-engineering/workflow/test-plans/<slug>.json`, `.ai-engineering/workflow/prototypes/<slug>*`, `.ai-engineering/workflow/reviews/<slug>-*.md`, and whichever of `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md` and `CHANGELOG.md` the step touched. Never stage a design slot (`.ai-engineering/brainstorm.html`, `.ai-engineering/spec.html`, `.ai-engineering/plan.html`) unless the step explicitly owns it. Do not stage `.ai-engineering/workflow/playwright/`, `.env*` or files that were in the Phase 0 baseline.
- **When to commit, and with which message.** The `commit-msg` hook (`src/floor/index.ts`) accepts any of the eleven Conventional Commit types — `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert` — with an optional scope matching `[a-z0-9._/-]+` (no `#`); it checks nothing about the body. This repo's house convention still puts the checkpoint number in the body rather than the scope — the hook does not enforce that — so `plan`, `gate` and `wip` are gone and the number moved off the scope. Each message ends with the co-author trailer.

| After | Message |
|---|---|
| Plan approved (Phase 1) | `chore(<slug>): plan checkpoints, test plan, prototypes` |
| Checkpoint passed | `feat(<slug>): checkpoint N <title>`, with the JSON |
| Stopped after one failed fix | `chore(<slug>): stopped at <gate>, needs human`, committed before you stop |
| Wrap-up | `docs(<slug>): changelog, filemap, learnings` |

- **Nothing to commit?** Skip the commit. Never make an empty commit, and never pass `--no-verify`. A verify receipt that changed no file still updates the JSON, and that JSON rides in the checkpoint commit.

## The brainstorm gate

Before Phase 0, read `.ai-engineering/brainstorm.html`. Plan nothing until every line below is true:

- the file exists;
- `<meta name="ai-feature">` is the slug of the feature you were just asked to build;
- `<meta name="ai-approved">` is a `YYYY-MM-DD` date, and that date is within 14 days;
- there is exactly one of each marker, and the status line is exactly
  `complete ·` that same date.

Anything else is unknown, not approval: a missing, draft, malformed, ambiguous,
mismatched or expired artifact. Run `/ai-brainstorm` for this feature and stop. Do not
turn the old page into checkpoints. When the slug matches but the date is older than
14 days, say the date out loud and re-run the interview.

When the gate passes, every later phase reads both files. `.ai-engineering/PRD.html` is the conclusions. `brainstorm.html` is the interview: what was wanted, what was decided, and what was refused.

## Phase 0: Preflight

- Work in the current checkout by default; a managed worktree is optional, not a
  prerequisite. Use the local read-only `ai-eng worktree list` to find registered
  worktrees and active checkpoints, and `ai-eng worktree list <slug>` when checking a
  specific existing feature. The list reports only Git-registered worktrees and their
  lifecycle checkpoints; it does not infer a feature from a brainstorm or an
  unregistered folder. A brainstorm approval is not worktree or lifecycle state, and
  there is no pre-worktree approval projection. Once a checkpoint exists, it alone is
  authoritative; missing, malformed or contradictory checkpoint state is unknown and
  cannot authorize work.
  Before deciding
  whether work may continue, explicitly surface a pending plan approval as
  `awaiting-plan-approval` with `plan_approval: pending`, a pending app review as
  `awaiting-app-review` with `app_review: pending`, and `ready-to-merge` with
  `app_review: approved`. Do not reduce these to a generic pending-approval label.
  For pending plan approval, pause and ask the human to **Approve**, **Edit**, or
  **Stop** before implementation continues. For pending app review, pause and ask the
  human to **Approve**, **Request changes**, or **Stop here** before merging. For
  `ready-to-merge`, report that state and ask whether to continue the merge before any
  merge action. Unknown lifecycle state is not approval. Never fetch or sync remote
  state, and never merge an unapproved sibling.
- Resume an exact same-slug feature from its current checkout or its exact Git-listed
  worktree path. Feature-owned dirty files are continuable; do not stash or reset them.
  Leave foreign files untouched. If the checkpoint or ownership is unknown, or more
  than one checkout could be the source, preserve all work and ask instead of guessing.
- Semantic near-matches are advisory only, never a substitute for the exact slug.
- Clearly unrelated work may continue untouched. If another active feature could
  overlap, pause and ask the human to choose whether to isolate it; do not guess from a
  near-match or from dirty files alone. When isolation is useful or requested,
  including when another active feature is here, prefer the host's native worktree
  (`claude -w <branch>` or Cursor
  `/worktree`); if unavailable, run `ai-eng worktree new <branch>` and use the exact
  Git-listed path. The branch may have any valid Git name. Dirty design files stay in
  the current checkout and the managed-worktree command warns that they do not travel.
  If creation refuses, report the reason and stop; do not modify files or branches to
  force it. No file hints are accepted;
  the checkpoint's `files` list remains authoritative.
- Record the selected checkout's status and existing paths as a baseline; never clean up unrelated work. When the project has no database, no API health URL, and no signed-in pages, run `bun --version` in the selected checkout yourself and treat a successful run as ready. Do not spawn a subagent for that check. Take the folder lease once here with `ai-eng work`. Workers do not run `ai-eng work release` and do not read the lease implementation. Delegate environment
  readiness to one `general-purpose` subagent only when the project has a database, an API, or signed-in pages. That subagent reports ready or blocked, and
  runs from the selected checkout without modifying any other checkout:
  - the local DB is up, if the project has one (Project config → *DB status*; if it's
    down, run *DB start/reset* to apply migrations and the seed);
  - the API health check and the web URL both answer (if not, run the *Dev server*
    command from the selected worktree root in the background);
  - `.ai-engineering/workflow/playwright/auth.json` exists, if the app has signed-in
    pages. If it's missing, create it only in the selected worktree when Project
    config → *Automated sign-in* describes a way (e.g. a demo-login button or seeded
    test credentials): script a Playwright sign-in and save
    `context.storageState({ path: '.ai-engineering/workflow/playwright/auth.json' })`,
    using `npx -y -p playwright node <script>` with the script in the scratchpad. Save
    one file per role listed under *Roles*
    (`.ai-engineering/workflow/playwright/auth-<role>.json`), with `auth.json` as a
    copy of the most privileged one.

Only if automatic sign-in is impossible (Project config gives no way), add the manual step to the Phase 1 checkpoint review, so the user handles it in the same stop:
```
! npx -y playwright codegen --save-storage=.ai-engineering/workflow/playwright/auth.json <web URL><sign-in path>
```

## Phase 1: Plan

Run Phase 1 and its workers from the selected checkout, normally the current checkout.
Create the checkpoint plan, test plan and prototypes only there; do not copy plans
between checkouts.

1. **Checkpoints:** run the `checkpoint-planner` agent with the feature request. Its first write of `.ai-engineering/workflow/checkpoints/<slug>.json` in the selected checkout must include `gates` and `ui` for each checkpoint and this lifecycle: `phase: implementation`, `plan_approval: approved`, `app_review: not-started`, `base_ref: null`, `reviewed_base: null`, and `reviewed_feature: null`. The checkpoint gate rejects a new plan with missing or contradictory state or one written outside the selected checkout at its matching slug path. If it comes back with questions, don't ask the user. Answer them yourself from the PRD, the decisions and the code, re-run it with those answers, and log them as `assumptions`.
   - Resumed legacy plans keep their existing lifecycle: `awaiting-plan-approval` requires `plan_approval: pending`, `app_review: not-started`, and cleared review SHAs.
2. **Test plan:** run a `general-purpose` subagent to do steps 1–2 of `ai-test-planner`. That's the plan only, no tests yet: it writes `.ai-engineering/workflow/test-plans/<slug>.json`, with every case linked to a `checkpoint` and each checkpoint's test commands added to its `verify` array.
3. **Prototypes:** list the distinct `ui.prototype` paths across the checkpoints. Launch one `general-purpose` subagent per prototype **in parallel**. Each one follows `ai-prototype` for its screen, covering the states named in `ui.states`, and skips the `open` step.

4. **Open the plan:** start the viewer if it isn't already running with `python3 -m http.server 8765` from the selected checkout root in the background (not `docs/`, so prototype links resolve), then open `http://localhost:8765/.ai-engineering/workflow/checkpoints/viewer.html?plan=<slug>`. It updates live as the JSON changes and remains the progress view for the run. The checkpoint hook checks the local brainstorm artifact's matching feature slug, approval date within 14 days, and matching `complete ·` status line on this first approved lifecycle write. This is local guardrail validation of the HTML approval stamp, not independent proof of who approved it. Then proceed directly to Phase 2 without another approval question.

For a resumed legacy plan that is still pending at its checkpoint review, preserve its prior human _stop_ 1: checkpoint review. Show the viewer details and use `ask_user_question` to offer: **Approve**, **Edit**, or **Stop**. Do not begin Phase 2 or dispatch its workers until the human approves the checkpoint plan. After approval, set the lifecycle phase to `implementation`, persist `plan_approval: approved`, `app_review: not-started`, and cleared review SHAs, and confirm the guarded write succeeded. On **Edit**, keep plan approval pending, update the plan and ask again. This legacy path does not apply to a new plan started from an approved brainstorm.

## Phase 2: Checkpoint loop

For each checkpoint in `id` order, and only once the previous one has `status: "passed"`. Checkpoints stay serial. Do not start the next one in this turn.

### a. Build
Use one `general-purpose` subagent, the builder. The first prompt starts with `[checkpoint <slug>#<id> implement]`. Resume this same builder for later checkpoints and for the one fix. Add: *"You are already a subagent. Do not spawn subagents."*

Give it this checkpoint's `goal`, `tasks`, `files`, `acceptance`, and `verify`, the pasted rules, and the project commands. For a UI checkpoint, also give `ui.prototype` and its `.ai-engineering/workflow/prototypes/<name>.states.json`. The live page must use **the same field labels and button text**, and support the same states, because the UI gate drives both sides with identical steps. It follows `AGENTS.md`, reuses existing helpers, and updates `FILEMAP.md` (and `PERMISSIONS.md` if access changes).

It writes the failing tests for this checkpoint (step 3 of `ai-test-planner`; step 4 of `ai-test-planner` when `ui` is set), runs them, implements, and runs `verify` in order: unit, API, CLI, then UI e2e only if the layers above passed. A test that passes before implementation is suspicious; it reports that. It does not edit tests after they exist unless a finding says the test is wrong.

It returns at most 15 lines: PASS or FAIL, `changed_files`, and one line per verify command. Record `changed_files`. When the receipt says PASS, set `gates.behavior` to `"passed"`. Do not spawn a behavior agent. When it says FAIL, apply **On failure** once.

### b. Gate 2: UI (skip if `gates.ui.status` is `"n/a"`)
Do not start a server for a checkpoint whose UI gate is `"n/a"`. Otherwise run `ai-review-ui` steps 2–4 yourself in **gate mode**, using `ui.route`, `ui.prototype` and `--scope <ui.scope joined by commas>`. Step 2 re-checks that the app is up and the sign-in session is still valid, and gate mode checks the scenario's `route` matches `ui.route`, so a dead server or a stale route never shows up as false mismatches. That way only the regions this checkpoint has built are captured and judged. The capture script puts both sides in the same state for each scenario, and prints only one line per state, so run it yourself. Then launch the two reviewers in parallel. **The gate passes** when every live-reproducible state is `match` (a `MISMATCH` means the page behaves differently from the prototype) and there are no `high` or `med` findings, except ones tagged `[intentional?]`. Log those as notes; they don't fail the gate.

### c. Review
Follow `ai-adversarial-loop` in its orchestrator mode: one critic round, and one fix only when the critic returns a BLOCKER or a MAJOR. The critic prompt starts with `[checkpoint <slug>#<id> review]`. Give it the acceptance list, the pasted rules, `changed_files`, and the builder's verify receipt. It judges the diff. It does not re-run verify when the receipt is present.

- **`VERDICT: PASS`:** set `gates.review` to `"passed"`. Record MINOR findings in `notes`.
- **BLOCKER or MAJOR:** resume the builder once with `[checkpoint <slug>#<id> fix]` and those findings. It fixes the root cause, does not edit the tests unless a finding says the test is wrong, re-runs the verify commands it touched, and returns `ROOT CAUSE:`, `FIX:`, `LESSON:`. Append that lesson to `LEARNINGS.md` using the template in that file. Resume the same critic once. PASS sets the gate passed. A second FAIL is **On failure**. Do not open a third round and do not split the checkpoint.

The thread file is `.ai-engineering/workflow/reviews/<slug>-<id>.md`. The critic writes findings there. You do not read the thread. You act on the verdict line. If the fix changed code, the builder's new receipt is the behavior gate. Re-run the UI gate only when this checkpoint has one.

### On failure
Set the gate to `"failed"`, store the findings, and set the top-level `"halted": {"reason": "<gate> failed after one fix", "checkpoint": <id>}`. The Stop hook blocks ending the turn mid-checkpoint unless this is set. Commit `chore(<slug>): stopped at <gate>, needs human`, tell the human the checkpoint and the findings, and end the turn. Log it with the gate `circuit-breaker`. Everything done so far stays on disk, so `/ai-orchestrator resume <slug>` continues after their input. On resume, remove `halted` before continuing.

### On pass
Set all the gates and the checkpoint's `status` to `"passed"`. Post one line to the user, e.g. `✓ 2/5 Add review endpoint (behavior ✓ ui n/a review ✓)`. Commit `feat(<slug>): checkpoint N <title>`. End the turn. The next session runs `/ai-orchestrator resume <slug>`.

## Phase 3: Wrap-up

Use one `general-purpose` subagent to:
- run the full suites (Project config → *All tests*, *Lint*, *Build*, and all UI e2e specs), to check that later checkpoints didn't break earlier ones. This is the only full-suite run of the feature;
- add an entry under Unreleased in `CHANGELOG.md`;
- check `FILEMAP.md` is complete, and update `.ai-engineering/PRD.html` if the feature changed scope or business rules;
- consolidate `LEARNINGS.md`: promote any lesson that now appears in 2 or more Log entries (across all features, not just this one) to a **Rule** citing those entries, and merge Rules that say the same thing. It must never edit or delete a Log entry.
- these shared-file edits are made on the selected feature branch; they reach the detected base only through the Phase 4 merge step.
- in the same pass, when the feature diff matches a trigger, run that skill. `ai-security` when it touches auth, SQL, migrations, or workflows. Skip `ai-security` when the diff touches none of those. `ai-write` when it changes a public interface, a documented behaviour, or a command a README shows. Both run when both match. Neither waits for the other.

If anything fails, treat it as a Gate 1 failure on the last checkpoint. First reopen that checkpoint in the JSON: set `gates.behavior.status` to `"failed"`, set `ui` and `review` back to `"pending"` (leave `ui` alone if it's `"n/a"`), and set `status` to `"pending"`. Then run the fixer with `[checkpoint <slug>#<id> fix]`.

Before opening Phase 4, finish and commit Phase 3 changes under the commit-as-you-go rule. Finish any outstanding review artifacts on the selected branch before pinning approval. Stage each existing `.ai-engineering/workflow/reviews/<slug>-*.md` separately; include `.ai-engineering/recap.html` only if the user explicitly requested and created it. Never use a glob with no match. Commit those artifacts, then synchronize the selected checkout:

1. Reconfirm the selected checkout and branch. The current checkout is valid; if using
   a linked worktree, confirm its exact Git-listed path. Run
   `git status --porcelain --untracked-files=all` and require a clean tree. Capture
   the full branch ref with `git symbolic-ref --quiet HEAD`, then capture its full
   commit with `git rev-parse <selected branch ref>`. Resolve the base using the detection
   order in `.ai-engineering/brainstorm.html` §6.7; if it says ask, ask once rather
   than guessing. Identify its full local ref as `base_ref`; run
   `git rev-parse <base_ref>` and retain its exact full commit as the rebase target.
   Never fetch or sync remote state, or merge an unapproved sibling.
2. From the selected checkout run `git rebase <detected base>`. If a conflict is clear, resolve
   it in the selected checkout, stage only the resolved paths, and continue the rebase.
   If either side's intent is unclear, run `git rebase --abort` first. Verify the original branch,
   feature commit, tree ID and clean status are restored before writing
   `lifecycle.phase: blocked`; if restoration cannot be verified, preserve the current
   state and stop without changing lifecycle state or claiming a clean restoration.
3. After a clean rebase or clear resolution, rerun affected behavior checks, rerun
   affected UI checks only when the checkpoint has a UI gate, then rerun the affected
   review gate only when the rebase changed files, and only on that diff. On any failed check, abort an active rebase first, restore the selected
   feature branch to its captured pre-rebase commit only when the tree is clean, and
   verify the original branch, feature commit, tree ID and clean status before writing
   `blocked`. If any restoration check fails, stop without changing checkpoint state or
   claiming clean preservation.
4. After all affected gates pass, rerun `git rev-parse <base_ref>` and require its exact
   full commit to equal the target used for the rebase. If it moved, rebase onto the
   detected base again and rerun affected gates before review. Run
   `git rev-parse <selected branch ref>` and capture that exact full commit as
   `lifecycle.reviewed_feature`. Use the checkpoint-gated state update to set
   `lifecycle.base_ref`, retain the exact full commit as `lifecycle.reviewed_base`, set
   `lifecycle.phase` to `awaiting-app-review` and `lifecycle.app_review` to `pending`,
   then make and verify a checkpoint-only commit.
5. Only then proceed to Phase 4 with the exact pending checkpoint commit SHA. Keep the
   selected checkout and branch in place.

## Phase 4: Human stop 2, app review

The feature isn't done until a human has looked at it. Before asking, verify the
lifecycle is `awaiting-app-review` with `app_review: pending`, `reviewed_base` equal
to the exact detected base commit recorded in Phase 3, and a clean selected checkout
whose `HEAD` equals its checked-out branch ref. Capture that exact full branch SHA
from `git rev-parse <selected branch ref>` as `PENDING_REVIEW_SHA`; Phase 3 guarantees
it is the pending checkpoint-only review commit. Make sure the dev server is running,
then use `AskUserQuestion` to ask the user to try the feature. Include:

- the routes to open, and which role or test login to use for each (from Project config → *Roles* and *Automated sign-in*);
- a checkpoint summary: sizes, retries per gate, and test counts per layer;
- the prototype paths, so they can compare;
- any deferred MINOR or `[intentional?]` notes.

Offer three choices: **Approve**, **Request changes**, **Stop here**.

Do not use the former manual Git merge and `ai-eng worktree rm` close flow.

- **Request changes:** before asking, resolve the exact Git-listed checkout holding
  `.ai-engineering/workflow/checkpoints/<slug>.json`—the current checkout or a
  configured managed worktree—and record its actual checked-out branch ref
  (`refs/heads/<branch>`) and full `HEAD` SHA of the checkpoint-only pending-review
  commit as `PENDING_REVIEW_SHA`. After the human chooses Request changes, first run
  `ai-eng worktree request-changes <slug> <PENDING_REVIEW_SHA>` from the repository.
  The command resolves the unique checkout from that exact checkpoint and verifies
  that its `HEAD` and actual branch-ref tip still equal the token and its checkpoint
  is `awaiting-app-review` with `app_review: pending`; the branch may have any name.
  It atomically commits only the transition to `implementation`, clears app-review
  status and both reviewed SHAs, then reports the new commit. If the SHA is stale or
  any check fails, preserve all work and return to app review; never substitute a
  newer SHA. Only after that transition succeeds, log the feedback in `LEARNINGS.md`
  with the gate `human`. Something every automated gate missed is the highest-value
  learning, so also promote it to a Rule right away and say which gate should have
  caught it. Turn the feedback into new checkpoints appended to the JSON (next `id`,
  with `builds_on` the last one). Run them through Phase 2 and Phase 3 without asking
  again at checkpoint level, because the feedback is the approval. Then return to
  this app review.
- **Approve:** Never invoke `ai-visual-recap` automatically or create `.ai-engineering/recap.html`. The recap is optional and never required for merge. Only when the user explicitly invokes `/ai-visual-recap` themselves may a recap be created; its absence must not delay approval, merge, or worktree removal.
  After app approval, recommend **PR** when a forge remote is available and
  **Local merge** otherwise. Then let the human choose **PR**, **Local merge**, or
  **Keep the branch**; app approval alone does not choose an integration route.
  - **PR:** hand off to `/ai-pr`; do not invoke the local merge transaction.
  - **Keep the branch:** leave the approved branch and checkout in place and do not
    merge or remove them.
  - **Local merge:** continue below.
  1. Confirm the selected checkout is clean and its full `HEAD` equals its checked-out branch ref. All review artifacts must already be committed before the Phase 3 review pin. If any new artifact or code change remains, return to Phase 3 and obtain renewed app review instead of committing it after the pin. Read the already pinned `lifecycle.reviewed_feature` from the checkpoint and record `REVIEWED_FEATURE_SHA=<that exact full commit ID>`; never recapture the metadata-only `HEAD`.
  2. After the human approves, verify `lifecycle.reviewed_base` still equals the exact commit at `lifecycle.base_ref` and `lifecycle.reviewed_feature` is still an ancestor of the selected branch tip. Do not replace either reviewed SHA with a later metadata-commit tip. Use the checkpoint-gated state update in the selected checkout to retain the exact full `lifecycle.reviewed_base` and `lifecycle.reviewed_feature` SHAs, then set `lifecycle.app_review: approved` and `lifecycle.phase: ready-to-merge`. Confirm the update passed its gate, all gates passed, both reviewed refs are current, and the checkout remains clean. Stage and make a second, distinct checkpoint-only commit containing only `.ai-engineering/workflow/checkpoints/<slug>.json`; verify it preserves both reviewed SHAs and leaves the reviewed feature code tree unchanged. If the checkpoint is missing, invalid, stale, or the update makes the checkout dirty, stop without closing or removing anything.
  3. Invoke exactly `ai-eng worktree merge <slug>` for the close transaction. This command owns the compare-and-swap transaction, exact-parent verification and safe refresh of any checkout holding the detected base; do not perform any part of that transaction yourself. It leaves the feature branch and checkout in place and proposes `ai-eng worktree rm <slug>` for explicit cleanup. Do not switch branches, fetch, or close an unapproved sibling. If the detected base moved before merge, preserve the feature files; the command clears the stale review SHAs and returns it to `implementation`. Rerun affected gates and obtain renewed human app review before retrying. Never write lifecycle phase `complete`.
  4. Claim the feature integrated only after the command succeeds and Git confirms the exact reviewed-parent merge on `lifecycle.base_ref`. The feature checkout remains available until someone explicitly removes it. Never push.
  The merge commit is the single integration point for shared files — `CHANGELOG.md`, `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md`, and `.ai-engineering/PRD.html` when scope changed.
- **Stop here:** commit whatever is outstanding on the selected feature branch and leave it unmerged.

## Lifecycle

Lane: standard, full
Writes: .ai-engineering/workflow/checkpoints
Read by: humans, the next checkpoint worker
Dies: when the feature is approved or the plan is closed
Stop: approve
Stop words: approve, ok, go, adelante
Stop confirms: the app review, or a checkpoint plan only when resuming a pending legacy plan
Stop runs: merge after app-review approval, or continue Phase 2 after legacy plan approval
Next: none — Phase 4 closes after app review approval; recap is optional and user-invoked.
