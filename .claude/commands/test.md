---
description: Generate tests for code and run the test suite
---

## Context

Generates missing tests for specified code and runs the test suite. Follows the project's testing standards and patterns.

## Inputs

$ARGUMENTS - File paths to generate tests for, or "run" to just run existing tests

## Steps

### 1. Determine Stack and Test Framework

Detect the stack from file extensions:
- `.cs` files → NUnit, Moq, FluentAssertions
- `.ts/.tsx` files → Vitest or Jest, React Testing Library
- `.py` files → pytest

Read the relevant standards file:
- `standards/dotnet.md` (Testing section)
- `standards/typescript.md` (Testing section)
- `standards/python.md` (Testing section)
- `standards/testing.md` (Cross-stack philosophy)

### 2. Analyze Code to Test

If $ARGUMENTS includes file paths (not just "run"):
- Read each file to understand its public API
- Identify the happy path and error paths
- Check for existing tests (look for corresponding test file)
- Identify dependencies that need mocking

### 3. Generate Tests

Follow these patterns per stack:

**.NET (NUnit):**
- Create test class in matching test project directory
- Use `[TestFixture]` with `BaseTest` if available
- Name: `{ClassName}Tests.cs`
- Methods: `{Method}_When{Scenario}_Should{Expected}` or `{Method}_{Scenario}_{Expected}`
- Use `[SetUp]` for mock creation
- Use `Assert.EnterMultipleScope()` for grouped assertions
- Test both success and error paths for Result<T> methods

**TypeScript (Vitest/Jest):**
- Create test file: `{component}.test.tsx` or `{module}.test.ts`
- Use `describe` blocks matching the component/function
- Use `it` with descriptive names
- For React components: use `render`, `screen`, `fireEvent` from Testing Library

**Python (pytest):**
- Create test file: `test_{module}.py`
- Use `def test_{function}_{scenario}()` naming
- Use `pytest.fixture` for setup
- Use `pytest.raises` for exception testing

### 4. Run Tests

Execute the test suite:
- .NET: `dotnet test`
- TypeScript: `npm test` or `npx vitest run`
- Python: `pytest`

### 5. Report Results

```markdown
## Test Results

**Status:** PASS | FAIL
**Tests:** X passed, Y failed, Z skipped
**Coverage:** X% (if available)

### New Tests Created
- [file path] - [what it tests]

### Failed Tests (if any)
- [test name] - [failure reason]
```

## Verification

- All new tests pass
- Tests cover both happy path and error paths
- Test names are descriptive and follow conventions
- No hardcoded dates or flaky patterns
