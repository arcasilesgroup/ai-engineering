# Testing Review Dimension

## Scope Priority
1. **Coverage gaps** — missing tests for new code, untested error paths, missing edge cases
2. **Test quality** — structure, naming, isolation, assertion specificity
3. **Mocking scope** — appropriate mock boundaries, over-mocking, unit vs integration balance
4. **Test reliability** — determinism, brittleness, flaky test indicators
5. **Test-code sync** — stale assertions, incomplete negative tests
6. **Optimization boundary** — both sides of fast path/slow path tested

## Critical Anti-Patterns
- No-op tests (test exists but asserts nothing meaningful)
- Testing the mock (asserting mock behavior, not real behavior)
- Wrong method called (test name doesn't match what's tested)
- Incomplete negative assertions (test asserts "not A" but doesn't verify "is B")

## Self-Challenge
- Is the missing test actually valuable, or is the code trivial enough to not need one?
- Is the suggested mock boundary correct for this project's testing philosophy?
