---
name: debug
description: Use when something is broken and you need to find out why — test failures, runtime errors, crashes, regressions, unexpected behavior. Systematic 4-phase diagnosis — never patches symptoms without finding the root cause.
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-debug

4-phase systematic diagnosis. Refuses to patch symptoms without root cause.

## Phase 1: REPRODUCE

- Reproduce locally. If only on CI, reproduce in a fresh container that
  mirrors CI.
- Capture exact error message, stack trace, environment.
- If you cannot reproduce in 30 minutes, escalate — don't guess.

## Phase 2: ISOLATE

- Bisect against `main`. `git bisect` or manual binary search.
- Disable suspected components one by one.
- Read the actual code path the failing input traverses.

## Phase 3: ROOT CAUSE

- Write down the *causal chain* in plain English.
- A root cause is one where "if X had been different, the bug wouldn't
  exist." If your candidate cause has multiple "if onlys", keep digging.
- Update `LESSONS.md` with the surprising part.

## Phase 4: FIX + REGRESSION TEST

- Write the failing test FIRST (`/ai-test` RED).
- Apply the minimum fix.
- Confirm test passes. Confirm related tests still pass.
- Submit a PR (`/ai-pr`) referencing the bug + this skill's analysis.

## Common mistakes

- Patching the symptom (`if (x === undefined) x = 0`)
- Skipping the regression test ("we'll remember to be careful")
- Stopping at the first plausible cause
- Not reading the actual code (relying on memory or guess)
