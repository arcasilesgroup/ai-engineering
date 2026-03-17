---
name: simplify
version: 1.0.0
description: 'Reduce code complexity with pattern-aware reconnaissance: guard clauses,
  early returns, extract methods — preserving behavior.'
tags: [simplification, complexity, readability, patterns]
---

# Code Simplifier

## Purpose

Identifies and reduces code complexity with pattern-aware reconnaissance. Improves readability of code without changing behavior. Distinct from refactor: refactor changes structure (move, rename, split), code-simplifier reduces complexity within existing structure.

## Trigger

- Command: `/ai-code-simplifier [files|scope]`
- Context: code has high complexity, deep nesting, or readability issues.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"code-simplifier"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

1. **Reconnaissance** -- scan changed files (`git diff --name-only`) or user-provided scope.

2. **Complexity Analysis** -- measure per function/method:
   - Cyclomatic complexity (threshold: <=10)
   - Cognitive complexity (threshold: <=15)
   - Nesting depth (threshold: <=4)
   - Function length (threshold: <50 lines)

3. **Pattern Detection** -- identify simplification opportunities:
   - Nested conditionals -> guard clauses / early returns
   - Long functions -> extract method
   - Complex boolean expressions -> named predicates
   - Deep nesting -> flatten with early exit
   - Repeated patterns -> extract utility
   - Magic numbers -> named constants
   - Complex list comprehensions -> readable loops or utility functions

4. **Simplify** -- apply transformations preserving behavior:
   - One pattern at a time
   - Run tests after each transformation
   - If tests fail, revert and skip that transformation

5. **Validate** -- run linter + type checker + tests post-simplification.

6. **Report** -- before/after metrics:
   ```
   # Simplification Report
   ## Before: complexity avg 12.4, max 18, nesting avg 3.2
   ## After:  complexity avg 7.1, max 10, nesting avg 1.8
   ## Changes: 5 functions simplified, 2 extracted, 1 inlined
   ## All tests pass
   ```

## When NOT to Use

- **Changing architecture** -- use `refactor` instead.
- **Adding features** -- use `build` instead.
- **No complexity issues** -- don't fix what isn't broken.
