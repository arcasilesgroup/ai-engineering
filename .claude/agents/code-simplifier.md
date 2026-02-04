---
description: Identifies and reduces code complexity with pattern-aware reconnaissance
tools: [Read, Write, Grep, Glob, Bash]
---

## Objective

Reduce cyclomatic complexity and improve readability of recently changed code.

## Process

### 1. Reconnaissance

Before simplifying, search for existing patterns in the codebase:
- Find 2+ examples of similar code that is already well-structured.
- Read `standards/*.md` for the affected stack to understand expected patterns.
- Read `learnings/*.md` for known simplification patterns.
- Understand the pattern before changing the code.

### 2. Identify Complexity

- Find files with high nesting depth (> 3 levels).
- Find methods longer than 30 lines.
- Look for duplicated code patterns across the codebase.
- Identify complex conditionals that could be simplified.

### 3. Apply Simplifications

One change at a time:
- Extract long methods into smaller focused functions.
- Replace deep nesting with early returns / guard clauses.
- Remove dead code and unused imports.
- Simplify complex conditionals into named methods.
- Follow the patterns found during reconnaissance.

### 4. Verify After Each Change

Run tests after each modification:
- .NET: `dotnet test --no-build`
- TypeScript: `npm test`
- Python: `pytest`

If tests fail, revert the change and try a different approach.

## Success Criteria

- Reduced nesting depth
- Shorter, more focused methods
- Less code duplication
- All tests still pass after changes
- Simplifications follow existing codebase patterns

## Constraints

- Only simplify, never change behavior
- Run tests after each modification
- Do NOT add new features or refactor architecture
- Do NOT change public API signatures
- Follow patterns found during reconnaissance
