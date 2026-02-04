# Skill: Generate NUnit Tests

---
id: dotnet/generate-tests
name: Generate NUnit Tests
complexity: medium
estimated_time: 10-15 minutes
---

## Description

Generates NUnit test fixtures following project patterns including BaseTest inheritance, mock setup, and proper assertion grouping.

## Prerequisites

- Class to test exists
- Understanding of expected behavior

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Class to test | Yes | Provider, Service, or Controller |
| Methods to test | Yes | Public methods requiring tests |
| Test scenarios | Yes | Happy path, errors, edge cases |

## Outputs

- Test fixture class
- Mock setup
- Test methods with Arrange-Act-Assert pattern

## Execution Steps

### Step 1: Create Test File

```
tests/{YourProject}.Tests/
├── Business/Providers/
│   └── UserProviderTests.cs
├── Services/
│   └── UserServiceTests.cs
└── Controllers/V1/
    └── UserControllerTests.cs
```

### Step 2: Create Test Fixture

```csharp
using Moq;
using NUnit.Framework;
using {YourProject}.Domain.Results;
using {YourProject}.Business.Providers;
using {YourProject}.Services.Interfaces;

namespace {YourProject}.Tests.Business.Providers;

[TestFixture]
public class UserProviderTests : BaseTest
{
    private Mock<IUserService> _userServiceMock;
    private Mock<INotificationService> _notificationServiceMock;
    private Mock<ILogger<UserProvider>> _loggerMock;
    private UserProvider _sut;

    [SetUp]
    public void SetUp()
    {
        _userServiceMock = new Mock<IUserService>();
        _notificationServiceMock = new Mock<INotificationService>();
        _loggerMock = new Mock<ILogger<UserProvider>>();
        
        _sut = new UserProvider(
            _userServiceMock.Object,
            _notificationServiceMock.Object,
            _loggerMock.Object);
    }
}
```

### Step 3: Add Happy Path Tests

```csharp
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
        Assert.That(result.Value.Email, Is.EqualTo(expectedUser.Email));
    }
}

#endregion
```

### Step 4: Add Error Case Tests

```csharp
[Test]
public async Task GetUserAsync_WithNullId_ReturnsInvalidInputError()
{
    // Arrange
    string userId = null;

    // Act
    Result<UserResponse> result = await _sut.GetUserAsync(userId);

    // Assert
    using (Assert.EnterMultipleScope())
    {
        Assert.That(result.IsError, Is.True);
        Assert.That(result.Error, Is.TypeOf<InvalidInputError>());
    }
}

[Test]
public async Task GetUserAsync_WhenUserNotFound_ReturnsNotFoundError()
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
```

### Step 5: Add Edge Case Tests

```csharp
[Test]
public async Task GetUserAsync_WithEmptyId_ReturnsInvalidInputError()
{
    // Arrange
    string userId = "";

    // Act
    Result<UserResponse> result = await _sut.GetUserAsync(userId);

    // Assert
    Assert.That(result.IsError, Is.True);
}

[Test]
public async Task GetUserAsync_WithWhitespaceId_ReturnsInvalidInputError()
{
    // Arrange
    string userId = "   ";

    // Act
    Result<UserResponse> result = await _sut.GetUserAsync(userId);

    // Assert
    Assert.That(result.IsError, Is.True);
}
```

### Step 6: Add Verification Tests

```csharp
[Test]
public async Task GetUserAsync_CallsServiceWithCorrectId()
{
    // Arrange
    string userId = "user-123";
    _userServiceMock
        .Setup(x => x.GetByIdAsync(userId))
        .ReturnsAsync(Result<User>.Success(CreateTestUser(userId)));

    // Act
    await _sut.GetUserAsync(userId);

    // Assert
    _userServiceMock.Verify(x => x.GetByIdAsync(userId), Times.Once);
}
```

## Test Naming Convention

```
[MethodName]_[Scenario]_[ExpectedResult]
```

Examples:
- `GetUserAsync_WithValidId_ReturnsUser`
- `GetUserAsync_WithNullId_ReturnsInvalidInputError`
- `CreateUserAsync_WhenServiceFails_ReturnsError`

## Checklist

- [ ] Test fixture inherits from BaseTest
- [ ] SetUp method creates mocks and SUT
- [ ] Tests grouped by method using #region
- [ ] Naming follows convention
- [ ] Happy path tested
- [ ] Error cases tested
- [ ] Edge cases tested (null, empty, whitespace)
- [ ] Service calls verified
- [ ] Assert.EnterMultipleScope used for grouped assertions

## Related Skills

- [Create Provider](../create-provider/skill.md)
- [Create Endpoint](../create-endpoint/skill.md)

## Example Invocation

```
Generate tests for MigrateApisProvider:
- Class: MigrateApisProvider
- Methods: MigrateApiVersionAsync, GetMigrationStatusAsync
- Dependencies: IApiCenterService, IApiManagementService
- Scenarios:
  - Happy path migration
  - Source version not found
  - Target version already exists
  - Service failures
```
