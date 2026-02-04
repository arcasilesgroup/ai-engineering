# .NET Coding Standards

> C# coding conventions and style guidelines for .NET 8 projects.

---

## Type Explicitness (`var` Policy)

### Rule: Avoid `var` by Default

To improve code review readability and make types explicit:

```csharp
// ✅ PREFERRED: Explicit types
Result<User> userResult = await _userService.GetUserAsync(id);
List<ApiVersion> versions = new List<ApiVersion>();
string userName = user.Name;

// ✅ ACCEPTABLE: var when type is obvious on right side
var user = new User();
var versions = new List<ApiVersion>();
var dictionary = new Dictionary<string, int>();

// ❌ AVOID: var with method returns (type not obvious)
var result = await _service.ProcessAsync(input);  // What type is result?
var data = GetData();  // What does this return?
```

---

## Structure & Nesting

### Guard Clauses (Early Return)

Flatten code by validating preconditions first:

```csharp
// ✅ GOOD: Guard clauses
public async Task<Result<Order>> ProcessOrderAsync(OrderRequest request)
{
    if (request is null)
        return new InvalidInputError("Request cannot be null");
    
    if (string.IsNullOrEmpty(request.CustomerId))
        return new InvalidInputError("CustomerId is required");
    
    Result<Customer> customerResult = await _customerService.GetAsync(request.CustomerId);
    if (customerResult.IsError)
        return customerResult.Error;
    
    // Happy path continues here without nesting
    Customer customer = customerResult.Value;
    return await CreateOrderAsync(customer, request);
}

// ❌ BAD: Deep nesting
public async Task<Result<Order>> ProcessOrderAsync(OrderRequest request)
{
    if (request is not null)
    {
        if (!string.IsNullOrEmpty(request.CustomerId))
        {
            var customerResult = await _customerService.GetAsync(request.CustomerId);
            if (!customerResult.IsError)
            {
                // Deeply nested happy path
            }
        }
    }
    return new InvalidInputError("Invalid request");
}
```

### Object Initializers

Use initializers instead of line-by-line assignment:

```csharp
// ✅ GOOD: Object initializer
var response = new ApiVersionResponse
{
    Id = version.Id,
    Name = version.Name,
    Status = version.Status,
    CreatedAt = version.CreatedAt
};

// ❌ BAD: Line-by-line assignment
var response = new ApiVersionResponse();
response.Id = version.Id;
response.Name = version.Name;
response.Status = version.Status;
response.CreatedAt = version.CreatedAt;
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `UserService`, `ApiVersionProvider` |
| Interfaces | I-prefix | `IUserService`, `IApiVersionProvider` |
| Methods | PascalCase | `GetUserAsync`, `ProcessOrder` |
| Properties | PascalCase | `UserName`, `IsActive` |
| Local variables | camelCase | `userId`, `orderCount` |
| Parameters | camelCase | `string userId`, `int pageSize` |
| Private fields | _camelCase | `_userRepository`, `_logger` |
| Constants | PascalCase | `DefaultPageSize`, `MaxRetries` |

### Async Suffix

Always use `Async` suffix for async methods:

```csharp
// ✅ CORRECT
public async Task<User> GetUserAsync(string id)
public async Task ProcessOrderAsync(Order order)

// ❌ INCORRECT
public async Task<User> GetUser(string id)
```

---

## Null Handling

### Nullable Reference Types

Enable and respect nullable reference types:

```csharp
// ✅ GOOD: Explicit nullability
public string? GetOptionalValue()
public void Process(string requiredValue, string? optionalValue = null)

// Check before use
if (optionalValue is not null)
{
    // Use optionalValue
}
```

### Null Checks

```csharp
// ✅ PREFERRED: Pattern matching
if (user is null)
    return new NotFoundError("User not found");

if (user is not null)
    Process(user);

// ✅ ACCEPTABLE: Traditional null check
if (user == null)
    return new NotFoundError("User not found");
```

---

## Collections

### Prefer Immutable Returns

```csharp
// ✅ GOOD: Return read-only collections
public IReadOnlyList<User> GetUsers() => _users.AsReadOnly();
public IReadOnlyDictionary<string, Config> GetConfigs() => _configs;

// ❌ AVOID: Exposing mutable collections
public List<User> GetUsers() => _users;  // Caller can modify internal state
```

### LINQ Best Practices

```csharp
// ✅ GOOD: Appropriate LINQ usage
List<string> activeNames = users
    .Where(u => u.IsActive)
    .Select(u => u.Name)
    .ToList();

// ❌ AVOID: Multiple enumerations
IEnumerable<User> activeUsers = users.Where(u => u.IsActive);
int count = activeUsers.Count();      // First enumeration
var first = activeUsers.FirstOrDefault();  // Second enumeration
```

---

## Documentation

### XML Documentation for Public APIs

```csharp
/// <summary>
/// Retrieves a user by their unique identifier.
/// </summary>
/// <param name="userId">The unique identifier of the user.</param>
/// <returns>
/// A Result containing the User if found, or a NotFoundError if the user doesn't exist.
/// </returns>
/// <example>
/// <code>
/// Result&lt;User&gt; result = await _provider.GetUserAsync("user-123");
/// if (result.IsError)
///     return result.Error;
/// User user = result.Value;
/// </code>
/// </example>
public async Task<Result<User>> GetUserAsync(string userId)
```

---

## File Organization

### Class File Structure

```csharp
namespace Company.Project.Feature;

public class UserService : IUserService
{
    // 1. Constants
    private const int MaxRetries = 3;
    
    // 2. Static fields
    private static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(30);
    
    // 3. Instance fields
    private readonly IUserRepository _repository;
    private readonly ILogger<UserService> _logger;
    
    // 4. Constructor(s)
    public UserService(IUserRepository repository, ILogger<UserService> logger)
    {
        _repository = repository;
        _logger = logger;
    }
    
    // 5. Public properties
    public int RetryCount { get; private set; }
    
    // 6. Public methods
    public async Task<Result<User>> GetUserAsync(string id) { }
    
    // 7. Private/protected methods
    private void ValidateInput(string input) { }
}
```

---

## Common Pitfalls

### ❌ Accessing Result.Value Without Check

```csharp
// ❌ DANGEROUS: Throws InvalidOperationException
Result<User> result = await GetUserAsync(id);
User user = result.Value;  // What if IsError is true?

// ✅ SAFE: Always check first
Result<User> result = await GetUserAsync(id);
if (result.IsError)
    return result.Error;
User user = result.Value;
```

### ❌ Using Exceptions for Flow Control

```csharp
// ❌ BAD: Exception for expected scenario
try
{
    var user = await _repository.GetByIdAsync(id);
}
catch (UserNotFoundException)
{
    return new NotFoundError("User not found");
}

// ✅ GOOD: Result pattern
Result<User> userResult = await _repository.GetByIdAsync(id);
if (userResult.IsError)
    return userResult.Error;
```
