# .NET Standards

> Consolidated .NET 8 standards: coding conventions, patterns, ASP.NET Core, Azure Functions, and testing.

---

## 1. Coding Conventions

### Type Explicitness (`var` Policy)

Avoid `var` by default to improve code review readability:

```csharp
// PREFERRED: Explicit types
Result<User> userResult = await _userService.GetUserAsync(id);
List<ApiVersion> versions = new List<ApiVersion>();
string userName = user.Name;

// ACCEPTABLE: var when type is obvious on right side
var user = new User();
var versions = new List<ApiVersion>();
var dictionary = new Dictionary<string, int>();

// AVOID: var with method returns (type not obvious)
var result = await _service.ProcessAsync(input);  // What type is result?
var data = GetData();  // What does this return?
```

### Guard Clauses (Early Return)

Flatten code by validating preconditions first:

```csharp
// GOOD: Guard clauses
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

### Object Initializers

```csharp
// GOOD: Object initializer
var response = new ApiVersionResponse
{
    Id = version.Id,
    Name = version.Name,
    Status = version.Status,
    CreatedAt = version.CreatedAt
};
```

### Naming Conventions

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
// CORRECT
public async Task<User> GetUserAsync(string id)
public async Task ProcessOrderAsync(Order order)

// INCORRECT
public async Task<User> GetUser(string id)
```

### Nullable Reference Types

Enable and respect nullable reference types:

```csharp
public string? GetOptionalValue()
public void Process(string requiredValue, string? optionalValue = null)

if (optionalValue is not null)
{
    // Use optionalValue
}
```

### Null Checks

```csharp
// PREFERRED: Pattern matching
if (user is null)
    return new NotFoundError("User not found");

if (user is not null)
    Process(user);
```

### Collections

```csharp
// Return read-only collections
public IReadOnlyList<User> GetUsers() => _users.AsReadOnly();
public IReadOnlyDictionary<string, Config> GetConfigs() => _configs;

// LINQ: avoid multiple enumerations
List<string> activeNames = users
    .Where(u => u.IsActive)
    .Select(u => u.Name)
    .ToList();
```

### File Organization (Class Structure Order)

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

### XML Documentation

```csharp
/// <summary>
/// Retrieves a user by their unique identifier.
/// </summary>
/// <param name="userId">The unique identifier of the user.</param>
/// <returns>
/// A Result containing the User if found, or a NotFoundError if the user doesn't exist.
/// </returns>
public async Task<Result<User>> GetUserAsync(string userId)
```

---

## 2. Result Pattern

Railway-oriented programming for explicit error handling without exceptions.

### Core Types

```csharp
Result<T>  // For operations with a return value
Result     // For operations without a return value
```

### Basic Usage

```csharp
// Returning success
public Result<User> GetUser(string id)
{
    User user = _repository.Find(id);
    return user;  // Implicit conversion to Result<User>.Success(user)
}

// Returning errors
public Result<User> GetUser(string id)
{
    if (string.IsNullOrEmpty(id))
        return new InvalidInputError("User ID is required");

    User? user = _repository.Find(id);
    if (user is null)
        return new NotFoundError($"User {id} not found");

    return user;
}
```

### CRITICAL: Always Check IsError Before Accessing Value

```csharp
// DANGEROUS: Will throw InvalidOperationException if IsError is true
Result<User> result = await GetUserAsync(id);
User user = result.Value;  // NEVER DO THIS

// SAFE: Always check first
Result<User> result = await GetUserAsync(id);
if (result.IsError)
    return result.Error;
User user = result.Value;  // Safe to access after check
```

### Early Return Pattern

```csharp
public async Task<Result<OrderResponse>> ProcessOrderAsync(string orderId, string customerId)
{
    if (string.IsNullOrEmpty(orderId))
        return new InvalidInputError("Order ID is required");

    Result<Customer> customerResult = await _customerService.GetAsync(customerId);
    if (customerResult.IsError)
        return customerResult.Error;

    Result<Order> orderResult = await _orderService.GetAsync(orderId);
    if (orderResult.IsError)
        return orderResult.Error;

    Customer customer = customerResult.Value;
    Order order = orderResult.Value;

    if (!order.BelongsTo(customer))
        return new ForbiddenError("Order does not belong to customer");

    OrderResponse response = CreateResponse(order, customer);
    return response;
}
```

### Domain Error Types

