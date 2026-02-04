# .NET Testing Standards

> NUnit testing patterns and conventions for .NET 8 projects.

---

## Test Framework

- **Framework:** NUnit 3.x
- **Assertions:** NUnit Assert or FluentAssertions
- **Mocking:** Moq
- **Coverage:** Coverlet

---

## Test Project Structure

```
tests/
└── {YourProject}.Tests/
    ├── Business/
    │   └── Providers/
    │       └── UserProviderTests.cs
    ├── Services/
    │   └── UserServiceTests.cs
    ├── Controllers/
    │   └── V1/
    │       └── UserControllerTests.cs
    ├── Fixtures/
    │   └── BaseTest.cs
    └── TestData/
        └── UserTestData.cs
```

---

## Base Test Pattern

Use a shared base test class for common setup:

```csharp
[TestFixture]
public abstract class BaseTest
{
    protected IConfiguration Configuration { get; private set; }
    
    [OneTimeSetUp]
    public void OneTimeSetUp()
    {
        Configuration = new ConfigurationBuilder()
            .AddJsonFile("test.settings.json", optional: true)
            .AddEnvironmentVariables()
            .Build();
    }
    
    // Shared test data builders
    protected static User CreateTestUser(string id = "test-user-1", string name = "Test User")
    {
        return new User
        {
            Id = id,
            Name = name,
            Email = $"{id}@test.com",
            CreatedAt = DateTime.UtcNow
        };
    }
    
    protected static ApiVersion CreateTestApiVersion(
        string id = "v1",
        string status = "active",
        int daysFromNow = 0)
    {
        return new ApiVersion
        {
            Id = id,
            Status = status,
            CreatedAt = DateTime.UtcNow.AddDays(daysFromNow)
        };
    }
}
```

---

## Test Class Structure

```csharp
[TestFixture]
public class UserProviderTests : BaseTest
{
    // 1. Private fields for mocks and SUT
    private Mock<IUserService> _userServiceMock;
    private Mock<ILogger<UserProvider>> _loggerMock;
    private UserProvider _sut;  // System Under Test
    
    // 2. SetUp - runs before each test
    [SetUp]
    public void SetUp()
    {
        _userServiceMock = new Mock<IUserService>();
        _loggerMock = new Mock<ILogger<UserProvider>>();
        _sut = new UserProvider(_userServiceMock.Object, _loggerMock.Object);
    }
    
    // 3. Tests grouped by method
    #region GetUserAsync
    
    [Test]
    public async Task GetUserAsync_WithValidId_ReturnsUser()
    {
        // Arrange
        string userId = "user-123";
        User expectedUser = CreateTestUser(userId);
        _userServiceMock
            .Setup(x => x.GetByIdAsync(userId))
            .ReturnsAsync(Result<User>.Success(expectedUser));
        
        // Act
        Result<UserResponse> result = await _sut.GetUserAsync(userId);
        
        // Assert
        using (Assert.EnterMultipleScope())
        {
            Assert.That(result.IsError, Is.False);
            Assert.That(result.Value.Id, Is.EqualTo(userId));
            Assert.That(result.Value.Name, Is.EqualTo(expectedUser.Name));
        }
    }
    
    [Test]
    public async Task GetUserAsync_WithInvalidId_ReturnsNotFoundError()
    {
        // Arrange
        string userId = "nonexistent";
        _userServiceMock
            .Setup(x => x.GetByIdAsync(userId))
            .ReturnsAsync(new NotFoundError($"User {userId} not found"));
        
        // Act
        Result<UserResponse> result = await _sut.GetUserAsync(userId);
        
        // Assert
        using (Assert.EnterMultipleScope())
        {
            Assert.That(result.IsError, Is.True);
            Assert.That(result.Error, Is.TypeOf<NotFoundError>());
        }
    }
    
    #endregion
}
```

---

## Naming Conventions

### Test Method Names

```
[MethodName]_[Scenario]_[ExpectedResult]
```

**Examples:**
```csharp
GetUserAsync_WithValidId_ReturnsUser()
GetUserAsync_WithNullId_ReturnsInvalidInputError()
ProcessOrder_WhenInventoryInsufficient_ReturnsConflictError()
CalculateDiscount_WithPremiumCustomer_AppliesPercentageDiscount()
```

### Test Categories

Use `[Category]` for test organization:

```csharp
[Test]
[Category("Integration")]
public async Task DatabaseConnection_WhenConfigured_Succeeds()

[Test]
[Category("Slow")]
public async Task BulkImport_WithLargeDataset_CompletesWithinTimeout()
```

---

## Assertion Patterns

### Using Assert.EnterMultipleScope()

Prefer `EnterMultipleScope()` over `Assert.Multiple()` for grouped assertions:

