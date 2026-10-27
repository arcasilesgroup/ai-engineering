---
name: ai-orchestrator
description: Build a whole feature end-to-end through subagents. It plans gated checkpoints, writes tests and prototypes, then loops each checkpoint through implement → behavior gate (CLI/code tests, UI e2e last) → UI gate (live vs prototype) → adversarial review gate until every checkpoint passes, then hands it to a human to review. Use when the user says "build X", "orchestrate X", "/ai-orchestrator <feature>", or asks to resume an orchestrated feature.
license: MIT
---

# Orchestrator

You coordinate; you don't do the work. Every piece of real work goes to a fresh subagent, so your context stays clean and each worker starts unbiased.

**Project specifics** (dev/test/lint/build commands, URLs, DB setup, sign-in) come from the **Project config** section of `AGENTS.md`. Pass the relevant values into every worker prompt so workers don't have to hunt for them.

## Approval stops

On a fresh run, the human approves the brainstorm before Phase 0 and reviews the app
in Phase 4. A new plan backed by that approved brainstorm opens in the viewer and
continues to Phase 2 without another plan-approval question. Only a resumed legacy
plan with `phase: awaiting-plan-approval` and `plan_approval: pending` keeps the
Phase 1 checkpoint-review stop.

Everywhere else, decide and keep going:
- **Ambiguity:** choose the option most consistent with `.ai-engineering/PRD.html`, `.ai-engineering/brainstorm.html`, `DECISIONS.md` and the existing code, and log it as an `assumptions` entry in the checkpoint JSON. The human sees those at the next review. The brainstorm gate, below, refuses a missing, stale, or unrelated interview before any of this runs.
- **Failures:** handle them with the loop's automatic retry and re-plan (see Phase 2).
- Never pause for permission to run tests, start servers, or fix code.
- The only mid-run stop is the final circuit breaker in Phase 2.

## Context rules (non-negotiable)

- **Never read source code, diffs, test output or screenshots yourself.** Subagents read them and report back in a few lines.
- **Checkpoint progress lives on disk** in `.ai-engineering/workflow/checkpoints/<slug>.json`; that file is the source of truth for checkpoint status. Phase 0's read-only `ai-eng worktree list` is the source of truth for worktree existence, paths, cleanliness and reported lifecycle status. Change the checkpoint file only with Edit or Write, never through Bash. The same hook validates every write to it: no gate can be passed out of order, no checkpoint can be marked passed with a gate still open, and no checkpoint can be touched while an earlier one is open. Update it after every step, so `/ai-orchestrator resume <slug>` can pick up after a crash or `/clear`.
- **Every subagent prompt:**
  - in Phase 2 and later, **starts with the gate marker** `[checkpoint <slug>#<id> <stage>]`, where `<slug>` is the feature slug you were asked to build and `<stage>` is one of `tests`, `implement`, `behavior`, `ui`, `review` or `fix`. The TypeScript checkpoint guard (`src/guards/checkpoint.ts`, in the chain) reads it and blocks the call if:
    - an earlier checkpoint hasn't passed;
    - this checkpoint has already passed;
    - or the gate before this one hasn't passed.

    **If the hook blocks you, never work around it.** Fix the state it names: finish the earlier gate, or reopen the checkpoint;
  - is self-contained: paths to read, the checkpoint slice, and what to return;
  - tells the worker to read the **Rules** section of `LEARNINGS.md` first, plus any Log entries whose tags match the work;
  - ends with: *"Return at most 15 lines: result, files changed, failures. No code, no logs."*
- **Subagents can't spawn subagents.** When a prompt points a worker at a skill that says "launch a subagent", add: *"You are already a subagent. Do those steps yourself."* Anything that needs parallel subagents (prototypes, test writers, UI reviewers), you launch directly, several `Agent` calls in one message.
- **Fresh workers only:** use a new subagent for each step and each fix attempt. Don't continue an earlier one with SendMessage. A worker that wrote the code never reviews it.

## Commits: commit as you go

