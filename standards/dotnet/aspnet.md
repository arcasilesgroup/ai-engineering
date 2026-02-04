# ASP.NET Core Standards

> Patterns and conventions for ASP.NET Core Web APIs.

---

## Controller Structure

### Versioned Controllers

```csharp
namespace {YourProject}.Controllers.V1;

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
    
    /// <summary>
    /// Gets a user by ID.
    /// </summary>
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

---

## Route Conventions

### URL Patterns

```
GET    /api/v1/users              # List users
GET    /api/v1/users/{id}         # Get single user
POST   /api/v1/users              # Create user
PUT    /api/v1/users/{id}         # Replace user
PATCH  /api/v1/users/{id}         # Partial update
DELETE /api/v1/users/{id}         # Delete user

# Nested resources
GET    /api/v1/users/{id}/orders           # List user's orders
GET    /api/v1/users/{id}/orders/{orderId} # Get specific order
```

### Route Naming

- Use **kebab-case** for multi-word resources: `/api/v1/api-versions`
- Use **plural nouns** for collections: `/users`, `/orders`
- Use **path parameters** for identifiers: `/users/{userId}`
- Use **query parameters** for filtering: `/users?status=active&pageSize=20`

---

## HTTP Methods & Status Codes

| Action | Method | Success | Common Errors |
|--------|--------|---------|---------------|
| List | GET | 200 OK | 400 Bad Request |
| Get single | GET | 200 OK | 404 Not Found |
| Create | POST | 201 Created | 400 Bad Request, 409 Conflict |
| Replace | PUT | 200 OK | 404 Not Found, 400 Bad Request |
| Partial update | PATCH | 200 OK | 404 Not Found, 400 Bad Request |
| Delete | DELETE | 204 No Content | 404 Not Found |

---

## Response Patterns

### Success Responses

```csharp
// GET single item
[HttpGet("{id}")]
public async Task<IActionResult> Get(string id)
{
    Result<UserResponse> result = await _provider.GetAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}

// GET list
[HttpGet]
public async Task<IActionResult> GetAll([FromQuery] int pageSize = 20)
{
    Result<UsersResponse> result = await _provider.GetAllAsync(pageSize);
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

### Error Response Format (Problem Details)

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.4",
  "title": "Not Found",
  "status": 404,
  "detail": "User with ID 'user-123' was not found.",
  "traceId": "00-abc123-def456-00"
}
```

---

## ProducesResponseType Attributes

Always document all possible response types:

```csharp
[HttpGet("{id}")]
[ProducesResponseType(typeof(UserResponse), StatusCodes.Status200OK)]
[ProducesResponseType(typeof(NotFoundResponse), StatusCodes.Status404NotFound)]
[ProducesResponseType(typeof(BadRequestResponse), StatusCodes.Status400BadRequest)]
[ProducesResponseType(typeof(InternalErrorResponse), StatusCodes.Status500InternalServerError)]
public async Task<IActionResult> GetUser(string id)
```

---

## Input Validation

### Model Validation

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

### FluentValidation (for complex rules)

```csharp
public class CreateUserRequestValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserRequestValidator()
    {
        RuleFor(x => x.Name)
            .NotEmpty()
            .MaximumLength(100);
            
        RuleFor(x => x.Email)
            .NotEmpty()
            .EmailAddress()
            .Must(BeUniqueEmail)
            .WithMessage("Email already in use");
    }
    
    private bool BeUniqueEmail(string email) => 
        // Validation logic
        true;
}
```

---

## API Versioning

### Configuration

```csharp
services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;
    options.ApiVersionReader = new UrlSegmentApiVersionReader();
})
.AddMvc(options =>
{
    options.Conventions.Add(new VersionByNamespaceConvention());
});
```

### Deprecation

```csharp
[ApiController]
[ApiVersion("1.0", Deprecated = true)]  // Mark as deprecated
[ApiVersion("2.0")]
[Route("api/v{version:apiVersion}/[controller]")]
public class UsersController : ControllerBase
{
    [HttpGet("{id}")]
    [MapToApiVersion("1.0")]
    public async Task<IActionResult> GetV1(string id) { }
    
    [HttpGet("{id}")]
    [MapToApiVersion("2.0")]
    public async Task<IActionResult> GetV2(string id) { }
}
```

---

## Swagger/OpenAPI

### Operation Documentation

```csharp
/// <summary>
/// Retrieves a user by their unique identifier.
/// </summary>
/// <param name="userId">The unique identifier of the user.</param>
/// <returns>The requested user details.</returns>
/// <response code="200">Returns the user.</response>
/// <response code="404">User not found.</response>
[HttpGet("{userId}")]
[SwaggerOperation(
    Summary = "Get user by ID",
    Description = "Retrieves detailed information about a specific user.",
    OperationId = "Users_GetById",
    Tags = new[] { "Users" }
)]
public async Task<IActionResult> GetUser(string userId)
```

---

## Dependency Injection Pattern

### Controller Constructor

```csharp
public class UsersController : ControllerBase
{
    private readonly IUserProvider _provider;
    private readonly IErrorMapper _errorMapper;
    private readonly ILogger<UsersController> _logger;
    
    public UsersController(
        IUserProvider provider,
        IErrorMapper errorMapper,
        ILogger<UsersController> logger)
    {
        _provider = provider;
        _errorMapper = errorMapper;
        _logger = logger;
    }
}
```

### Registration in Startup

```csharp
public static IServiceCollection AddBusinessDependencies(this IServiceCollection services)
{
    services.AddScoped<IUserProvider, UserProvider>();
    services.AddScoped<IOrderProvider, OrderProvider>();
    return services;
}
```