| Error Type | HTTP Status | Use Case |
|------------|-------------|----------|
| `NotFoundError` | 404 | Resource doesn't exist |
| `InvalidInputError` | 400 | Simple validation failure |
| `InvalidInputDetailedError` | 400 | Validation with field details |
| `UnauthorizedError` | 401 | Authentication required |
| `ForbiddenError` | 403 | Insufficient permissions |
| `ConflictError` | 409 | State conflict |
| `InternalError` | 500 | Unexpected failures |

```csharp
new NotFoundError("User not found");
new InvalidInputError("Invalid email format");
new InvalidInputDetailedError("Validation failed", new[]
{
    new ValidationError("Email", "Invalid format"),
    new ValidationError("Age", "Must be positive")
});
new InternalError("Database operation failed", exception);
```

### Implicit Conversions

```csharp
public Result<User> GetUser() => new User();              // Value to Result<T>
public Result<User> GetUser() => new NotFoundError("...");  // Error to Result<T>

Result<Customer> customerResult = await GetCustomerAsync();
if (customerResult.IsError)
    return customerResult.Error;  // Returns Result<Order> with same error
```

### Method Chaining (Bind / Map)

```csharp
// Map: Transform value without additional error handling
Result<UserDto> dtoResult = userResult.Map(user => new UserDto(user));

// Bind: Chain operations that can fail
Result<Order> orderResult = await customerResult
    .Bind(customer => GetPrimaryOrderAsync(customer));
```

**Bind Lambda Parameter Rule** -- always declare the lambda parameter, even if unused:

```csharp
// CORRECT: Parameter declared
result.Bind(version => GetNextStepAsync());

// WRONG: Compiler cannot infer generic types
result.Bind(_ => GetNextStepAsync());
```

### Controller Integration with ToActionResult

```csharp
[HttpGet("{id}")]
public async Task<IActionResult> GetUser(string id)
{
    Result<UserResponse> result = await _provider.GetUserAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}

[HttpDelete("{id}")]
public async Task<IActionResult> DeleteUser(string id)
{
    Result result = await _provider.DeleteUserAsync(id);
    return result.ToActionResult(_errorMapper, () => NoContent());
}
```

### Anti-Patterns

```csharp
// BAD: Try/catch for flow control
try { var user = await _service.GetUserAsync(id); return Ok(user); }
catch (NotFoundException ex) { return NotFound(ex.Message); }

// GOOD: Result pattern
Result<User> result = await _service.GetUserAsync(id);
return result.ToActionResult(_errorMapper, user => Ok(user));

// BAD: Value accessed before check
var user = result.Value;
if (result.IsError) return result.Error;

// GOOD: Check first
if (result.IsError) return result.Error;
var user = result.Value;

// BAD: Deep nesting
if (!customerResult.IsError) { if (!orderResult.IsError) { /* ... */ } }

// GOOD: Early returns
if (customerResult.IsError) return customerResult.Error;
if (orderResult.IsError) return orderResult.Error;
```

---

## 3. Error Mapping

Centralized conversion of domain errors to HTTP responses.

### Configuration (API Startup.cs)

```csharp
services.AddErrorMappings(mappings =>
{
    mappings.Map<NotFoundError>()
        .To<NotFoundResponse>(StatusCodes.Status404NotFound);
    mappings.Map<InvalidInputError>()
        .To<BadRequestResponse>(StatusCodes.Status400BadRequest);
    mappings.Map<InvalidInputDetailedError>()
        .To<BadRequestResponse>(StatusCodes.Status400BadRequest);
    mappings.Map<UnauthorizedError>()
        .To<UnauthorizedResponse>(StatusCodes.Status401Unauthorized);
    mappings.Map<ForbiddenError>()
        .To<ForbiddenResponse>(StatusCodes.Status403Forbidden);
    mappings.Map<ConflictError>()
        .To<ConflictResponse>(StatusCodes.Status409Conflict);
    // Fallback for unmapped errors
    mappings.Map<BaseError>()
        .To<InternalErrorResponse>(StatusCodes.Status500InternalServerError);
});
```

### Configuration (Functions)

```csharp
public static IServiceCollection AddErrorMappings(this IServiceCollection services)
{
    services.AddErrorMappings(mappings =>
    {
        mappings.Map<NotFoundError>()
            .To<NotFoundResponse>(StatusCodes.Status404NotFound)
            .AfterMap((error, response, context) =>
            {
                context.HttpContext?.Items.Add(
                    RequestLoggerFilter.ResponseBodyType,
                    typeof(NotFoundResponse));
            });
        // Additional mappings...
    });
    return services;
}
```