Every step that changes files ends with a commit on `feat/<slug>`, so the git history is a full, resumable record of the run. You make the commits yourself with Bash; the output is small.

- **Tree and branch:** Work in the current checkout by default. When isolation is needed, `ai-eng worktree new <branch>` creates a Git-listed checkout from the detected base; on resume, use its exact listed path and continue only if it is clean and trusted. Never derive a path or switch a branch. Everything is committed on the feature branch, and `ai-eng worktree merge <slug>` makes one `--no-ff` merge against the detected base after app review.
- **Stage explicit paths only.** Never use `git add -A` or `git add .`. The session owns its worktree now, so a loose stage can no longer sweep a sibling session's edits, but an explicit list keeps each commit the slice it claims and keeps the design slots out. Stage the step's `changed_files`, its test files, `.ai-engineering/workflow/checkpoints/<slug>.json`, `.ai-engineering/workflow/test-plans/<slug>.json`, `.ai-engineering/workflow/prototypes/<slug>*`, `.ai-engineering/workflow/reviews/<slug>-*.md`, and whichever of `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md` and `CHANGELOG.md` the step touched. Never stage a design slot (`.ai-engineering/brainstorm.html`, `.ai-engineering/spec.html`, `.ai-engineering/plan.html`) from inside a feature checkout; dirty design files stay in their original checkout when a worktree is created. Do not stage `.ai-engineering/workflow/playwright/`, `.env*` or files that were in the Phase 0 baseline.
- **When to commit, and with which message.** The `commit-msg` hook (`src/floor/index.ts`) accepts any of the eleven Conventional Commit types — `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert` — with an optional scope matching `[a-z0-9._/-]+` (no `#`); it checks nothing about the body. This repo's house convention still puts the checkpoint number in the body rather than the scope — the hook does not enforce that — so `plan`, `gate` and `wip` are gone and the number moved off the scope. Each message ends with the co-author trailer.

| After | Message |
|---|---|
| Plan approved (Phase 1) | `chore(<slug>): plan checkpoints, test plan, prototypes` |
| 2a tests written | `test(<slug>): checkpoint N failing tests for <title>` |
| 2b implement | `feat(<slug>): checkpoint N <title>` |
| Each gate result | `chore(<slug>): checkpoint N <gate> gate passed` or `chore(<slug>): checkpoint N <gate> gate failed (attempt k)`, with the JSON and the LEARNINGS entry |
| Each fix | `fix(<slug>): checkpoint N <root cause, in a few words>` |
| Re-plan split | `chore(<slug>): replan split N into N..M` |
| Wrap-up | `docs(<slug>): changelog, filemap, learnings` |
| Circuit-breaker stop | `chore(<slug>): stopped at <gate>, needs human`, committed before you stop |

- **Nothing to commit?** If a step changed no files (a gate that only ran checks still changes the JSON), skip that commit. Never make an empty commit, and never pass `--no-verify`.

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

- Before any new or resumed work, run the same read-only, local preflight used by
  ai-brainstorm: `ai-eng worktree list`, then `ai-eng worktree list <slug>` when the
  exact requested state is not already present. The list reports only Git-registered
  checkouts and their lifecycle checkpoints; it does not infer a feature from a
  brainstorm or an unregistered folder. The former `approval-before-start` projection
  required approval within 14 days and a matching complete status line. That projection
  is read-only and is no longer emitted; a brainstorm never authorizes work. Once a
  checkpoint exists, it alone is authoritative; missing, malformed or contradictory
  checkpoint state is unknown and never falls back to brainstorm. unknown/pending and cannot authorize work.
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
- If a listed worktree with the same slug has dirty or unknown status, or is missing
  or untrusted, preserve it, report its exact Git-listed path and evidence, and stop
  Phase 0 immediately. Do not run `ai-eng worktree new`, resume it, run
  `ai-eng worktree rm`, reset it, switch branches, or otherwise mutate it.
- Semantic near-matches are advisory only, never a substitute for the exact slug.
- Only if that same-slug entry is clean, trusted and already on its feature branch, resume
  it using its exact Git-listed path; never derive a path or switch a branch.
