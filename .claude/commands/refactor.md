---
description: Refactor code while preserving behavior with test verification
---

## Context

Performs targeted refactoring of specified code while ensuring all tests continue to pass. Focuses on improving code quality without changing behavior.

## Inputs

$ARGUMENTS - File paths or description of what to refactor (e.g., "extract method from UserService.GetAsync")

## Steps

### 1. Understand Current State

- Read the target file(s) and understand the current implementation.
- Read related test files to understand expected behavior.
- Check `standards/*.md` for applicable coding standards.
- Run existing tests to establish a passing baseline.

### 2. Plan Refactoring

Identify specific improvements:
- **Extract Method**: Long methods (> 30 lines) → smaller focused methods
- **Guard Clauses**: Deep nesting → early returns
- **Remove Duplication**: Repeated code → shared abstractions
- **Simplify Conditionals**: Complex boolean logic → named methods
- **Improve Naming**: Unclear names → intention-revealing names

Present the refactoring plan to the user before proceeding.

### 3. Apply Changes

Apply one refactoring at a time:
1. Make the change
2. Run tests to verify behavior is preserved
3. If tests fail, revert and try a different approach
4. Move to the next refactoring

### 4. Verify

- Run the full test suite
- Confirm no new warnings or errors
- Check that the refactored code follows project standards

### 5. Report

```markdown
## Refactoring Report

**Files changed:** X
**Tests status:** All passing

### Changes Applied
1. **[file:line]** [What was refactored] → [Result]
2. ...

### Quality Improvements
- Reduced cyclomatic complexity from X to Y
- Reduced nesting depth from X to Y
- Removed X lines of duplicate code
```

## Verification

- All tests pass before and after refactoring
- No behavior changes (same inputs produce same outputs)
- Code follows project standards
- No new warnings introduced
