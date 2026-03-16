---
name: refactor
description: "Improve internal code structure without changing external behavior; use when addressing code smells, duplication, or excessive complexity."
metadata:
  version: 1.0.0
  tags: [refactoring, code-quality, simplification]
  ai-engineering:
    scope: read-write
    token_estimate: 675
---

# Refactor

## Purpose

Safe refactoring skill: improve internal code structure without changing external behavior. Ensures tests exist before refactoring and validates behavior preservation after each transformation.

## Trigger

- Command: agent invokes refactor skill or user requests code improvement.
- Context: code smells, duplication, excessive complexity, poor naming, long functions.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"refactor"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Breaking changes or API migrations** — use `migrate` instead. Refactor preserves behavior; migration changes it.
- **Architecture restructuring** (module reorganization, new layers) — use `arch-review` to analyze first, then refactor individual components.
- **Code review feedback** (PR-level review with approval/rejection) — use `code-review` instead.
- **New feature implementation** — refactor is for existing code improvement, not adding new capabilities.

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

- Never refactor without tests. If tests don't exist, write them first (see `.agents/skills/test/SKILL.md`).
- Refactoring must not introduce new features or fix bugs — those are separate tasks.
- Keep refactoring PRs separate from feature PRs for clean review.
- Follow `standards/framework/stacks/python.md` code patterns.

### Iteration Limits

- Max 3 attempts to resolve the same issue. After 3 failures, escalate to user with evidence of attempts.
- Each attempt must try a different approach — repeating the same action is not a valid retry.

### Post-Action Validation

- After completing refactoring, run `ruff check` and `ruff format --check` on modified files.
- If `.ai-engineering/` content was modified, run integrity-check.
- If validation fails, fix issues and re-validate (max 3 attempts per iteration limits).

## References

- `standards/framework/stacks/python.md` — code patterns and quality baseline.
- `standards/framework/quality/core.md` — complexity thresholds.
- `.agents/skills/test/SKILL.md` — for writing tests before refactoring.
- `.agents/agents/ai-build.md` — agent that uses this skill.
