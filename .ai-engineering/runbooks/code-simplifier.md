---
owner: operate
---

# Runbook: Code Simplifier

## Purpose

Identifies and reduces code complexity with pattern-aware reconnaissance. Improves readability without changing behavior.

**Distinct from refactor**: refactor changes structure (move, rename, split); code-simplifier reduces complexity within existing structure.

## Schedule

Weekly (Wednesday 5AM) via `ai-eng-code-simplifier.yml`.

## Procedure

1. **Scan complexity**: Run `ruff check src/ --select C901` to find functions with cyclomatic complexity > 10.
2. **Scan cognitive complexity**: Identify functions with cognitive complexity > 15 or nesting > 4 levels.
3. **Scan duplication**: Run `ai-eng policy duplication` to find duplicated blocks > 3%.
4. **Scan dead code**: Identify unused imports, unreachable branches, commented-out code.
5. **Prioritize**: Rank findings by impact (frequency x complexity x change risk).
6. **Propose**: For each finding, provide before/after code examples showing the simplification.
7. **Report**: Create an issue with prioritized recommendations.

## What to Simplify

- Functions > 50 lines -> extract logical sections
- Nesting > 4 levels -> early returns, guard clauses
- Complex conditionals -> extract to named boolean variables
- Repeated patterns -> DRY within the same module (not premature abstraction)
- Dead code -> remove completely (no comments)

## What NOT to Simplify

- Code that is already clear and simple (don't fix what isn't broken)
- Performance-critical hot paths (simplification may hurt performance)
- Generated code or vendored dependencies
- Test fixtures and test data (verbosity is acceptable)

## Output

GitHub issue with:
- Title: `chore(simplify): weekly complexity report YYYY-MM-DD`
- Body: prioritized findings with before/after examples
- Labels: `code-quality`, `simplification`