- If the slug is not listed, first classify the other work. Clearly unrelated work
  may continue untouched. A likely overlap, or dirty/missing/uncertain work that could
  overlap, means pause here and ask the human for a decision. Otherwise work in the
  current checkout by default. If another feature is active there, or isolation was
  requested, run `ai-eng worktree new <branch>` and use the exact Git-listed path;
  the branch may have any valid Git name. Dirty design files stay in the current
  checkout and the command warns that they do not travel. If creation refuses, report
  the reason and stop; do not modify the files or branch to force it.
  No file hints are accepted; hints never authorize implementation or replace the
  approved checkpoint's `files` list.
- Record the selected worktree's clean state as a baseline. Delegate environment
  readiness to one `general-purpose` subagent, which reports ready or blocked, and
  runs from the selected feature worktree without modifying any other worktree:
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

Run Phase 1 and its workers from the selected feature worktree. Create the checkpoint
plan, test plan and prototypes only in the selected feature worktree. Never create a
checkpoint plan in the primary checkout or copy any plan between worktrees.

1. **Checkpoints:** run the `checkpoint-planner` agent with the feature request. Its first write of `.ai-engineering/workflow/checkpoints/<slug>.json` in the selected checkout must include `gates` and `ui` for each checkpoint and this lifecycle: `phase: implementation`, `plan_approval: approved`, `app_review: not-started`, `base_ref: null`, `reviewed_base: null`, and `reviewed_feature: null`. The checkpoint gate rejects a new plan with missing or contradictory state or one written outside the selected checkout at its matching slug path. If it comes back with questions, don't ask the user. Answer them yourself from the PRD, the decisions and the code, re-run it with those answers, and log them as `assumptions`.
   - Resumed legacy plans keep their existing lifecycle: `awaiting-plan-approval` requires `plan_approval: pending`, `app_review: not-started`, and cleared review SHAs.
2. **Test plan:** run a `general-purpose` subagent to do steps 1–2 of `ai-test-planner`. That's the plan only, no tests yet: it writes `.ai-engineering/workflow/test-plans/<slug>.json`, with every case linked to a `checkpoint` and each checkpoint's test commands added to its `verify` array.
3. **Prototypes:** list the distinct `ui.prototype` paths across the checkpoints. Launch one `general-purpose` subagent per prototype **in parallel**. Each one follows `ai-prototype` for its screen, covering the states named in `ui.states`, and skips the `open` step.

4. **Open the plan:** start the viewer if it isn't already running with `python3 -m http.server 8765` from the selected feature worktree root in the background (not `docs/`, so prototype links resolve), then open `http://localhost:8765/.ai-engineering/workflow/checkpoints/viewer.html?plan=<slug>`. It updates live as the JSON changes and remains the progress view for the run. The checkpoint hook checks the local brainstorm artifact's matching feature slug, approval date within 14 days, and matching `complete ·` status line on this first approved lifecycle write. This is local guardrail validation of the HTML approval stamp, not independent proof of who approved it. Then proceed directly to Phase 2 without another approval question.

For a resumed legacy plan that is still pending at its checkpoint review, preserve its prior human _stop_ 1: checkpoint review. Show the viewer details and use `ask_user_question` to offer: **Approve**, **Edit**, or **Stop**. Do not begin Phase 2 or dispatch its workers until the human approves the checkpoint plan. After approval, set the lifecycle phase to `implementation`, persist `plan_approval: approved`, `app_review: not-started`, and cleared review SHAs, and confirm the guarded write succeeded. On **Edit**, keep plan approval pending, update the plan and ask again. This legacy path does not apply to a new plan started from an approved brainstorm.

## Phase 2: Checkpoint loop

For each checkpoint in `id` order, and only once the previous one has `status: "passed"`:

### a. Write the tests first
Use one `general-purpose` subagent per layer, launched in parallel: unit, and API. Each follows step 3 of the test-planner skill for this checkpoint's cases only. If `ui` is set, one more subagent writes the UI e2e cases (step 4). The tests should fail at this point, because nothing is implemented yet. A test that passes before implementation is suspicious; report it.

