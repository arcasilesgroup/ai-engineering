---
name: debug
version: 1.0.0
description: Systematic bug diagnosis using reproduce-isolate-identify-fix-test cycle;
  use when investigating unexpected behavior, test failures, or runtime errors.
tags: [debugging, diagnosis, root-cause, troubleshooting]
---

# Debug

## Purpose

Systematic diagnosis skill for identifying, isolating, and fixing bugs. Follows a structured reproduce → isolate → identify → fix → test cycle to ensure root cause resolution, not symptom patching.

## Trigger

- Command: agent invokes debug skill or user reports a bug/error.
- Context: unexpected behavior, test failure, runtime error, or regression.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"debug"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

1. **Reproduce** — confirm the bug is reproducible with a minimal case.
   - Gather error output, stack trace, logs.
   - Identify the exact input/state that triggers the issue.
   - If not reproducible, document conditions and stop.

2. **Isolate** — narrow down the scope.
   - Identify the module, function, and line where failure occurs.
   - Use binary search (comment out code, add assertions) to isolate.
   - Check recent changes (`git log`, `git diff`) for regression candidates.

3. **Identify** — determine root cause.
   - Distinguish symptom from cause. Ask "why" at least 3 times.
   - Check edge cases: null/empty inputs, boundary values, concurrency, state mutation.
   - Verify assumptions about dependencies, APIs, and data contracts.

4. **Fix** — implement the minimal correct fix.
   - Fix the root cause, not the symptom.
   - Keep the fix small and focused. One logical change.
   - Ensure fix doesn't break existing behavior — run existing tests first.

5. **Test** — verify the fix and prevent regression.
   - Write a test that fails without the fix and passes with it.
   - Run full test suite to confirm no regressions.
   - Test edge cases around the fixed area.

## When NOT to Use

- **Code review** (PR feedback, pattern assessment) — use `code-review` instead.
- **Test writing** (designing test strategy, writing test suites) — use `test-run` or `test-plan` instead. Debug writes regression tests for fixes; test-run writes comprehensive test suites.
- **Refactoring** (improving code structure) — use `refactor` instead. Debug fixes bugs; refactor improves structure.
- **Architecture analysis** (coupling, cohesion, boundaries) — use `arch-review` instead.

## Examples

### Example 1: Diagnose failing integration test

User says: "This integration test started failing after yesterday's changes; debug it."
Actions:

1. Reproduce failure, isolate failing module/line, and identify root cause from recent deltas.
2. Apply minimal root-cause fix and add a regression test.
   Result: Failure is resolved with reproducible evidence and regression protection.

## Output Contract

- Root cause analysis: what went wrong and why.
- Fix description: what was changed and why.
- Test evidence: new test(s) that cover the fix.
- Regression check: full test suite passes.

## Governance Notes

- Never guess at fixes. Always reproduce first.
- If the bug is in a governance-critical path (hooks, gates, install, update), escalate severity.
- Record any new decisions or risk acceptances in `state/decision-store.json`.
- Do not introduce workarounds that mask the root cause.

### Iteration Limits

- Max 3 attempts to resolve the same issue. After 3 failures, escalate to user with evidence of attempts.
- Each attempt must try a different approach — repeating the same action is not a valid retry.

## References

- `standards/framework/quality/core.md` — test and coverage requirements.
- `.agents/agents/ai-build.md` — agent that uses this skill systematically.
- `.agents/agents/ai-verify.md` — agent that uses debug for investigating verification failures.
- `.agents/skills/explain/SKILL.md` — Feynman-style explanations for root cause understanding.