### Standard Mapping Table

| Domain Error | HTTP Status | Response Type |
|--------------|-------------|---------------|
| `NotFoundError` | 404 | `NotFoundResponse` |
| `InvalidInputError` | 400 | `BadRequestResponse` |
| `InvalidInputDetailedError` | 400 | `BadRequestResponse` |
| `UnauthorizedError` | 401 | `UnauthorizedResponse` |
| `ForbiddenError` | 403 | `ForbiddenResponse` |
| `ConflictError` | 409 | `ConflictResponse` |
| `BaseError` (fallback) | 500 | `InternalErrorResponse` |

### Usage in Controllers

```csharp
// With ToActionResult extension
[HttpGet("{id}")]
public async Task<IActionResult> GetUser(string id)
{
    Result<UserResponse> result = await _provider.GetUserAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}

// Manual mapping
[HttpGet("{id}")]
public async Task<IActionResult> GetUser(string id)
{
    Result<UserResponse> result = await _provider.GetUserAsync(id);
    if (result.IsError)
    {
        ErrorMappingResult mapping = _errorMapper.Map(result.Error);
        return StatusCode(mapping.StatusCode, mapping.Response);
    }
    return Ok(result.Value);
}
```

### Response Format (RFC 7807 Problem Details)

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.4",
  "title": "Not Found",
  "status": 404,
  "detail": "User with ID 'user-123' was not found.",
  "traceId": "00-abc123def456-789xyz-00"
}
```

Validation errors with field details:

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "Bad Request",
  "status": 400,
  "detail": "One or more validation errors occurred.",
  "errors": {
    "email": ["Invalid email format"],
    "age": ["Must be a positive number"]
  },
  "traceId": "00-abc123def456-789xyz-00"
}
```

### Adding New Error Types (3 Steps)

**Step 1: Create domain error:**

```csharp
public class RateLimitExceededError : BaseError
{
    public int RetryAfterSeconds { get; }
    public RateLimitExceededError(string message, int retryAfterSeconds)
        : base(message)
    {
        RetryAfterSeconds = retryAfterSeconds;
    }
}
```

**Step 2: Create response type:**

```csharp
public class RateLimitResponse
{
    public string Message { get; init; }
    public int RetryAfterSeconds { get; init; }
}
```

**Step 3: Register mapping:**

```csharp
mappings.Map<RateLimitExceededError>()
    .To<RateLimitResponse>(StatusCodes.Status429TooManyRequests)
    .AfterMap((error, response, context) =>
    {
        context.HttpContext?.Response.Headers.Add(
            "Retry-After",
            error.RetryAfterSeconds.ToString());
    });
```

### AfterMap Hook

Use for post-mapping operations (headers, telemetry, logging):

```csharp
mappings.Map<NotFoundError>()
    .To<NotFoundResponse>(StatusCodes.Status404NotFound)
    .AfterMap((error, response, context) =>
    {
        context.HttpContext?.Items.Add("ErrorType", nameof(NotFoundError));
        var logger = context.HttpContext?.RequestServices
            .GetService<ILogger<ErrorMapper>>();
        logger?.LogWarning("Resource not found: {Message}", error.Message);
    });
```

### Testing Error Mappings

```csharp
[Test]
public void Map_NotFoundError_Returns404()
{
    var error = new NotFoundError("User not found");
    IErrorMapper mapper = CreateMapper();
    ErrorMappingResult result = mapper.Map(error);

    using (Assert.EnterMultipleScope())
    {
        Assert.That(result.StatusCode, Is.EqualTo(404));
        Assert.That(result.Response, Is.TypeOf<NotFoundResponse>());
    }
}
```

---

## 4. Dependency Injection

### Registration Pattern

**Business dependencies:**

```csharp
public static class DependencyInjectionExtensions
{
    public static IServiceCollection AddBusinessDependencies(this IServiceCollection services)
    {
        services.AddScoped<IUserProvider, UserProvider>();
        services.AddScoped<IOrderProvider, OrderProvider>();
        services.AddScoped<IProductProvider, ProductProvider>();
        return services;
    }
}
```

**Service dependencies:**

