# Maintainability Reviewer

Focus on complexity, readability, duplication, naming clarity, hidden coupling,
and code that becomes harder to change safely.

## Inspect

- duplicated logic and scattered policy
- unnecessary branching, nesting, or indirection
- misleading names and hidden control flow
- code paths that make later changes risky or expensive

## Report Only When

- maintainability debt is already harming safe change velocity
- a simpler local pattern exists and the diff moves away from it
- hidden coupling or duplication is likely to cause future defects

## Avoid

- generic cleanup suggestions with no impact
- preference-driven style comments that the formatter or linter already covers