```csharp
// ✅ PREFERRED: EnterMultipleScope
using (Assert.EnterMultipleScope())
{
    Assert.That(result.IsError, Is.False);
    Assert.That(result.Value.Id, Is.EqualTo(expectedId));
    Assert.That(result.Value.Items, Has.Count.EqualTo(3));
}

// ✅ ALSO ACCEPTABLE: Assert.Multiple
Assert.Multiple(() =>
{
    Assert.That(result.IsError, Is.False);
    Assert.That(result.Value.Id, Is.EqualTo(expectedId));
});

// ❌ AVOID: Separate assertions (fails on first)
Assert.That(result.IsError, Is.False);
Assert.That(result.Value.Id, Is.EqualTo(expectedId));
Assert.That(result.Value.Items, Has.Count.EqualTo(3));
```

### Common Assertions

```csharp
// Equality
Assert.That(actual, Is.EqualTo(expected));
Assert.That(actual, Is.Not.EqualTo(other));

// Null checks
Assert.That(value, Is.Null);
Assert.That(value, Is.Not.Null);

// Type checks
Assert.That(error, Is.TypeOf<NotFoundError>());
Assert.That(result, Is.InstanceOf<BaseError>());

// Collections
Assert.That(list, Is.Empty);
Assert.That(list, Is.Not.Empty);
Assert.That(list, Has.Count.EqualTo(5));
Assert.That(list, Contains.Item(expected));
Assert.That(list, Has.Exactly(2).Matches<User>(u => u.IsActive));

// Strings
Assert.That(text, Does.StartWith("Error:"));
Assert.That(text, Does.Contain("not found"));
Assert.That(text, Is.EqualTo("expected").IgnoreCase);

// Boolean
Assert.That(result.IsError, Is.True);
Assert.That(result.IsError, Is.False);

// Exceptions
Assert.ThrowsAsync<ArgumentNullException>(async () => await _sut.ProcessAsync(null));
```

---

## Mocking Patterns

### Setup Patterns

```csharp
// Return success
_serviceMock
    .Setup(x => x.GetAsync(It.IsAny<string>()))
    .ReturnsAsync(Result<User>.Success(testUser));

// Return error
_serviceMock
    .Setup(x => x.GetAsync("invalid"))
    .ReturnsAsync(new NotFoundError("Not found"));

// Throw exception (for testing error handling)
_serviceMock
    .Setup(x => x.GetAsync("error"))
    .ThrowsAsync(new HttpRequestException("Network error"));

// Conditional returns
_serviceMock
    .Setup(x => x.GetAsync(It.Is<string>(id => id.StartsWith("valid"))))
    .ReturnsAsync(Result<User>.Success(testUser));
```

### Verification Patterns

```csharp
// Verify called once
_serviceMock.Verify(x => x.GetAsync(userId), Times.Once);

// Verify never called
_serviceMock.Verify(x => x.DeleteAsync(It.IsAny<string>()), Times.Never);

// Verify called with specific argument
_serviceMock.Verify(x => x.SaveAsync(It.Is<User>(u => u.Id == expectedId)), Times.Once);
```

---

## Test Data Patterns

### Dynamic Dates for Time-Dependent Tests

```csharp
// ✅ GOOD: Dynamic relative dates
[Test]
public void IsExpired_WhenPastDeadline_ReturnsTrue()
{
    // Arrange
    var item = new Subscription
    {
        ExpiresAt = DateTime.UtcNow.AddDays(-1)  // Yesterday
    };
    
    // Act & Assert
    Assert.That(item.IsExpired, Is.True);
}

// ❌ BAD: Hardcoded dates (will break over time)
var item = new Subscription
{
    ExpiresAt = new DateTime(2024, 12, 31)  // Will behave differently after this date
};
```

### Test Data Builders

```csharp
public static class TestData
{
    public static ApiDefinitionList ApiDefinitions() => new ApiDefinitionList
    {
        Value = new List<ApiDefinition>
        {
            new() { Id = "api-1", Name = "Customer API", Version = "v1" },
            new() { Id = "api-2", Name = "Orders API", Version = "v2" }
        }
    };
    
    public static ApiVersionsWithProductionListModel ApiVersionsWithProduction() => new()
    {
        Versions = new List<ApiVersionModel>
        {
            new() { Id = "v1", Status = "production", CreatedAt = DateTime.UtcNow.AddDays(-90) },
            new() { Id = "v2", Status = "preview", CreatedAt = DateTime.UtcNow.AddDays(-30) }
        }
    };
}
```

---

## Running Tests

```powershell
# Run all tests
dotnet test

# Run with verbosity
dotnet test --verbosity normal

# Run specific category
dotnet test --filter "Category=Integration"

# Run specific test class
dotnet test --filter "FullyQualifiedName~UserProviderTests"

# With coverage
dotnet test --collect:"XPlat Code Coverage"
```
