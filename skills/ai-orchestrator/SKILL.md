---
name: ai-orchestrator
description: Build a whole feature end-to-end through subagents. It plans gated checkpoints, writes tests and prototypes, then loops each checkpoint through implement → behavior gate (CLI/code tests, UI e2e last) → UI gate (live vs prototype) → adversarial review gate until every checkpoint passes, then hands it to a human to review. Use when the user says "build X", "orchestrate X", "/ai-orchestrator <feature>", or asks to resume an orchestrated feature.
license: MIT
---

# Orchestrator

You coordinate; you don't do the work. Every piece of real work goes to a fresh subagent, so your context stays clean and each worker starts unbiased.

**Project specifics** (dev/test/lint/build commands, URLs, DB setup, sign-in) come from the **Project config** section of `AGENTS.md`. Pass the relevant values into every worker prompt so workers don't have to hunt for them.

## Autonomy: the human is asked exactly twice

1. **Checkpoint review**, at the end of Phase 1.
2. **App review**, in Phase 4.

Everywhere else, decide and keep going:
- **Ambiguity:** choose the option most consistent with `.ai-engineering/PRD.html`, `.ai-engineering/brainstorm.html`, `DECISIONS.md` and the existing code, and log it as an `assumptions` entry in the checkpoint JSON. The human sees those at the next review. The brainstorm gate, below, refuses a missing, stale, or unrelated interview before any of this runs.
- **Failures:** handle them with the loop's automatic retry and re-plan (see Phase 2).
- Never pause for permission to run tests, start servers, or fix code.
- The only mid-run stop is the final circuit breaker in Phase 2.

## Context rules (non-negotiable)

- **Never read source code, diffs, test output or screenshots yourself.** Subagents read them and report back in a few lines.
- **All state lives on disk** in `.ai-engineering/workflow/checkpoints/<slug>.json`, and that file is the only thing you read to know where you are. Change it only with Edit or Write, never through Bash. The same hook validates every write to it: no gate can be passed out of order, no checkpoint can be marked passed with a gate still open, and no checkpoint can be touched while an earlier one is open. Update it after every step, so `/ai-orchestrator resume <slug>` can pick up after a crash or `/clear`.
- **Every subagent prompt:**
  - in Phase 2 and later, **starts with the gate marker** `[checkpoint <slug>#<id> <stage>]`, where `<stage>` is one of `tests`, `implement`, `behavior`, `ui`, `review` or `fix`. The `checkpoint-gate` hook (`scripts/checkpoint-gate.py`, PreToolUse) reads it and blocks the call with exit code 2 if:
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

Every step that changes files ends with a commit on the feature branch, so the git history is a full, resumable record of the run. You make the commits yourself with Bash; the output is small.

- **Branch:** Phase 0 runs `git switch -c feat/<slug>` (or `git switch feat/<slug>` on resume). This doesn't touch the working tree. Everything is committed there, and `main` gets one squashed commit per feature at the app review, per the `AGENTS.md` git workflow.
- **Stage explicit paths only.** Never use `git add -A` or `git add .`, because other sessions share this tree. Stage the step's `changed_files`, its test files, `.ai-engineering/workflow/checkpoints/<slug>.json`, `.ai-engineering/workflow/test-plans/<slug>.json`, `.ai-engineering/workflow/prototypes/<slug>*`, `.ai-engineering/workflow/reviews/<slug>-*.md`, and whichever of `LEARNINGS.md`, `FILEMAP.md`, `PERMISSIONS.md` and `CHANGELOG.md` the step touched. Never stage `.ai-engineering/workflow/playwright/`, `.env*` or files that were in the Phase 0 baseline.
- **When to commit, and with which message.** Each message ends with the co-author trailer.

| After | Message |
|---|---|
| Plan approved (Phase 1) | `plan(<slug>): checkpoints, test plan, prototypes` |
| 2a tests written | `test(<slug>#N): failing tests for <title>` |
| 2b implement | `feat(<slug>#N): <title>` |
| Each gate result | `gate(<slug>#N): <gate> passed` or `gate(<slug>#N): <gate> failed (attempt k)`, with the JSON and the LEARNINGS entry |
| Each fix | `fix(<slug>#N): <root cause, in a few words>` |
| Re-plan split | `plan(<slug>): split #N into #N..#M` |
| Wrap-up | `docs(<slug>): changelog, filemap, learnings` |
| Circuit-breaker stop | `wip(<slug>#N): stopped at <gate>, needs human`, committed before you stop |

- **Nothing to commit?** If a step changed no files (a gate that only ran checks still changes the JSON), skip that commit. Never make an empty commit, and never pass `--no-verify`.

## The brainstorm gate

Before Phase 0, read `.ai-engineering/brainstorm.html`. Plan nothing until every line below is true:

- the file exists;
- `<meta name="ai-feature">` is the slug of the feature you were just asked to build;
- `<meta name="ai-approved">` is a `YYYY-MM-DD` date, and that date is within 14 days;
- the status line is `complete ·` that same date.

Anything else is the wrong interview or a stale one: a missing file, a draft, another slug, or an approval older than 14 days. Run `/ai-brainstorm` for this feature and stop. Do not turn the old page into checkpoints. When the slug matches but the date is older than 14 days, say the date out loud and re-run the interview.

When the gate passes, every later phase reads both files. `.ai-engineering/PRD.html` is the conclusions. `brainstorm.html` is the interview: what was wanted, what was decided, and what was refused.

## Phase 0: Preflight

Delegate this to one `general-purpose` subagent, which reports ready or blocked:

