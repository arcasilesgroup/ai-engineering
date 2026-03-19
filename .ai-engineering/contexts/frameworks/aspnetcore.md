## ASP.NET Core Best Practices

### Project Structure

**Organize by feature, not layer:**

- Group related files together
- Use minimal API for simple endpoints
- Use controllers for complex logic
- Separate concerns: Controllers, Services, Repositories

**Pattern:**

```text
Features/
  Users/
    UserController.cs
    UserService.cs
    UserRepository.cs
    User.cs
  Products/
    ProductController.cs
    ...
```text

### Dependency Injection

**Built-in DI container:**

- Register services in `Program.cs`
- Use constructor injection
- Register appropriate lifetimes: Singleton, Scoped, Transient
- Inject interfaces, not implementations

**Pattern:**

```csharp
// ✅ GOOD: Service registration
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddSingleton<IEmailService, EmailService>();

// ✅ GOOD: Constructor injection
public class UserController : ControllerBase
{
    private readonly IUserService _userService;

    public UserController(IUserService userService)
    {
        _userService = userService;
    }
}
```text

### Controllers and Routing

**RESTful API design:**

- Use attribute routing
- Return appropriate HTTP status codes
- Use `ActionResult<T>` for typed responses
- Use route constraints and model binding

**Pattern:**

```csharp
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    public UsersController(IUserService userService)
    {
        _userService = userService;
    }

    // ✅ GOOD: Typed response with status codes
    [HttpGet("{id}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<UserDto>> GetUser(string id)
    {
        var user = await _userService.GetUserAsync(id);
        if (user == null)
        {
            return NotFound();
        }
        return Ok(user);
    }

    [HttpPost]
    [ProducesResponseType(StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<UserDto>> CreateUser(CreateUserRequest request)
    {
        if (!ModelState.IsValid)
        {
            return BadRequest(ModelState);
        }

        var user = await _userService.CreateUserAsync(request);
        return CreatedAtAction(nameof(GetUser), new { id = user.Id }, user);
    }
}
```text

### Middleware

**Custom middleware:**

- Use for cross-cutting concerns
- Keep middleware focused
- Order matters in pipeline
- Use `IApplicationBuilder` extensions

**Pattern:**

```csharp
// ✅ GOOD: Custom middleware
public class RequestLoggingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RequestLoggingMiddleware> _logger;

    public RequestLoggingMiddleware(
        RequestDelegate next,
        ILogger<RequestLoggingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        _logger.LogInformation("Request: {Method} {Path}",
            context.Request.Method,
            context.Request.Path);

        await _next(context);

        _logger.LogInformation("Response: {StatusCode}",
            context.Response.StatusCode);
    }
}

// Extension method
public static class MiddlewareExtensions
{
    public static IApplicationBuilder UseRequestLogging(
        this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<RequestLoggingMiddleware>();
    }
}

// Usage in Program.cs
app.UseRequestLogging();
```text

### Configuration

**Use configuration system:**

- appsettings.json for defaults
- appsettings.{Environment}.json for environment-specific
- Environment variables for secrets
- Use Options pattern for strongly-typed config

**Pattern:**

```csharp
// ✅ GOOD: Options pattern
public class EmailOptions
{
    public string SmtpHost { get; set; } = string.Empty;
    public int SmtpPort { get; set; }
    public string FromAddress { get; set; } = string.Empty;
}

// Registration
builder.Services.Configure<EmailOptions>(
    builder.Configuration.GetSection("Email"));

// Usage
public class EmailService
{
    private readonly EmailOptions _options;

    public EmailService(IOptions<EmailOptions> options)
    {
        _options = options.Value;
    }
}
```text

### Validation

**Model validation:**

- Use data annotations
- Use FluentValidation for complex rules
- Validate in controller actions
- Return validation errors to client

**Pattern:**

```csharp
// ✅ GOOD: Data annotations
public class CreateUserRequest
{
    [Required]
    [EmailAddress]
    public string Email { get; set; } = string.Empty;

    [Required]
    [MinLength(3)]
    [MaxLength(50)]
    public string Name { get; set; } = string.Empty;

    [Required]
    [MinLength(8)]
    public string Password { get; set; } = string.Empty;
}

// ✅ GOOD: FluentValidation
public class CreateUserValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserValidator()
    {
        RuleFor(x => x.Email).NotEmpty().EmailAddress();
        RuleFor(x => x.Name).NotEmpty().Length(3, 50);
        RuleFor(x => x.Password).NotEmpty().MinimumLength(8);
    }
}

// Registration
builder.Services.AddValidatorsFromAssemblyContaining<CreateUserValidator>();
```text

### Error Handling

**Global exception handling:**

- Use exception middleware
- Return consistent error responses
- Log exceptions
- Don't expose sensitive information

