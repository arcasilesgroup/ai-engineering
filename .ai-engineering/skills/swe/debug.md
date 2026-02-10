# Debug

## Purpose

Systematic diagnosis skill for identifying, isolating, and fixing bugs. Follows a structured reproduce → isolate → identify → fix → test cycle to ensure root cause resolution, not symptom patching.

## Trigger

- Command: agent invokes debug skill or user reports a bug/error.
- Context: unexpected behavior, test failure, runtime error, or regression.

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

## References

- `standards/framework/quality/python.md` — test and coverage requirements.
- `agents/debugger.md` — agent that uses this skill systematically.
- `agents/verify-app.md` — agent that uses debug for investigating verification failures.
