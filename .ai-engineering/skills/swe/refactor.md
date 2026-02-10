# Refactor

## Purpose

Safe refactoring skill: improve internal code structure without changing external behavior. Ensures tests exist before refactoring and validates behavior preservation after each transformation.

## Trigger

- Command: agent invokes refactor skill or user requests code improvement.
- Context: code smells, duplication, excessive complexity, poor naming, long functions.

## Procedure

1. **Tests first** — verify test coverage exists for the target code.
   - If coverage is insufficient, write tests that capture current behavior BEFORE refactoring.
   - Run tests to establish green baseline.

2. **Identify targets** — select specific smells to address:
   - Extract method/function (long functions >50 lines).
   - Rename for clarity (ambiguous names).
   - Simplify conditionals (nested if/else, complex boolean logic).
   - Split modules (files with multiple responsibilities).
   - Remove duplication (rule of three).
   - Reduce coupling (dependency injection over hard-coded deps).

3. **Small steps** — apply one transformation at a time.
   - Run tests after each transformation.
   - If tests fail, revert the last change and investigate.
   - Commit after each successful transformation (optional micro-commits).

4. **Verify** — confirm behavior preservation.
   - All existing tests pass.
   - No new warnings from `ruff check` or `ty check`.
   - Code reads more clearly than before.

## Output Contract

- List of refactoring transformations applied.
- Before/after comparison of key metrics (complexity, line count, duplication).
- All tests pass after refactoring.
- No behavior changes — same inputs produce same outputs.

## Governance Notes

- Never refactor without tests. If tests don't exist, write them first (see `skills/swe/test-strategy.md`).
- Refactoring must not introduce new features or fix bugs — those are separate tasks.
- Keep refactoring PRs separate from feature PRs for clean review.
- Follow `standards/framework/stacks/python.md` code patterns.

## References

- `standards/framework/stacks/python.md` — code patterns and quality baseline.
- `standards/framework/quality/python.md` — complexity thresholds.
- `skills/swe/test-strategy.md` — for writing tests before refactoring.
- `agents/code-simplifier.md` — agent that uses this skill.