### b. Implement
Use one `general-purpose` subagent. Give it:
- the checkpoint's `goal`, `tasks`, `files` and `acceptance`;
- the test files it has to turn green;
- for UI checkpoints, the `ui.prototype` path to match, plus its `.ai-engineering/workflow/prototypes/<name>.states.json`. The live page must use **the same field labels and button text**, and support the same states, because the UI gate drives both sides with identical steps;
- the rule "follow `AGENTS.md`, reuse existing helpers, update `FILEMAP.md` (and `PERMISSIONS.md` if access changes)".

It must not edit the tests. If it believes a test is wrong, it reports that instead. It returns the list of files it changed; record that list in the JSON as `changed_files`.

### c. Gate 1: Behavior
Use one `general-purpose` subagent. It runs the checkpoint's `verify` commands **in layer order: unit → API → CLI (lint, build, health `curl`) → UI e2e**, and stops at the first layer that fails. The UI e2e layer runs only if everything below it passed. It returns PASS, or FAIL with each failing case and its likely cause.

### d. Gate 2: UI (skip if `gates.ui.status` is `"n/a"`)
Run `ai-review-ui` steps 2–4 yourself in **gate mode**, using `ui.route`, `ui.prototype` and `--scope <ui.scope joined by commas>`. Step 2 re-checks that the app is up and the sign-in session is still valid, and gate mode checks the scenario's `route` matches `ui.route`, so a dead server or a stale route never shows up as false mismatches. That way only the regions this checkpoint has built are captured and judged. The capture script puts both sides in the same state for each scenario, and prints only one line per state, so run it yourself. Then launch the two reviewers in parallel. **The gate passes** when every live-reproducible state is `match` (a `MISMATCH` means the page behaves differently from the prototype) and there are no `high` or `med` findings, except ones tagged `[intentional?]`. Log those as notes; they don't fail the gate.

### e. Gate 3: Adversarial review
Run `ai-adversarial-loop` yourself, as its coordinator, with the checkpoint slice and `changed_files`. Up to 4 rounds, `adversarial-reviewer` (the critic) and `fixer` debate through `.ai-engineering/workflow/reviews/<slug>-<id>.md`; each keeps its memory across rounds, and a deadlock goes to an arbiter.

- **Loop returns PASS and the fixer changed nothing:** the gate passes.
- **Loop returns PASS but the fixer changed code:** re-run Gate 1, and Gate 2 if it applies, with the updated `changed_files`. If they pass, the gate passes. If either fails, it goes to that gate's failure path as usual.
- **Loop returns FAIL** (it hit the round cap): that's one failed `review` attempt, with the open findings as its findings. It goes to the failure path, where the re-plan and circuit breaker still apply. In that path, the "fixer" for a review failure is the next adversarial loop.

Record any MINOR findings in `notes`.

### On failure
1. Set the gate to `"failed"`, increase its `attempts` by one, and store its findings.
2. Hand **only those findings plus `changed_files`** to a **new** `general-purpose` fixer subagent. It fixes the root cause, doesn't edit the tests unless a finding says the test itself is wrong, and returns the files it changed plus three lines: `ROOT CAUSE:`, `FIX:`, `LESSON:`. The lesson is one sentence that would have prevented the failure.
   Append a Log entry to `LEARNINGS.md` straight away, using the template in that file: the failure is the gate's findings summary, and the root cause, fix and lesson come from the fixer. Write it even if a later attempt fails; failed fixes are learnings too.
3. Re-run **from Gate 1**, because a fix can break behavior that passed before.
4. **Automatic re-plan:** if any gate reaches 3 failed attempts on one checkpoint, don't ask the user. Run `checkpoint-planner` on that checkpoint alone, together with its accumulated findings, and have it split the checkpoint into smaller ones. Insert them in its place, renumbering the later checkpoints, and continue the loop.
5. **Circuit breaker (the only mid-run stop):** if a checkpoint that came out of a split also reaches 3 failed attempts, set the top-level `"halted": {"reason": "<gate> failed 3× after split", "checkpoint": <id>}` in the plan JSON. The Stop hook blocks ending the turn mid-checkpoint unless this is set. Then stop and tell the user. Give them the checkpoint, the last findings from each gate, and what was tried. Log it with the gate `circuit-breaker`; once the user explains the real cause, log that cause and promote it to a Rule. Everything done so far stays on disk, so `/ai-orchestrator resume <slug>` continues after their input. On resume, remove `halted` before continuing.