- the local DB is up, if the project has one (Project config → *DB status*; if it's down, run *DB start/reset* to apply migrations and the seed);
- the API health check and the web URL both answer (if not, run the *Dev server* command from the repo root in the background);
- `.ai-engineering/workflow/playwright/auth.json` exists, if the app has signed-in pages. If it's missing, the subagent creates it without the user when Project config → *Automated sign-in* describes a way (e.g. a demo-login button or seeded test credentials): it scripts a Playwright sign-in and saves `context.storageState({ path: '.ai-engineering/workflow/playwright/auth.json' })`, using `npx -y -p playwright node <script>` with the script in the scratchpad. It saves one file per role listed under *Roles* (`.ai-engineering/workflow/playwright/auth-<role>.json`), with `auth.json` as a copy of the most privileged one;
- the git tree state (`git status --porcelain`), recorded as a baseline so the feature's files can be told apart from others' work, plus the current branch name (the merge target later);
- the feature branch `feat/<slug>`: switch to it, creating it if it doesn't exist (see Commits).

Only if automatic sign-in is impossible (Project config gives no way), add the manual step to the Phase 1 checkpoint review, so the user handles it in the same stop:
```
! npx -y playwright codegen --save-storage=.ai-engineering/workflow/playwright/auth.json <web URL><sign-in path>
```

## Phase 1: Plan

1. **Checkpoints:** run the `checkpoint-planner` agent with the feature request. It writes `.ai-engineering/workflow/checkpoints/<slug>.json`, with `gates` and `ui` set for each checkpoint. If it comes back with questions, don't ask the user. Answer them yourself from the PRD, the decisions and the code, re-run it with those answers, and log them as `assumptions`.
2. **Test plan:** run a `general-purpose` subagent to do steps 1–2 of `ai-test-planner`. That's the plan only, no tests yet: it writes `.ai-engineering/workflow/test-plans/<slug>.json`, with every case linked to a `checkpoint` and each checkpoint's test commands added to its `verify` array.
3. **Prototypes:** list the distinct `ui.prototype` paths across the checkpoints. Launch one `general-purpose` subagent per prototype **in parallel**. Each one follows `ai-prototype` for its screen, covering the states named in `ui.states`, and skips the `open` step.

4. **Human stop 1: checkpoint review.** First start the plan viewer, if it isn't already running, with `python3 -m http.server 8765` from the repo root in the background (the root, not `docs/`, so the viewer's prototype links resolve). Open `http://localhost:8765/.ai-engineering/workflow/checkpoints/viewer.html?plan=<slug>` for the user; it updates live as the JSON changes, so it doubles as the progress view for the whole run. Then use `AskUserQuestion` to show:
   - the `plain_summary`, then each checkpoint as one plain-language line taken from its `simple` title (e.g. `Step 1: Work out discounted prices`), falling back to `plain.what` for older plans. The user isn't technical, so leave out file names, sizes and gate jargon; the viewer has those under "Technical details";
   - the `assumptions`;
   - the `new_dependencies` (approving the plan approves installing these; add `@playwright/test` whenever `ui` checkpoints exist and it isn't installed);
   - the test counts per layer;
   - the prototype paths, so they can be opened and checked.

   Offer: **Approve**, **Edit** (the user describes the changes), or **Stop**.
   - **Edit:** re-run `checkpoint-planner` with the feedback (and fix the test plan and prototypes if they're affected), then ask again.
   - **Approve:** this is the last question until the app review. Run Phase 2 and Phase 3 without stopping.

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
- in the same pass, when the feature diff matches a trigger, run that skill. `ai-security` when it touches auth, SQL, migrations, or workflows. `ai-write` when it changes a public interface, a documented behaviour, or a command a README shows. Both run when both match. Neither waits for the other.

If anything fails, treat it as a Gate 1 failure on the last checkpoint. First reopen that checkpoint in the JSON: set `gates.behavior.status` to `"failed"`, set `ui` and `review` back to `"pending"` (leave `ui` alone if it's `"n/a"`), and set `status` to `"pending"`. Then run the fixer with `[checkpoint <slug>#<id> fix]`.

## Phase 4: Human stop 2, app review

The feature isn't done until a human has looked at it. Make sure the dev server is running, then use `AskUserQuestion` to ask the user to try the feature. Include:

- the routes to open, and which role or test login to use for each (from Project config → *Roles* and *Automated sign-in*);
- a checkpoint summary: sizes, retries per gate, and test counts per layer;
- the prototype paths, so they can compare;
- any deferred MINOR or `[intentional?]` notes.

Offer three choices: **Approve**, **Request changes**, **Stop here**.

- **Request changes:** first log the feedback in `LEARNINGS.md` with the gate `human`. Something every automated gate missed is the highest-value learning, so also promote it to a Rule right away and say which gate should have caught it. Then turn the feedback into new checkpoints appended to the JSON (next `id`, with `builds_on` the last one). Run them through Phase 2 and Phase 3 without asking again at checkpoint level, because the feedback is the approval. Then return to this app review.
- **Approve:** run `/ai-visual-recap` on this branch first. The page it writes, `.ai-engineering/recap.html`, is the review. Then make sure everything on `feat/<slug>` is committed. Switch back to the branch recorded in Phase 0 and run `git merge --squash feat/<slug>`. Then make one commit whose message describes the feature, per the `AGENTS.md` git workflow. Keep `feat/<slug>` so its step-by-step history stays available. Don't push.
- **Stop here:** commit whatever is outstanding on `feat/<slug>` and leave it unmerged.

## Lifecycle

Lane: standard, full
Writes: .ai-engineering/workflow/checkpoints
Read by: humans, the next checkpoint worker
Dies: when the feature is approved or the plan is closed
Stop: approve
Stop words: approve, ok, go, adelante
Stop confirms: the checkpoint plan
Stop runs: the orchestrator continues Phase 2
Next: ai-visual-recap
