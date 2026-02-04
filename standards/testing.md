# Testing Standards

> Cross-stack testing philosophy, patterns, and anti-patterns. Applies to all technology stacks.

---

## 1. Testing Philosophy

- **Tests are documentation**: A well-named test describes expected behavior better than comments.
- **Test behavior, not implementation**: Tests should survive refactoring if behavior doesn't change.
- **Fast feedback**: Unit tests run in seconds, not minutes. Integration tests are separate.
- **Deterministic**: Tests produce the same result every time. No flaky tests.
- **Independent**: Tests don't depend on each other or execution order.

---

## 2. Test Pyramid

```
         ╱  E2E  ╲          Few, slow, expensive
        ╱─────────╲
       ╱ Integration╲       Some, medium speed
      ╱───────────────╲
     ╱   Unit Tests    ╲    Many, fast, cheap
    ╱───────────────────╲
```

| Level | Scope | Speed | Count |
|-------|-------|-------|-------|
| Unit | Single function/method | < 50ms | Many (80%) |
| Integration | Multiple components | < 5s | Some (15%) |
| E2E | Full system | < 30s | Few (5%) |

---

## 3. Naming Convention

### Pattern: `MethodName_Scenario_ExpectedResult`

```csharp
// .NET
public void GetUserAsync_WhenUserExists_ReturnsUser()
public void GetUserAsync_WhenUserNotFound_ReturnsNotFoundError()
public void CreateOrder_WithInvalidQuantity_ThrowsValidationException()
```

```typescript
// TypeScript
describe('UserService', () => {
  it('returns user when user exists', () => {})
  it('returns null when user not found', () => {})
})
```

```python
# Python
def test_get_user_when_user_exists_returns_user():
def test_get_user_when_not_found_returns_none():
```

### Rules

- Test name must describe the scenario, not the implementation.
- Use `When`/`With`/`Given` to describe the condition.
- Use `Should`/`Returns`/`Throws` to describe the expected outcome.
- Never use generic names like `test1`, `testHappyPath`, `testMethod`.

---

## 4. Test Structure: Arrange-Act-Assert

Every test follows the AAA pattern:

```csharp
[Test]
public void CalculateTotal_WithDiscount_ReturnsDiscountedPrice()
{
    // Arrange
    Order order = new Order { Items = [new Item { Price = 100 }] };
    decimal discountPercent = 10;

    // Act
    decimal total = _calculator.CalculateTotal(order, discountPercent);

    // Assert
    Assert.That(total, Is.EqualTo(90));
}
```

### Rules

- **One logical assertion per test** (multiple physical assertions allowed if testing one concept).
- **No logic in tests**: No `if`, `for`, `while`, `switch` in test code.
- **No shared mutable state**: Each test creates its own data.

---

## 5. What to Test

### Always Test

- Happy path (expected successful flow)
- Error/failure paths (what happens when things go wrong)
- Edge cases (empty collections, null inputs, boundary values)
- Business rules (the domain logic that matters)
- Security boundaries (authorization checks, input validation)

### Never Test

- Framework code (e.g., ASP.NET routing, React rendering engine)
- Simple property getters/setters with no logic
- Third-party library internals
- Private methods directly (test through public API)
- Implementation details (internal data structures, private state)

---

## 6. Mocking Guidelines

### When to Mock

- External services (HTTP clients, databases, file system)
- Time-dependent code (use injectable clock/time provider)
- Non-deterministic code (random, GUIDs)
- Slow dependencies (network calls, disk I/O)

### When NOT to Mock

- Simple value objects / DTOs
- Pure functions with no side effects
- The system under test itself
- Data transformations

### Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Mocking everything | Tests verify mock setup, not behavior | Only mock external boundaries |
| Mock returning mocks | Tight coupling to implementation | Restructure code or use fakes |
| Verifying internal calls | Breaks on refactoring | Assert on outputs, not interactions |
| Complex mock setup (> 10 lines) | Test is testing too much | Break into smaller units |

---

## 7. Test Data

### Rules

- **No hardcoded dates**: Use `DateTime.UtcNow` or `DateTimeOffset.UtcNow` with relative calculations.
- **No magic numbers**: Use named constants or builder patterns.
- **Minimal data**: Only include fields relevant to the test scenario.
- **Builder pattern**: Use test data builders for complex objects.

```csharp
// Good: relative date
DateTime expiryDate = DateTime.UtcNow.AddDays(30);

// Bad: hardcoded date
DateTime expiryDate = new DateTime(2024, 12, 31);
```

```csharp
// Good: builder pattern
Order order = new OrderBuilder()
    .WithItem("Widget", price: 10.00m)
    .WithDiscount(15)
    .Build();

// Bad: constructor with many parameters
Order order = new Order("Widget", 10.00m, 15, null, true, "USD", DateTime.Now);
```

---

## 8. Test Organization

### File Structure

| Stack | Source | Test |
|-------|--------|------|
| .NET | `src/Project/UserService.cs` | `tests/Project.Tests/UserServiceTests.cs` |
| TypeScript | `src/services/user.ts` | `src/services/user.test.ts` |
| Python | `src/services/user.py` | `tests/test_user.py` |

### Grouping

- Group tests by the class/module under test.
- Within a group, order: happy path → error paths → edge cases.
- Use `[TestFixture]` (.NET), `describe` blocks (TS), or test classes (Python) for grouping.

---

## 9. Assertion Best Practices

### .NET (NUnit)

```csharp
// Use Assert.EnterMultipleScope for grouped assertions
using (Assert.EnterMultipleScope())
{
    Assert.That(result.Name, Is.EqualTo("John"));
    Assert.That(result.Age, Is.EqualTo(30));
    Assert.That(result.IsActive, Is.True);
}
```

### TypeScript (Vitest/Jest)

```typescript
expect(result).toEqual({ name: 'John', age: 30 });
expect(array).toHaveLength(3);
expect(fn).toThrow(ValidationError);
expect(element).toBeInTheDocument();
```

### Python (pytest)

```python
assert result.name == "John"
assert len(items) == 3

with pytest.raises(ValidationError, match="invalid email"):
    validate_email("not-an-email")
```

---

## 10. Flaky Test Policy

- **Definition**: A test that passes and fails without code changes.
- **Response**: Immediately quarantine (skip with `[Ignore("Flaky: #issue")]`) and create an issue.
- **Root Causes**: Timing dependencies, shared state, external service calls, date/time hardcoding.
- **Prevention**: No `Thread.Sleep`, no shared mutable state, mock external calls, use relative dates.