### On pass
Set all the gates and the checkpoint's `status` to `"passed"`. Post one line to the user, e.g. `✓ 2/5 Add review endpoint (behavior ✓ ui n/a review ✓, 1 retry)`, and move on to the next checkpoint.

## Phase 3: Wrap-up

Use one `general-purpose` subagent to:
- run the full suites (Project config → *All tests*, *Lint*, *Build*, and all UI e2e specs), to check that later checkpoints didn't break earlier ones;
- add an entry under Unreleased in `CHANGELOG.md`;
- check `FILEMAP.md` is complete, and update `.ai-engineering/PRD.html` if the feature changed scope or business rules;
- consolidate `LEARNINGS.md`: promote any lesson that now appears in 2 or more Log entries (across all features, not just this one) to a **Rule** citing those entries, and merge Rules that say the same thing. It must never edit or delete a Log entry.
- these shared-file edits are made on `feat/<slug>` inside the worktree; they reach the primary tree only through the Phase 4 merge step, which is their single writer there.
- in the same pass, when the feature diff matches a trigger, run that skill. `ai-security` when it touches auth, SQL, migrations, or workflows. `ai-write` when it changes a public interface, a documented behaviour, or a command a README shows. Both run when both match. Neither waits for the other.

If anything fails, treat it as a Gate 1 failure on the last checkpoint. First reopen that checkpoint in the JSON: set `gates.behavior.status` to `"failed"`, set `ui` and `review` back to `"pending"` (leave `ui` alone if it's `"n/a"`), and set `status` to `"pending"`. Then run the fixer with `[checkpoint <slug>#<id> fix]`.

Before opening Phase 4, finish and commit Phase 3 changes under the commit-as-you-go rule. Finish any outstanding review artifacts on the feature branch before pinning approval. Stage each existing `.ai-engineering/workflow/reviews/<slug>-*.md` separately; include `.ai-engineering/recap.html` only if the user explicitly requested and created it. Never use a glob with no match. Commit those artifacts, then synchronize the feature worktree:

1. Reconfirm the selected checkout with read-only `ai-eng worktree list`; proceed only
   when its exact Git-listed path, branch and checkpoint are trusted and clean. Resolve
   `lifecycle.base_ref` from the detected base and record its full current commit as
   `lifecycle.reviewed_base`. Capture the feature branch's full commit as
   `lifecycle.reviewed_feature`, set `phase` to `awaiting-app-review` and
   `app_review` to `pending`, then make and verify a checkpoint-only commit. Do not
   rebase or otherwise synchronize the feature branch: if the detected base changes,
   the review is invalidated and the affected gates and app review must run again.
2. After affected checks pass, continue to Phase 4 with the exact pending checkpoint
   commit SHA; keep the feature checkout and branch in place.

## Phase 4: Human stop 2, app review

The feature isn't done until a human has looked at it. Before asking, verify the
lifecycle is `awaiting-app-review` with `app_review: pending`, `reviewed_base` equal
to the exact detected base commit recorded in Phase 3, and a clean feature checkout
whose `HEAD` equals `refs/heads/feat/<slug>`. Capture that exact full branch SHA from
`git rev-parse refs/heads/feat/<slug>` as `PENDING_REVIEW_SHA`; Phase 3 guarantees it
is the pending checkpoint-only review commit. Make sure the dev server is running,
then use `AskUserQuestion` to ask the user to try the feature. Include:

- the routes to open, and which role or test login to use for each (from Project config → *Roles* and *Automated sign-in*);
- a checkpoint summary: sizes, retries per gate, and test counts per layer;
- the prototype paths, so they can compare;
- any deferred MINOR or `[intentional?]` notes.

Offer three choices: **Approve**, **Request changes**, **Stop here**.

Do not use the former manual `git merge --no-ff feat/<slug>` and `ai-eng worktree rm <slug>` close flow.

- **Request changes:** before asking, capture the full current `HEAD` SHA of the
  checkpoint-only pending-review commit as `PENDING_REVIEW_SHA`. After the human
  chooses Request changes, first run
  `ai-eng worktree request-changes <slug> <PENDING_REVIEW_SHA>` from the primary
  checkout. The command accepts only a clean, live managed `feat/<slug>` worktree
  whose current full checkpoint-only commit SHA still equals that token and whose
  checkpoint is `awaiting-app-review` with `app_review: pending`. It atomically
  commits only the transition to `implementation`, clears app-review status and both
  reviewed SHAs, then reports the new commit. If the SHA is stale or any check fails,
  preserve all work and return to app review; never substitute a newer SHA. Only
  after that transition succeeds, log the feedback in `LEARNINGS.md` with the gate
  `human`. Something every automated gate missed is the highest-value learning, so
  also promote it to a Rule right away and say which gate should have caught it.
  Turn the feedback into new checkpoints appended to the JSON (next `id`, with
  `builds_on` the last one). Run them through Phase 2 and Phase 3 without asking
  again at checkpoint level, because the feedback is the approval. Then return to
  this app review.
- **Approve:** Never invoke `ai-visual-recap` automatically or create `.ai-engineering/recap.html`. The recap is optional and never required for merge. Only when the user explicitly invokes `/ai-visual-recap` themselves may a recap be created; its absence must not delay approval, merge, or worktree removal.
  1. Confirm the feature worktree is clean and its full `HEAD` equals `refs/heads/feat/<slug>`. All review artifacts must already be committed before the Phase 3 review pin. If any new artifact or code change remains, return to Phase 3 and obtain renewed app review instead of committing it after the pin. Read the already pinned `lifecycle.reviewed_feature` from the checkpoint and record `REVIEWED_FEATURE_SHA=<that exact full commit ID>`; never recapture the metadata-only `HEAD`.
  2. After the human approves, verify `lifecycle.reviewed_base` still equals the exact commit at `lifecycle.base_ref` and `lifecycle.reviewed_feature` is still an ancestor of the feature branch tip. Do not replace either reviewed SHA with a later metadata-commit tip. Use the checkpoint-gated state update in the selected checkout to retain both exact full SHAs, then set `lifecycle.app_review: approved` and `lifecycle.phase: ready-to-merge`. Confirm the update passed its gate, all gates passed, both reviewed refs are current, and the checkout remains clean. Stage and make a second, distinct checkpoint-only commit containing only `.ai-engineering/workflow/checkpoints/<slug>.json`; verify it preserves both reviewed SHAs and leaves the reviewed feature code tree unchanged. If the checkpoint is missing, invalid, stale, or the update makes the checkout dirty, stop without closing or removing anything.
  3. Invoke exactly `ai-eng worktree merge <slug>` for the close transaction. This command owns the compare-and-swap transaction, exact-parent verification and safe refresh of any checkout holding the detected base; do not perform any part of that transaction yourself. It leaves the feature branch and checkout in place and proposes `ai-eng worktree rm <slug>` for explicit cleanup. Do not switch branches, fetch, or close an unapproved sibling. If the detected base moved before merge, preserve the feature files; the command clears the stale review SHAs and returns it to `implementation`. Rerun affected gates and obtain renewed human app review before retrying. Never write lifecycle phase `complete`.
  4. Claim the feature integrated only after the command succeeds and Git confirms the exact reviewed-parent merge on `lifecycle.base_ref`. The feature checkout remains available until someone explicitly removes it. Never push.
  The merge commit is the single integration point for shared files — `CHANGELOG.md`, `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md`, and `.ai-engineering/PRD.html` when scope changed.
- **Stop here:** commit whatever is outstanding on `feat/<slug>` and leave it unmerged.

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