```csharp
public static IServiceCollection AddServiceDependencies(
    this IServiceCollection services, IConfiguration configuration)
{
    ConfigureExternalApiService(services, configuration);
    ConfigureNotificationService(services, configuration);
    return services;
}

private static void ConfigureExternalApiService(
    IServiceCollection services, IConfiguration configuration)
{
    services.Configure<ExternalApiOptions>(
        configuration.GetSection("ExternalApiService"));

    services.AddHttpClient<IExternalApiService, ExternalApiService>((sp, client) =>
    {
        var options = sp.GetRequiredService<IOptions<ExternalApiOptions>>().Value;
        client.BaseAddress = new Uri(options.BaseUrl);
    }).AddHttpMessageHandler<DependencyHandler>();  // MANDATORY
}
```

### HTTP Client -- DependencyHandler is MANDATORY

```csharp
// BAD: Missing resilience and telemetry
services.AddHttpClient<IExternalService, ExternalService>();

// GOOD: With handler
services.AddHttpClient<IExternalService, ExternalService>((sp, client) =>
{
    var options = sp.GetRequiredService<IOptions<ExternalServiceOptions>>().Value;
    client.BaseAddress = new Uri(options.BaseUrl);
    client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
}).AddHttpMessageHandler<DependencyHandler>();
```

### Options Pattern

```csharp
// Options class
public class ExternalApiOptions
{
    public required string BaseUrl { get; init; }
    public required string ApiKey { get; init; }
    public int TimeoutSeconds { get; init; } = 30;
    public int MaxRetries { get; init; } = 3;
}
```

```json
// appsettings.json
{
  "ExternalApiService": {
    "BaseUrl": "https://api.example.com",
    "ApiKey": "from-keyvault",
    "TimeoutSeconds": 30,
    "MaxRetries": 3
  }
}
```

```csharp
// Injecting options
public class ExternalApiService : IExternalApiService
{
    private readonly HttpClient _httpClient;
    private readonly ExternalApiOptions _options;

    public ExternalApiService(HttpClient httpClient, IOptions<ExternalApiOptions> options)
    {
        _httpClient = httpClient;
        _options = options.Value;
    }
}
```

### Lifetime Guidelines

| Lifetime | Use For | Example |
|----------|---------|---------|
| **Singleton** | Stateless, thread-safe services | `IMemoryCache`, Configuration |
| **Scoped** | Per-request state, DB contexts | Providers, Services, `DbContext` |
| **Transient** | Lightweight, stateless helpers | Validators, Factories |

### Naming Conventions

| Type | Naming | Interface |
|------|--------|-----------|
| Provider | `{Feature}Provider` | `I{Feature}Provider` |
| Service | `{External}Service` | `I{External}Service` |
| Repository | `{Entity}Repository` | `I{Entity}Repository` |
| Options | `{Feature}Options` | - |
| Handler | `{Purpose}Handler` | `I{Purpose}Handler` |

### Layered Architecture

```
+---------------------------------+
|     Controllers / Functions     |  <- Inject: Providers, ErrorMapper
+---------------------------------+
|           Providers             |  <- Inject: Services, Options, Cache
+---------------------------------+
|            Services             |  <- Inject: HttpClient, Options
+---------------------------------+
|     Infrastructure/External     |
+---------------------------------+
```

### Common Pitfalls

**Forgetting DependencyHandler** -- see HTTP Client section above.

**Scoped service captured in singleton:**

```csharp
// BAD: Captive dependency
services.AddSingleton<SingletonService>();  // Captures scoped service

// GOOD: Use IServiceScopeFactory
public class SingletonService
{
    private readonly IServiceScopeFactory _scopeFactory;
    public async Task DoWork()
    {
        using var scope = _scopeFactory.CreateScope();
        var scoped = scope.ServiceProvider.GetRequiredService<IScopedService>();
    }
}
```

**Not validating options:**

```csharp
services.AddOptions<ApiCenterOptions>()
    .Bind(configuration.GetSection("ApiCenterService"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

---

## 5. ASP.NET Core

### Controller Structure (Versioned)

```csharp
namespace YourProject.Controllers.V1;

[ApiController]
[ApiVersion("1.0")]
[Route("api/v{version:apiVersion}/[controller]")]
[Produces("application/json")]
public class UsersController : ControllerBase
{
    private readonly IUserProvider _provider;
    private readonly IErrorMapper _errorMapper;

    public UsersController(IUserProvider provider, IErrorMapper errorMapper)
    {
        _provider = provider;
        _errorMapper = errorMapper;
    }

