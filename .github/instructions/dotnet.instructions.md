---
applyTo: "**/*.cs"
---

# .NET Coding Standards for Copilot

These instructions apply to all C# files in this project. Follow these standards when generating or modifying code.

## Type Explicitness (var Policy)

- Use explicit types by default for method return assignments
- `var` is acceptable only when the type is obvious from the right-hand side (e.g., `var user = new User();`)
- Never use `var` with method returns where the type is not obvious

```csharp
// CORRECT
Result<User> userResult = await _userService.GetUserAsync(id);
List<ApiVersion> versions = new List<ApiVersion>();

// ACCEPTABLE (type obvious from right side)
var user = new User();
var dictionary = new Dictionary<string, int>();

// WRONG
var result = await _service.ProcessAsync(input);
```

## Result Pattern

All operations that can fail return `Result<T>`. Never use exceptions for flow control.

```csharp
// ALWAYS check IsError before accessing Value
Result<User> result = await _service.GetUserAsync(id);
if (result.IsError)
    return result.Error;
User user = result.Value;
```

- Return `Result<T>` for operations with a return value
- Return `Result` for void operations
- Use implicit conversions: `return user;` or `return new NotFoundError("...");`
- In controllers, use `result.ToActionResult(_errorMapper, response => Ok(response));`

## Error Mapping

Every domain error type must have a registered mapping. Missing mappings cause runtime exceptions.

| Error Type                 | HTTP Status | Response Type           |
|---------------------------|-------------|------------------------|
| `NotFoundError`           | 404         | `NotFoundResponse`     |
| `InvalidInputError`       | 400         | `BadRequestResponse`   |
| `InvalidInputDetailedError` | 400       | `BadRequestResponse`   |
| `UnauthorizedError`       | 401         | `UnauthorizedResponse` |
| `ForbiddenError`          | 403         | `ForbiddenResponse`    |
| `ConflictError`           | 409         | `ConflictResponse`     |
| `BaseError` (fallback)    | 500         | `InternalErrorResponse`|

When creating a new error type:
1. Create the domain error class extending `BaseError`
2. Create the response type (if needed)
3. Register the mapping in startup configuration

## Guard Clauses

Use early returns to keep code flat. Never deeply nest conditionals.

```csharp
public async Task<Result<Order>> ProcessOrderAsync(OrderRequest request)
{
    if (request is null)
        return new InvalidInputError("Request cannot be null");

    if (string.IsNullOrEmpty(request.CustomerId))
        return new InvalidInputError("CustomerId is required");

    Result<Customer> customerResult = await _customerService.GetAsync(request.CustomerId);
    if (customerResult.IsError)
        return customerResult.Error;

    Customer customer = customerResult.Value;
    return await CreateOrderAsync(customer, request);
}
```

## Naming Conventions

| Element         | Convention   | Example                          |
|----------------|-------------|----------------------------------|
| Classes         | PascalCase   | `UserService`, `ApiVersionProvider` |
| Interfaces      | I-prefix     | `IUserService`, `IApiVersionProvider` |
| Methods         | PascalCase   | `GetUserAsync`, `ProcessOrder`   |
| Properties      | PascalCase   | `UserName`, `IsActive`           |
| Local variables | camelCase    | `userId`, `orderCount`           |
| Parameters      | camelCase    | `string userId`, `int pageSize`  |
| Private fields  | _camelCase   | `_userRepository`, `_logger`     |
| Constants       | PascalCase   | `DefaultPageSize`, `MaxRetries`  |

## Async Patterns

- Always use `Async` suffix for async methods
- Use `async/await` throughout, never `.Result` or `.Wait()`
- Return `Task<Result<T>>` for async operations that can fail

```csharp
public async Task<Result<User>> GetUserAsync(string id)
public async Task<Result> DeleteUserAsync(string id)
```

## Null Handling

- Enable nullable reference types
- Use pattern matching for null checks: `if (user is null)`, `if (user is not null)`
- Mark nullable parameters/returns with `?`

## File Structure

Organize class members in this order:
1. Constants
2. Static fields
3. Instance fields (private readonly)
4. Constructor(s)
5. Public properties
6. Public methods
7. Private/protected methods

## Collections

- Return `IReadOnlyList<T>` or `IReadOnlyDictionary<K,V>` from public methods
- Avoid multiple enumerations of `IEnumerable<T>`
- Use object initializers instead of line-by-line assignment

## NUnit Testing

- Test framework: NUnit 3.x with Moq for mocking
- Naming: `MethodName_Scenario_ExpectedResult`
- Use `[TestFixture]` on test classes, `[Test]` on methods
- Use `Assert.EnterMultipleScope()` for grouped assertions
- Use `[SetUp]` for per-test initialization
- Follow Arrange/Act/Assert pattern
- Name the system under test `_sut`

```csharp
[TestFixture]
public class UserProviderTests : BaseTest
{
    private Mock<IUserService> _userServiceMock;
    private UserProvider _sut;

    [SetUp]
    public void SetUp()
    {
        _userServiceMock = new Mock<IUserService>();
        _sut = new UserProvider(_userServiceMock.Object);
    }

    [Test]
    public async Task GetUserAsync_WithValidId_ReturnsUser()
    {
        // Arrange
        User expectedUser = CreateTestUser("user-123");
        _userServiceMock
            .Setup(x => x.GetByIdAsync("user-123"))
            .ReturnsAsync(Result<User>.Success(expectedUser));

        // Act
        Result<UserResponse> result = await _sut.GetUserAsync("user-123");

        // Assert
        using (Assert.EnterMultipleScope())
        {
            Assert.That(result.IsError, Is.False);
            Assert.That(result.Value.Id, Is.EqualTo("user-123"));
        }
    }
}
```

## XML Documentation

Provide XML documentation for all public APIs:

```csharp
/// <summary>
/// Retrieves a user by their unique identifier.
/// </summary>
/// <param name="userId">The unique identifier of the user.</param>
/// <returns>A Result containing the User if found, or a NotFoundError.</returns>
public async Task<Result<User>> GetUserAsync(string userId)
```

## Security

- Never hardcode secrets or connection strings
- Validate all inputs at controller/function boundaries
- Use structured logging: `_logger.LogInformation("Processed {Count} items", count);`
- Never log sensitive data (passwords, tokens, PII)
- Do not expose stack traces in error responses
