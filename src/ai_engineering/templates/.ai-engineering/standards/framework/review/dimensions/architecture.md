# Architecture Review Dimension

## Scope Priority
1. **Necessity and simplification** — YAGNI, custom reimplementations of built-ins
2. **Minimal change scope** — scope creep, unrelated refactoring in feature PRs
3. **Established patterns** — consistency with existing codebase patterns
4. **Code reuse** — existing utilities that should be used instead of new code
5. **Library usage** — battle-tested libraries vs custom implementations
6. **Idiomatic approaches** — using language/framework features correctly
7. **Abstraction appropriateness** — abstract at 3+ use cases, not speculatively

## Process
Find 3 similar implementations in the codebase before flagging pattern violations.
When flagging, always provide a concrete alternative with actual code.

## Self-Challenge
- Is the existing pattern actually good, or is this an opportunity to improve it?
- Does the new code justify a new abstraction, or can it reuse existing ones?