    [HttpGet("{userId}")]
    [ProducesResponseType(typeof(UserResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(NotFoundResponse), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(BadRequestResponse), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> GetUser(string userId)
    {
        Result<UserResponse> result = await _provider.GetUserAsync(userId);
        return result.ToActionResult(_errorMapper, response => Ok(response));
    }
}
```

### Route Conventions

```
GET    /api/v1/users              # List users
GET    /api/v1/users/{id}         # Get single user
POST   /api/v1/users              # Create user
PUT    /api/v1/users/{id}         # Replace user
PATCH  /api/v1/users/{id}         # Partial update
DELETE /api/v1/users/{id}         # Delete user
GET    /api/v1/users/{id}/orders  # Nested resources
```

Use kebab-case for multi-word resources, plural nouns for collections, path parameters for identifiers, query parameters for filtering.

### Response Patterns

```csharp
// GET single
[HttpGet("{id}")]
public async Task<IActionResult> Get(string id)
{
    Result<UserResponse> result = await _provider.GetAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}

// POST create
[HttpPost]
public async Task<IActionResult> Create([FromBody] CreateUserRequest request)
{
    Result<UserResponse> result = await _provider.CreateAsync(request);
    return result.ToActionResult(_errorMapper, response =>
        CreatedAtAction(nameof(Get), new { id = response.Id }, response));
}

// DELETE
[HttpDelete("{id}")]
public async Task<IActionResult> Delete(string id)
{
    Result result = await _provider.DeleteAsync(id);
    return result.ToActionResult(_errorMapper, () => NoContent());
}
```

### Model Binding / Validation

```csharp
public class CreateUserRequest
{
    [Required(ErrorMessage = "Name is required")]
    [StringLength(100, MinimumLength = 2)]
    public required string Name { get; init; }

    [Required]
    [EmailAddress(ErrorMessage = "Invalid email format")]
    public required string Email { get; init; }

    [Range(18, 120, ErrorMessage = "Age must be between 18 and 120")]
    public int? Age { get; init; }
}
```

### API Versioning

```csharp
services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;
    options.ApiVersionReader = new UrlSegmentApiVersionReader();
});
```

---

## 6. Azure Functions

Isolated worker model for .NET 8.

### HTTP Trigger

```csharp
public class UserFunctions
{
    private readonly IUserProvider _provider;
    private readonly IErrorMapper _errorMapper;
    private readonly ILogger<UserFunctions> _logger;

    public UserFunctions(
        IUserProvider provider, IErrorMapper errorMapper, ILogger<UserFunctions> logger)
    {
        _provider = provider;
        _errorMapper = errorMapper;
        _logger = logger;
    }

    [Function("GetUser")]
    public async Task<HttpResponseData> GetUser(
        [HttpTrigger(AuthorizationLevel.Function, "get", Route = "users/{userId}")]
        HttpRequestData req, string userId)
    {
        Result<UserResponse> result = await _provider.GetUserAsync(userId);
        return await result.ToHttpResponseAsync(req, _errorMapper,
            response => req.CreateJsonResponse(response, HttpStatusCode.OK));
    }
}
```

### Timer Trigger

```csharp
public class CleanupFunction
{
    private readonly ICleanupProvider _provider;
    private readonly ILogger<CleanupFunction> _logger;

    public CleanupFunction(ICleanupProvider provider, ILogger<CleanupFunction> logger)
    {
        _provider = provider;
        _logger = logger;
    }

