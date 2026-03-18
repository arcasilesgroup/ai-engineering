# Maintainability Review Dimension

## Scope Priority
1. **Code clarity** — function complexity, nested conditionals, obscure logic
2. **Naming** — generic names, misleading names, inconsistent conventions
3. **Simplicity** — over-engineering, premature abstractions, SOLID violations
4. **Duplication** — copy-pasted blocks, similar functions, duplicated validation
5. **Documentation** — missing docs on public APIs, stale comments, WHY vs HOW
6. **Error handling** — silent failures, missing null checks, bare except clauses
7. **Testability** — hard-to-test functions, tight coupling, global state

## Philosophy
Boring is better than clever. Clear intent over conciseness. Single responsibility. No premature abstraction.

## Self-Challenge
- When flagging over-engineering, always include a concrete simpler alternative with actual code.
- Is the duplication actually harmful, or is it "healthy duplication" that's easier to understand?
