# code-simplifier Agent

> Identifies and reduces code complexity with pattern-aware reconnaissance.

## Purpose

Reduce cyclomatic complexity and improve readability of recently changed code. This agent searches for existing patterns before simplifying, ensuring consistency with the codebase.

## When to Use

- After a feature is complete and tests pass
- When code review flags high complexity
- When methods exceed 30 lines or nesting exceeds 3 levels
- As part of periodic codebase health maintenance

## How to Invoke

```
Run the code-simplifier agent on the recently changed files.
```

```
Dispatch code-simplifier to reduce complexity in src/services/OrderService.cs.
```

## What It Does

### 1. Reconnaissance

Before making any changes:
- Finds 2+ examples of similar well-structured code in the codebase
- Reads `standards/*.md` for the affected stack
- Reads `learnings/*.md` for known simplification patterns
- Understands the pattern before changing the code

### 2. Identify Complexity

- Files with high nesting depth (> 3 levels)
- Methods longer than 30 lines
- Duplicated code patterns across the codebase
- Complex conditionals that could be simplified

### 3. Apply Simplifications

One change at a time:
- Extract long methods into smaller focused functions
- Replace deep nesting with early returns / guard clauses
- Remove dead code and unused imports
- Simplify complex conditionals into named methods
- Follow patterns found during reconnaissance

### 4. Verify After Each Change

Runs tests after each modification:

| Stack | Command |
|-------|---------|
| .NET | `dotnet test --no-build` |
| TypeScript | `npm test` |
| Python | `pytest` |

If tests fail, reverts the change and tries a different approach.

## Output Format

```markdown
## Simplification Report

### Changes Made
1. **OrderService.cs:45** — Extracted `ValidateOrderItems()` from `PlaceOrder()` (was 42 lines → 15 + 12)
2. **OrderService.cs:78** — Replaced 4-level nesting with guard clauses
3. **UserService.cs:23** — Removed dead code (unused `LegacyValidate` method)

### Metrics
| File | Before | After |
|------|--------|-------|
| OrderService.cs | Complexity: 18 | Complexity: 8 |
| UserService.cs | Complexity: 12 | Complexity: 10 |

### Tests
✓ All 94 tests pass after changes
```

## Constraints

- Only simplifies, never changes behavior
- Runs tests after each modification
- Does NOT add new features or refactor architecture
- Does NOT change public API signatures
- Follows patterns found during reconnaissance

---
**See also:** [Agents Overview](Agents-Overview) | [/refactor skill](Skills-Code-Quality#refactor)
