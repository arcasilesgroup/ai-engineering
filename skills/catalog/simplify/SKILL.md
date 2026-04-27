---
name: simplify
description: Use to refactor for complexity reduction — guard clauses, extract method, flatten nesting, remove dead code — while preserving behavior. TDD precondition required. Trigger for "simplify this", "this is too complex", "reduce nesting", "extract this method", "refactor for readability".
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-simplify

Behavior-preserving refactoring for complexity reduction. Targets
cyclomatic > 10 or cognitive > 15 hotspots, applies a small palette of
proven transforms, and verifies the test suite stays green throughout.

> **TDD precondition.** `/ai-simplify` refuses to run on code without
> coverage. The skill writes RED tests for any uncovered behavior
> before touching the structure.

## When to use

- "Simplify this function / module"
- "Reduce nesting", "flatten this"
- "Extract method here"
- "Remove dead code"
- Pre-rewrite — measure complexity, see if a refactor avoids the rewrite

## Precondition: coverage

1. **Measure coverage** — `bun test --coverage` or `pytest --cov`.
2. **If coverage < 80%** on the target — STOP. Dispatch `/ai-test` to
   add RED tests until pinned. Only then refactor.
3. **Snapshot the test suite** — record green baseline.

## Refactor palette

| Transform | Trigger | Example |
|-----------|---------|---------|
| **Guard clauses** | nested `if` with early returns deferred | invert and `return` early |
| **Extract method** | function > 30 lines or > 1 reason to change | pull lines into named helper |
| **Flatten nesting** | depth > 3 | replace nested branches with table / dispatch |
| **Dead code removal** | unreachable branch / unused symbol | delete with confidence (tests prove safety) |
| **Replace conditional with polymorphism** | type-switch ladder | dispatch via interface |
| **Inline unhelpful indirection** | one-line wrapper that adds no clarity | inline at call site |

## Process

1. **Detect hotspots** — `radon cc` (Python), `eslint complexity`
   (TypeScript), `tokei` for size. Rank by cyclomatic + cognitive.
2. **Verify coverage** — refuse if < 80% on the target.
3. **Pick transform** from the palette. One transform at a time.
4. **Apply** as a minimal diff. Avoid rename + restructure in a single
   commit.
5. **Run tests** — must stay green. If they fail, revert and re-pick.
6. **Re-measure complexity** — confirm reduction. If unchanged, revert.
7. **Commit per transform** with `refactor(<scope>): <transform>` —
   small, reviewable, bisectable.
8. **Emit telemetry** — `simplify.applied` with before/after metrics.

## Hard rules

- NEVER refactor without coverage. Write RED tests first.
- NEVER combine restructure with behavior change — separate commits.
- NEVER weaken thresholds (cyclomatic ≤ 10, cognitive ≤ 15) by
  suppression. Refactor harder or accept risk via `/ai-risk-accept`.
- Test suite must stay green between every transform — no broken
  intermediate states.
- One transform per commit. `refactor(api): guard clause for null user`,
  not `refactor: cleanup`.

## Common mistakes

- Refactoring without tests, then "discovering" a regression in prod
- Bundling rename + restructure ("while I'm here…")
- Stopping at first improvement when the function is still > 10
- Adding `# noqa` or `// eslint-disable` to silence the analyzer
- Over-extraction — a 3-line helper used once is noise, not clarity
- Skipping the re-measure — congratulating yourself on a non-improvement