**Pattern:**

```csharp
// ✅ GOOD: Exception middleware
public class ExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionMiddleware> _logger;

    public ExceptionMiddleware(
        RequestDelegate next,
        ILogger<ExceptionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception");
            await HandleExceptionAsync(context, ex);
        }
    }

    private static async Task HandleExceptionAsync(
        HttpContext context,
        Exception exception)
    {
        context.Response.ContentType = "application/json";
        context.Response.StatusCode = exception switch
        {
            NotFoundException => StatusCodes.Status404NotFound,
            ValidationException => StatusCodes.Status400BadRequest,
            UnauthorizedException => StatusCodes.Status401Unauthorized,
            _ => StatusCodes.Status500InternalServerError
        };

        var response = new
        {
            error = exception.Message,
            statusCode = context.Response.StatusCode
        };

        await context.Response.WriteAsJsonAsync(response);
    }
}
```text

### Authentication and Authorization

**Security best practices:**

- Use JWT for stateless auth
- Use Identity for user management
- Implement proper authorization
- Use HTTPS only

**Pattern:**

```csharp
// ✅ GOOD: JWT authentication
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Key"]))
        };
    });

builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("AdminOnly", policy =>
        policy.RequireRole("Admin"));
});

// Usage
[Authorize(Policy = "AdminOnly")]
[HttpDelete("{id}")]
public async Task<IActionResult> DeleteUser(string id)
{
    await _userService.DeleteUserAsync(id);
    return NoContent();
}
```text

### Database Access

**Entity Framework Core:**

- Use async methods
- Use DbContext scoped per request
- Use migrations for schema changes
- Avoid N+1 queries with Include

**Pattern:**

```csharp
// ✅ GOOD: Repository pattern
public class UserRepository : IUserRepository
{
    private readonly AppDbContext _context;

    public UserRepository(AppDbContext context)
    {
        _context = context;
    }

    public async Task<User?> GetByIdAsync(string id)
    {
        return await _context.Users
            .Include(u => u.Profile)
            .FirstOrDefaultAsync(u => u.Id == id);
    }

    public async Task<List<User>> GetActiveUsersAsync()
    {
        return await _context.Users
            .Where(u => u.IsActive)
            .OrderBy(u => u.Name)
            .ToListAsync();
    }

    public async Task AddAsync(User user)
    {
        await _context.Users.AddAsync(user);
        await _context.SaveChangesAsync();
    }
}
```text

### Logging

**Use structured logging:**

- Use ILogger<T> from DI
- Include context in log messages
- Use appropriate log levels
- Configure providers in appsettings.json

**Pattern:**

```csharp
// ✅ GOOD: Structured logging
public class UserService
{
    private readonly ILogger<UserService> _logger;

    public UserService(ILogger<UserService> logger)
    {
        _logger = logger;
    }

    public async Task<User> GetUserAsync(string id)
    {
        _logger.LogInformation("Fetching user {UserId}", id);

        try
        {
            var user = await _repository.GetByIdAsync(id);
            if (user == null)
            {
                _logger.LogWarning("User {UserId} not found", id);
            }
            return user;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching user {UserId}", id);
            throw;
        }
    }
}
```text

### Testing

**Testing best practices:**

- Unit test services and business logic
- Integration test controllers with WebApplicationFactory
- Use in-memory database for testing
- Mock dependencies

**Pattern:**

```csharp
// ✅ GOOD: Unit test
public class UserServiceTests
{
    private readonly Mock<IUserRepository> _mockRepository;
    private readonly UserService _service;

    public UserServiceTests()
    {
        _mockRepository = new Mock<IUserRepository>();
        _service = new UserService(_mockRepository.Object);
    }

    [Fact]
    public async Task GetUserAsync_ShouldReturnUser_WhenUserExists()
    {
        // Arrange
        var userId = "123";
        var user = new User { Id = userId, Name = "John" };
        _mockRepository
            .Setup(r => r.GetByIdAsync(userId))
            .ReturnsAsync(user);

        // Act
        var result = await _service.GetUserAsync(userId);

        // Assert
        Assert.NotNull(result);
        Assert.Equal(userId, result.Id);
    }
}

// ✅ GOOD: Integration test
public class UsersControllerTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;

    public UsersControllerTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task GetUser_ShouldReturn200_WhenUserExists()
    {
        var client = _factory.CreateClient();
        var response = await client.GetAsync("/api/users/123");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}
```text

### Common Anti-Patterns

**Avoid:**

- Blocking async code with `.Result` or `.Wait()`
- Using `dynamic` unnecessarily
- Not disposing DbContext properly
- Catching and swallowing exceptions
- Putting business logic in controllers
- Not using async/await for I/O operations
- Hardcoding configuration values
