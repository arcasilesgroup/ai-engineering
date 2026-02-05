# Code Quality Skills

> Skills for maintaining high code quality: review, test, fix, and refactor.

## /review

**Code review against project standards.**

```
/review staged           # Review staged changes
/review src/services/    # Review a directory
/review feature-branch   # Review a branch
```

### Review Process

1. **Load context** — Reads CLAUDE.md, standards, learnings
2. **Identify stack** — Determines which standards apply
3. **Analyze changes** — Reviews against 6 dimensions
4. **Report** — APPROVE or REQUEST CHANGES with details

### The 6 Dimensions

| Dimension | What It Checks |
|-----------|---------------|
| **Correctness** | Logic errors, edge cases, null handling |
| **Security** | OWASP Top 10, injection, auth issues |
| **Performance** | N+1 queries, memory leaks, inefficient algorithms |
| **Maintainability** | Complexity, naming, documentation |
| **Standards** | Project conventions, patterns, formatting |
| **Testing** | Coverage, test quality, edge cases |

### Example Review Output

```markdown
## Code Review: AuthController.cs

**Verdict:** REQUEST CHANGES

### Critical Issues (must fix)
- [ ] Line 45: Token stored in local storage (XSS risk)
- [ ] Line 78: SQL concatenation (injection vulnerability)

### Suggestions (nice to have)
- [ ] Consider extracting token validation to a service
- [ ] Add structured logging for auth events
```

---

## /test

**Generate tests and run the test suite.**

```
/test src/services/UserService.cs    # Generate tests for a file
/test run                            # Run all tests
/test coverage                       # Run with coverage report
```

### Test Generation

When generating tests, the skill:

1. **Reads the source file** — Understands public methods
2. **Finds existing tests** — Follows established patterns
3. **Generates tests** — Covers happy path and error cases
4. **Names clearly** — `MethodName_Scenario_ExpectedResult`

### Test Frameworks Supported

| Stack | Framework | Command |
|-------|-----------|---------|
| .NET | NUnit | `dotnet test` |
| TypeScript | Vitest/Jest | `npm test` |
| Python | pytest | `pytest` |

### Example Generated Test

```csharp
[Test]
public async Task GetUser_WithValidId_ReturnsUser()
{
    // Arrange
    var userId = Guid.NewGuid();
    var expectedUser = new User { Id = userId, Name = "Test" };
    _mockRepository.Setup(r => r.GetAsync(userId))
        .ReturnsAsync(expectedUser);

    // Act
    var result = await _sut.GetUser(userId);

    // Assert
    Assert.That(result.IsError, Is.False);
    Assert.That(result.Value.Id, Is.EqualTo(userId));
}

[Test]
public async Task GetUser_WithInvalidId_ReturnsNotFoundError()
{
    // Arrange
    var userId = Guid.NewGuid();
    _mockRepository.Setup(r => r.GetAsync(userId))
        .ReturnsAsync((User?)null);

    // Act
    var result = await _sut.GetUser(userId);

    // Assert
    Assert.That(result.IsError, Is.True);
    Assert.That(result.FirstError.Type, Is.EqualTo(ErrorType.NotFound));
}
```

---

## /fix

**Fix failing tests, build errors, or lint issues.**

```
/fix tests    # Fix failing tests
/fix build    # Fix build errors
/fix lint     # Fix lint issues
```

### How It Works

1. **Runs the command** — Captures error output
2. **Analyzes errors** — Identifies root causes
3. **Applies fixes** — Makes minimal, targeted changes
4. **Verifies** — Re-runs to confirm fixes

### What It Fixes

| Target | What's Fixed |
|--------|--------------|
| `tests` | Failing assertions, missing mocks, test data issues |
| `build` | Compilation errors, missing references, type mismatches |
| `lint` | Formatting, unused variables, import order |

### Example

```
> /fix tests

Found 2 failing tests:
1. UserServiceTests.CreateUser_WithDuplicateEmail_ReturnsError
   - Expected: Result.IsError = true
   - Actual: Result.IsError = false

2. OrderServiceTests.PlaceOrder_WithInsufficientStock_ReturnsError
   - Expected: InventoryError
   - Actual: null reference exception

Analyzing...

Fix 1: UserService.CreateUser wasn't checking email uniqueness
- Added: await _repository.ExistsAsync(email) check

Fix 2: OrderService.PlaceOrder wasn't null-checking inventory result
- Added: if (inventory == null) return Error.NotFound()

Re-running tests...
✓ All 94 tests pass
```

---

## /refactor

**Refactor code with safety verification.**

```
/refactor src/services/UserService.cs --extract-method
/refactor src/controllers/ --reduce-complexity
```

### Refactoring Process

1. **Snapshot state** — Records current test status
2. **Analyze code** — Identifies refactoring opportunities
3. **Propose changes** — Shows what will change
4. **Apply changes** — Makes the refactoring
5. **Verify** — Runs tests to ensure nothing broke

### Safe Refactoring Principles

- **Tests must pass** before and after
- **Small steps** — One refactoring at a time
- **No behavior changes** — Same inputs produce same outputs
- **Rollback ready** — Easy to undo if tests fail

### Common Refactorings

| Refactoring | When to Use |
|-------------|-------------|
| Extract Method | Long methods, duplicated code |
| Extract Class | Class doing too much |
| Inline | Over-abstraction, unused indirection |
| Rename | Unclear naming |
| Move | Wrong location |

---

## /quality-gate

**Run full quality gate checks.**

```
/quality-gate
```

### What It Checks

| Check | Threshold | Action on Fail |
|-------|-----------|----------------|
| Test Coverage | >= 80% | Block |
| Duplications | <= 3% | Block |
| Reliability | A rating | Block |
| Security | A rating | Block |
| Maintainability | A rating | Warn |
| Secrets | 0 findings | Block |
| Dependencies | 0 critical | Block |

### Example Output

```markdown
## Quality Gate: PASSED

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Coverage | 84.2% | >= 80% | ✓ |
| Duplications | 1.8% | <= 3% | ✓ |
| Reliability | A | A | ✓ |
| Security | A | A | ✓ |
| Maintainability | A | A | ✓ |
| Secrets | 0 | 0 | ✓ |
| Critical Vulns | 0 | 0 | ✓ |

Ready to merge.
```

---
**See also:** [Daily Workflow Skills](Skills-Daily-Workflow) | [Security Skills](Skills-Security)