    [Function("DailyCleanup")]
    public async Task Run([TimerTrigger("0 0 2 * * *")] TimerInfo timer)
    {
        Result<int> result = await _provider.CleanupExpiredRecordsAsync();
        if (result.IsError)
        {
            _logger.LogError("Cleanup failed: {Error}", result.Error.Message);
            return;
        }
        _logger.LogInformation("Cleaned up {Count} records", result.Value);
    }
}
```

### Queue Trigger

```csharp
[Function("ProcessMessage")]
public async Task Run(
    [QueueTrigger("incoming-messages", Connection = "StorageConnection")]
    QueueMessage message)
{
    Result result = await _processor.ProcessAsync(message.Body.ToString());
    if (result.IsError)
    {
        _logger.LogError("Failed to process {MessageId}: {Error}",
            message.MessageId, result.Error.Message);
        throw new InvalidOperationException(result.Error.Message);  // Triggers retry
    }
}
```

### Host Configuration (Program.cs)

```csharp
var host = new HostBuilder()
    .ConfigureFunctionsWorkerDefaults(worker =>
    {
        worker.UseNewtonsoftJson();
    })
    .ConfigureServices((context, services) =>
    {
        IConfiguration configuration = context.Configuration;
        services.AddApplicationInsightsTelemetryWorkerService();
        services.ConfigureFunctionsApplicationInsights();
        services.AddBusinessDependencies();
        services.AddServiceDependencies(configuration);
        services.AddErrorMappings();
    })
    .Build();

await host.RunAsync();
```

### Error Handling Extensions

```csharp
public static class HttpResponseExtensions
{
    public static async Task<HttpResponseData> ToHttpResponseAsync<T>(
        this Result<T> result, HttpRequestData request,
        IErrorMapper errorMapper, Func<T, HttpResponseData> onSuccess)
    {
        if (result.IsError)
            return CreateErrorResponse(request, result.Error, errorMapper);
        return onSuccess(result.Value);
    }
}
```

---

## 7. Testing with NUnit

### BaseTest Pattern

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
}
```

### Test Class Structure

```csharp
[TestFixture]
public class UserProviderTests : BaseTest
{
    // 1. Private fields for mocks and SUT
    private Mock<IUserService> _userServiceMock;
    private Mock<ILogger<UserProvider>> _loggerMock;
    private UserProvider _sut;

    // 2. SetUp runs before each test
    [SetUp]
    public void SetUp()
    {
        _userServiceMock = new Mock<IUserService>();
        _loggerMock = new Mock<ILogger<UserProvider>>();
        _sut = new UserProvider(_userServiceMock.Object, _loggerMock.Object);
    }

    // 3. Tests grouped by method
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
}
```

### Naming Convention

```
[MethodName]_[Scenario]_[ExpectedResult]

GetUserAsync_WithValidId_ReturnsUser()
GetUserAsync_WithNullId_ReturnsInvalidInputError()
ProcessOrder_WhenInventoryInsufficient_ReturnsConflictError()
```

### Assertion Patterns (EnterMultipleScope)

```csharp
// PREFERRED: EnterMultipleScope (reports all failures, not just the first)
using (Assert.EnterMultipleScope())
{
    Assert.That(result.IsError, Is.False);
    Assert.That(result.Value.Id, Is.EqualTo(expectedId));
    Assert.That(result.Value.Items, Has.Count.EqualTo(3));
}
```

### Common Assertions

```csharp
Assert.That(actual, Is.EqualTo(expected));
Assert.That(value, Is.Null);
Assert.That(value, Is.Not.Null);
Assert.That(error, Is.TypeOf<NotFoundError>());
Assert.That(result, Is.InstanceOf<BaseError>());
Assert.That(list, Is.Empty);
Assert.That(list, Has.Count.EqualTo(5));
Assert.That(list, Contains.Item(expected));
Assert.That(list, Has.Exactly(2).Matches<User>(u => u.IsActive));
Assert.That(text, Does.Contain("not found"));
Assert.That(result.IsError, Is.True);
Assert.ThrowsAsync<ArgumentNullException>(async () => await _sut.ProcessAsync(null));
```

### Mocking Patterns

```csharp
// Setup: return success
_serviceMock
    .Setup(x => x.GetAsync(It.IsAny<string>()))
    .ReturnsAsync(Result<User>.Success(testUser));

// Setup: return error
_serviceMock
    .Setup(x => x.GetAsync("invalid"))
    .ReturnsAsync(new NotFoundError("Not found"));

// Setup: throw exception
_serviceMock
    .Setup(x => x.GetAsync("error"))
    .ThrowsAsync(new HttpRequestException("Network error"));

// Setup: conditional returns
_serviceMock
    .Setup(x => x.GetAsync(It.Is<string>(id => id.StartsWith("valid"))))
    .ReturnsAsync(Result<User>.Success(testUser));

// Verification
_serviceMock.Verify(x => x.GetAsync(userId), Times.Once);
_serviceMock.Verify(x => x.DeleteAsync(It.IsAny<string>()), Times.Never);
_serviceMock.Verify(x => x.SaveAsync(It.Is<User>(u => u.Id == expectedId)), Times.Once);
```

### Test Data Patterns

```csharp
// Dynamic dates (never hardcode dates that will break)
var item = new Subscription
{
    ExpiresAt = DateTime.UtcNow.AddDays(-1)  // Yesterday -- always in the past
};

// Test data builders
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
}
```

### Running Tests

```powershell
dotnet test                                           # Run all tests
dotnet test --verbosity normal                        # With verbosity
dotnet test --filter "Category=Integration"           # Specific category
dotnet test --filter "FullyQualifiedName~UserProviderTests"  # Specific class
dotnet test --collect:"XPlat Code Coverage"           # With coverage
```
