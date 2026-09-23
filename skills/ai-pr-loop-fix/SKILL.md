---
name: ai-pr-loop-fix
description: >-
  Post-implementation CI verification loop: pushes the current branch, polls CI via gh,
  diagnoses failures, applies obvious fixes (lint, import, type errors), and loops until
  green or 5 iterations cap. Never auto-merges. Trigger for "fix CI", "get to green",
  "CI loop", "verify CI". Not for diagnosing non-CI failures — use /ai-debug. Not for
  adding test coverage — use /ai-verify. Not for complex logic fixes — report and stop.
license: Apache-2.0
---

# ai-pr-loop-fix — push, poll, fix obvious, report the rest

## What it produces

A CI-green branch, or a clear report of what failed and why the fix is non-trivial.

## Steps

1. **Push the current branch.** `git push`. If push fails (upstream not set), set it and
   push again. If the branch is `main` or `master`, refuse: this skill fixes feature
   branches, not trunks.

2. **Poll CI.** `gh run list --branch <branch> --limit 1 --json databaseId,status,conclusion`.
   If `status` is `completed` and `conclusion` is `success`, skip to step 7. If
   `status` is `in_progress` or `queued`, wait 30s and poll again. Max 3 polls before
   declaring CI stuck (report and stop).

3. **Read the failure.** `gh run view <run-id> --log-failed` to get the actual logs.
   Scan for the first actionable error. The rest are usually cascades.

4. **Diagnose.** Classify the failure:
   - **Obvious**: lint error, missing import, unused variable, type mismatch, formatting.
   - **Logic**: wrong test expectation, broken behaviour, subtle type issue.
   - **Infrastructure**: flaky test, network timeout, dependency resolution.

5. **Fix obvious failures.** Apply the minimal edit, commit with a `fix: ci` prefix,
   push, increment iteration counter, go to step 2. Do NOT refactor while fixing CI.
   One line per fix.

6. **Report logic/infrastructure failures.** Print: the failing job name, the specific
   log lines that matter, and why the fix is not mechanical. Stop. The user decides.

7. **Done.** Print the green run URL. State how many iterations it took. Do NOT merge.
   Do NOT create or update a PR. The user handles merge.

## Iteration budget

Max 5 iterations. Hard cap. After 5:
- If the failure is still obvious, apply the fix but report that the loop budget is
  exhausted and stop before polling again.
- If the failure is unclear, report and stop.

## Anti-patterns

- **Refactoring while fixing CI.** The goal is green, not clean. Fix the error, ship,
  refactor in a separate pass.
- **Guessing at the root cause.** If the logs are ambiguous, say so. A wrong fix wastes
  an iteration budget slot and your trust.
- **Touching tests to make them pass.** If a test fails because the code is wrong, fix
  the code. If the test is wrong, that is a logic fix — report and stop.
- **Running the full test suite locally.** You are verifying CI, not replacing it. Local
  runs waste time and miss environment-specific failures.
- **Auto-merging.** Never. Not even if it is green.

## What this is not

- A replacement for /ai-debug. This skill handles CI failures that have already been
  diagnosed by the CI system. Unknown failures route to /ai-debug first.
- A deployment pipeline. It pushes code; it does not deploy, release, or merge.
- An excuse to skip reading the logs. Every iteration reads `--log-failed` — never guess.

## Done when

- CI conclusion is `success`, or
- A non-trivial failure is reported with evidence, or
- The iteration budget is exhausted with the last state reported.

## Lifecycle

Lane: light
Writes: nothing
Dies: on completion

Source: ai-engineering (own), Apache-2.0.
