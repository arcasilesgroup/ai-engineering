# .NET / C# Coding Standards

These standards govern all C# and .NET code generation. Follow every rule unless the developer explicitly overrides it. When in doubt, prefer clarity over cleverness, and consistency over personal style.

---

## C# Naming Conventions

### PascalCase

Use PascalCase for all public and protected members.

- Classes, records, structs, enums, interfaces, delegates
- Public/protected properties, methods, events, fields
- Namespaces
- Type parameters

```csharp
// DO
public class OrderService { }
public record OrderCreatedEvent(Guid OrderId, DateTime CreatedAt);
public enum OrderStatus { Pending, Confirmed, Shipped }
public interface IOrderRepository { }
public delegate void OrderChangedHandler(Order order);

// DON'T
public class orderService { }   // camelCase
public class order_service { }  // snake_case
```

### camelCase

Use camelCase for:

- Local variables
- Method parameters
- Lambda parameters

```csharp
// DO
public decimal CalculateTotal(IEnumerable<OrderLine> orderLines)
{
    var totalAmount = orderLines.Sum(line => line.Price * line.Quantity);
    return totalAmount;
}
```

### Underscore Prefix for Private Fields

Use `_camelCase` for private fields. Do NOT use `this.` to disambiguate.

```csharp
// DO
public class OrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly ILogger<OrderService> _logger;

    public OrderService(IOrderRepository orderRepository, ILogger<OrderService> logger)
    {
        _orderRepository = orderRepository;
        _logger = logger;
    }
}

// DON'T
public class OrderService
{
    private readonly IOrderRepository orderRepository;  // missing underscore
    private readonly ILogger<OrderService> m_logger;    // Hungarian notation
}
```

### Interface Naming

Always prefix interfaces with `I`.

```csharp
// DO
public interface IOrderRepository { }
public interface IEmailSender { }

// DON'T
public interface OrderRepository { }
public interface EmailSenderInterface { }
```

### Async Method Naming

Always suffix async methods with `Async`.

```csharp
// DO
public Task<Order> GetOrderAsync(Guid id, CancellationToken cancellationToken = default);
public Task SendEmailAsync(EmailMessage message, CancellationToken cancellationToken = default);

// DON'T
public Task<Order> GetOrder(Guid id);   // missing Async suffix
public Task SendEmail(EmailMessage message);
```

### Boolean Naming

Prefix booleans with `is`, `has`, `can`, `should`, or similar verbs.

```csharp
// DO
public bool IsActive { get; set; }
public bool HasDiscount { get; set; }
public bool CanEdit { get; set; }
private bool _shouldRetry;

// DON'T
public bool Active { get; set; }    // ambiguous
public bool Discount { get; set; }  // sounds like a noun
```

### Constants and Static Readonly

Use PascalCase for constants. Do NOT use SCREAMING_CASE.

```csharp
// DO
public const int MaxRetryCount = 3;
public static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(30);

// DON'T
public const int MAX_RETRY_COUNT = 3;   // not C# convention
public const int max_retry_count = 3;
```

---

## Code Layout and Formatting

### File Organization

Place members in this order within a class:

1. Constants and static readonly fields
2. Private fields
3. Constructors
4. Public properties
5. Public methods
6. Private/internal methods
7. Nested types (avoid if possible)

```csharp
public class OrderService : IOrderService
{
    // 1. Constants
    private const int MaxPageSize = 100;

    // 2. Private fields
    private readonly IOrderRepository _orderRepository;
    private readonly ILogger<OrderService> _logger;

    // 3. Constructor
    public OrderService(IOrderRepository orderRepository, ILogger<OrderService> logger)
    {
        _orderRepository = orderRepository;
        _logger = logger;
    }

    // 4. Public properties (if any)

    // 5. Public methods
    public async Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        // ...
    }

    // 6. Private methods
    private void ValidateOrder(Order order)
    {
        // ...
    }
}
```

### One Class Per File

Every top-level type gets its own file. The filename must match the type name.

```
// DO
OrderService.cs       -> public class OrderService
IOrderRepository.cs   -> public interface IOrderRepository
OrderStatus.cs        -> public enum OrderStatus
OrderCreatedEvent.cs  -> public record OrderCreatedEvent

// DON'T
Models.cs  -> contains Order, OrderLine, Customer (multiple types)
```

Exceptions:

- Record types used exclusively as inner DTOs of a single parent class may be nested
- Small companion types (e.g., a private helper record) may share a file if they are tightly coupled and private

### Namespace Matches Folder Structure

```
// File: src/Orders/Application/Commands/CreateOrderCommand.cs
namespace MyApp.Orders.Application.Commands;

// DON'T mismatch folder and namespace
// File: src/Orders/CreateOrderCommand.cs
namespace MyApp.Application.Commands;  // wrong: doesn't match file location
```

Use file-scoped namespaces (C# 10+).

```csharp
// DO
namespace MyApp.Orders.Application.Commands;

public class CreateOrderCommand { }

// DON'T
namespace MyApp.Orders.Application.Commands
{
    public class CreateOrderCommand { }  // unnecessary nesting
}
```

### Braces and Indentation

- Use Allman style braces (opening brace on its own line)
- 4-space indentation (no tabs)
- Always use braces for `if`, `for`, `while`, `foreach`, even for single-line bodies

```csharp
// DO
if (order.IsValid)
{
    await ProcessOrderAsync(order, cancellationToken);
}

// DON'T
if (order.IsValid)
    await ProcessOrderAsync(order, cancellationToken);  // missing braces

if (order.IsValid) { await ProcessOrderAsync(order, cancellationToken); }  // Egyptian braces
```

### Using Directives

Place `using` directives at the top of the file, outside the namespace. Rely on `global using` in a `GlobalUsings.cs` file for frequently used namespaces.

```csharp
// GlobalUsings.cs
global using System;
global using System.Collections.Generic;
global using System.Linq;
global using System.Threading;
global using System.Threading.Tasks;
global using Microsoft.Extensions.Logging;
```

---

## Commenting Standards

### XML Documentation

Add XML doc comments to all public and protected members. Focus on describing the purpose and behavior, not restating the signature.

```csharp
// DO
/// <summary>
/// Retrieves an order by its unique identifier.
/// Returns null if no order is found.
/// </summary>
/// <param name="id">The unique identifier of the order.</param>
/// <param name="cancellationToken">Token to cancel the operation.</param>
/// <returns>The order if found; otherwise, null.</returns>
/// <exception cref="ArgumentException">Thrown when <paramref name="id"/> is empty.</exception>
public Task<Order?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);

// DON'T
/// <summary>
/// Gets order by id.  // too terse, restates signature
/// </summary>
public Task<Order?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
```

### Inline Comments

Use inline comments sparingly -- only when the code's intent is not self-evident. Never comment what the code does; comment why.

```csharp
// DO
// Retry with exponential backoff because the payment gateway has transient failures
await Policy.Handle<HttpRequestException>()
    .WaitAndRetryAsync(3, attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt)))
    .ExecuteAsync(() => gateway.ChargeAsync(payment, cancellationToken));

// DON'T
// Set x to 5
var x = 5;

// Loop through orders
foreach (var order in orders) { }
```

### TODO Comments

Use `// TODO:` for known technical debt. Include a brief description of what needs to happen and ideally a ticket reference.

```csharp
// TODO: Replace in-memory cache with Redis once infrastructure is provisioned (PROJ-1234)
```

---

## Nullable Reference Types

### Always Enable Nullable

Enable nullable reference types project-wide. Never disable it per-file.

```xml
<!-- In .csproj -->
<PropertyGroup>
    <Nullable>enable</Nullable>
</PropertyGroup>
```

### Handle Nulls Explicitly

Annotate return types and parameters correctly. Use the null-forgiving operator (`!`) only when you can prove the value is non-null.

```csharp
// DO
public async Task<Order?> FindByIdAsync(Guid id, CancellationToken cancellationToken = default)
{
    var order = await _dbContext.Orders.FindAsync(new object[] { id }, cancellationToken);
    return order; // may be null -- caller must handle
}

public async Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
{
    var order = await _dbContext.Orders.FindAsync(new object[] { id }, cancellationToken);
    return order ?? throw new NotFoundException($"Order {id} not found.");
}

// DON'T
public async Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
{
    return (await _dbContext.Orders.FindAsync(new object[] { id }, cancellationToken))!;
    // null-forgiving hides a potential NullReferenceException
}
```

### Null Guard on Constructor Parameters

Guard required constructor parameters with `ArgumentNullException`.

```csharp
// DO (C# 10+)
public OrderService(IOrderRepository orderRepository, ILogger<OrderService> logger)
{
    _orderRepository = orderRepository ?? throw new ArgumentNullException(nameof(orderRepository));
    _logger = logger ?? throw new ArgumentNullException(nameof(logger));
}

// DO (C# 11+ with required keyword for DTOs)
public class CreateOrderRequest
{
    public required string CustomerName { get; init; }
    public required List<OrderLineRequest> Lines { get; init; }
}
```

---

## Record Types vs Classes vs Structs

### Use Records For

- DTOs and request/response objects
- Events
- Value objects in DDD
- Anything that is data-centric and benefits from value equality

```csharp
// DO - Immutable DTO
public record OrderResponse(
    Guid Id,
    string CustomerName,
    decimal TotalAmount,
    OrderStatus Status,
    DateTime CreatedAt);

// DO - Event
public record OrderCreatedEvent(Guid OrderId, string CustomerEmail, DateTime OccurredAt);

// DO - Value Object
public record Money(decimal Amount, string Currency);
public record Address(string Street, string City, string State, string ZipCode, string Country);
```

### Use Classes For

- Entities with identity and mutable state
- Services with injected dependencies
- Complex objects with behavior

```csharp
// DO - Entity with identity
public class Order
{
    public Guid Id { get; private set; }
    public OrderStatus Status { get; private set; }
    private readonly List<OrderLine> _lines = new();
    public IReadOnlyCollection<OrderLine> Lines => _lines.AsReadOnly();

    public void AddLine(Product product, int quantity)
    {
        _lines.Add(new OrderLine(product, quantity));
    }
}
```

### Use Structs For

- Small, immutable value types (under ~16 bytes)
- Performance-critical scenarios (avoid heap allocation)
- Types that represent a single value

```csharp
// DO
public readonly struct Coordinate
{
    public double Latitude { get; }
    public double Longitude { get; }

    public Coordinate(double latitude, double longitude)
    {
        Latitude = latitude;
        Longitude = longitude;
    }
}
```

Always make structs `readonly` to prevent defensive copying.

---

## Pattern Matching

### Switch Expressions

Prefer switch expressions over switch statements for mapping and transformations.

```csharp
// DO
public string GetStatusMessage(OrderStatus status) => status switch
{
    OrderStatus.Pending => "Your order is being processed.",
    OrderStatus.Confirmed => "Your order has been confirmed.",
    OrderStatus.Shipped => "Your order is on its way!",
    OrderStatus.Delivered => "Your order has been delivered.",
    OrderStatus.Cancelled => "Your order was cancelled.",
    _ => throw new ArgumentOutOfRangeException(nameof(status), status, "Unknown order status.")
};

// DON'T
public string GetStatusMessage(OrderStatus status)
{
    switch (status)
    {
        case OrderStatus.Pending:
            return "Your order is being processed.";
        case OrderStatus.Confirmed:
            return "Your order has been confirmed.";
        // ... verbose, error-prone
        default:
            throw new ArgumentOutOfRangeException(nameof(status));
    }
}
```

### Property Patterns

Use property patterns for complex condition matching.

```csharp
// DO
public decimal CalculateDiscount(Order order) => order switch
{
    { TotalAmount: > 1000, Customer.IsPremium: true } => 0.20m,
    { TotalAmount: > 1000 } => 0.10m,
    { TotalAmount: > 500 } => 0.05m,
    { Customer.IsPremium: true } => 0.03m,
    _ => 0m
};
```

### Is Patterns and Type Checks

Use `is` patterns instead of `as` + null check.

```csharp
// DO
if (result is SuccessResult success)
{
    return Ok(success.Value);
}

if (error is ValidationError { Errors.Count: > 0 } validationError)
{
    return BadRequest(validationError.Errors);
}

// DON'T
var success = result as SuccessResult;
if (success != null)
{
    return Ok(success.Value);
}
```

---

## LINQ Best Practices

### Method Syntax Over Query Syntax

Prefer method syntax for most queries. Use query syntax only when it significantly improves readability (e.g., multiple joins, let clauses).

```csharp
// DO - Method syntax for simple queries
var activeOrders = orders
    .Where(o => o.Status == OrderStatus.Active)
    .OrderByDescending(o => o.CreatedAt)
    .Select(o => new OrderSummary(o.Id, o.CustomerName, o.TotalAmount))
    .ToList();

// DO - Query syntax when it's clearer (complex joins)
var orderDetails = from order in orders
                   join customer in customers on order.CustomerId equals customer.Id
                   join product in products on order.ProductId equals product.Id
                   let discount = customer.IsPremium ? 0.1m : 0m
                   select new { order.Id, customer.Name, product.Title, discount };
```

### Understand Deferred Execution

Materialize queries (`.ToList()`, `.ToArray()`) when you need to iterate multiple times or when you want to capture the result at a point in time.

```csharp
// DO - Materialize when iterating multiple times
var validOrders = orders.Where(o => o.IsValid).ToList();
var count = validOrders.Count;
var first = validOrders.FirstOrDefault();

// DON'T - Query executes twice (or more)
var validOrders = orders.Where(o => o.IsValid); // deferred
var count = validOrders.Count();       // executes query
var first = validOrders.FirstOrDefault(); // executes query again
```

### Avoid Side Effects in LINQ

LINQ expressions should be pure. Do not mutate state inside `Select`, `Where`, or other operators.

```csharp
// DON'T
var results = orders.Select(o =>
{
    o.Status = OrderStatus.Processed; // MUTATING inside Select -- BAD
    return o;
}).ToList();

// DO
foreach (var order in orders)
{
    order.Status = OrderStatus.Processed;
}
```

### Prefer FirstOrDefault Over Single When Appropriate

Use `Single`/`SingleOrDefault` only when exactly one match is a business rule. Use `First`/`FirstOrDefault` when you just want the first match.

```csharp
// DO - When expecting zero or one match by unique key
var user = await dbContext.Users.SingleOrDefaultAsync(u => u.Email == email, cancellationToken);

// DO - When expecting zero or many but only need the first
var latestOrder = await dbContext.Orders
    .Where(o => o.CustomerId == customerId)
    .OrderByDescending(o => o.CreatedAt)
    .FirstOrDefaultAsync(cancellationToken);
```

---

## Async/Await Patterns

### Always Use CancellationToken

Accept `CancellationToken` as the last parameter on all async methods. Default it to `default` at the boundary.

```csharp
// DO
public async Task<Order> GetOrderAsync(Guid id, CancellationToken cancellationToken = default)
{
    return await _dbContext.Orders
        .Include(o => o.Lines)
        .FirstOrDefaultAsync(o => o.Id == id, cancellationToken)
        ?? throw new NotFoundException($"Order {id} not found.");
}

// DON'T
public async Task<Order> GetOrderAsync(Guid id)  // missing CancellationToken
{
    return await _dbContext.Orders.FirstOrDefaultAsync(o => o.Id == id);
}
```

### ConfigureAwait

In library code, use `ConfigureAwait(false)`. In ASP.NET Core application code (controllers, services), it is NOT necessary because ASP.NET Core has no `SynchronizationContext`.

```csharp
// DO - Library code
public async Task<string> ReadFileAsync(string path, CancellationToken cancellationToken = default)
{
    var content = await File.ReadAllTextAsync(path, cancellationToken).ConfigureAwait(false);
    return content;
}

// DO - ASP.NET Core application code (ConfigureAwait not needed)
public async Task<Order> GetOrderAsync(Guid id, CancellationToken cancellationToken = default)
{
    var order = await _orderRepository.GetByIdAsync(id, cancellationToken);
    return order;
}
```

### Avoid Async Void

Never use `async void` except for event handlers. Use `async Task` instead.

```csharp
// DO
public async Task ProcessOrderAsync(Order order, CancellationToken cancellationToken = default)
{
    // ...
}

// DON'T
public async void ProcessOrder(Order order) // exceptions will be unobserved!
{
    // ...
}
```

### ValueTask

Use `ValueTask` when a method frequently returns synchronously (e.g., cached results). In most cases, `Task` is fine.

```csharp
// DO - Method often returns cached value
public ValueTask<Product?> GetProductAsync(Guid id, CancellationToken cancellationToken = default)
{
    if (_cache.TryGetValue(id, out Product? product))
    {
        return ValueTask.FromResult(product);
    }

    return new ValueTask<Product?>(LoadProductFromDatabaseAsync(id, cancellationToken));
}
```

### Do Not Block on Async Code

Never call `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` on a `Task`.

```csharp
// DO
var order = await GetOrderAsync(id, cancellationToken);

// DON'T
var order = GetOrderAsync(id).Result;           // deadlock risk
var order = GetOrderAsync(id).GetAwaiter().GetResult(); // still blocking
GetOrderAsync(id).Wait();                       // deadlock risk
```

---

## ASP.NET Core Conventions

### Minimal APIs vs Controllers

Use **Minimal APIs** for simple, resource-oriented endpoints. Use **Controllers** when you need complex routing, filters, or model binding behaviors.

```csharp
// DO - Minimal API for a simple CRUD resource
var group = app.MapGroup("/api/orders").WithTags("Orders");

group.MapGet("/", async (IOrderService orderService, CancellationToken cancellationToken) =>
    Results.Ok(await orderService.GetAllAsync(cancellationToken)));

group.MapGet("/{id:guid}", async (Guid id, IOrderService orderService, CancellationToken cancellationToken) =>
    await orderService.GetByIdAsync(id, cancellationToken) is { } order
        ? Results.Ok(order)
        : Results.NotFound());

group.MapPost("/", async (CreateOrderRequest request, IOrderService orderService, CancellationToken cancellationToken) =>
{
    var order = await orderService.CreateAsync(request, cancellationToken);
    return Results.Created($"/api/orders/{order.Id}", order);
});
```

```csharp
// DO - Controller for complex scenarios
[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class OrdersController : ControllerBase
{
    private readonly IMediator _mediator;

    public OrdersController(IMediator mediator)
    {
        _mediator = mediator;
    }

    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(OrderResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(Guid id, CancellationToken cancellationToken)
    {
        var result = await _mediator.Send(new GetOrderQuery(id), cancellationToken);
        return result.Match<IActionResult>(
            success => Ok(success),
            notFound => NotFound());
    }
}
```

### Middleware Order

Register middleware in the correct order. The order matters for security and functionality.

```csharp
var app = builder.Build();

// 1. Exception handling (outermost)
app.UseExceptionHandler("/error");

// 2. HSTS (production only)
if (!app.Environment.IsDevelopment())
{
    app.UseHsts();
}

// 3. HTTPS redirection
app.UseHttpsRedirection();

// 4. Static files (if applicable)
app.UseStaticFiles();

// 5. Routing
app.UseRouting();

// 6. CORS (must be between UseRouting and UseAuthorization)
app.UseCors();

// 7. Rate limiting
app.UseRateLimiter();

// 8. Authentication
app.UseAuthentication();

// 9. Authorization
app.UseAuthorization();

// 10. Custom middleware

// 11. Endpoints
app.MapControllers();
```

### Route Naming

Use lowercase, kebab-case routes. Prefer plural nouns for resources.

```csharp
// DO
[Route("api/order-items")]
[Route("api/v{version:apiVersion}/orders")]

// DON'T
[Route("api/OrderItems")]   // PascalCase
[Route("api/getOrders")]    // verb in route
[Route("api/order_items")]  // snake_case
```

---

## Dependency Injection

### Lifetime Scopes

Choose the correct lifetime for each service registration.

| Lifetime | Use When | Examples |
|-----------|----------|----------|
| **Transient** | Lightweight, stateless services | Validators, mappers, factories |
| **Scoped** | Per-request state; database contexts | `DbContext`, `IUnitOfWork`, request-scoped services |
| **Singleton** | Thread-safe, shared state; expensive to create | `HttpClient` (via `IHttpClientFactory`), caches, configuration |

```csharp
// DO
builder.Services.AddScoped<IOrderRepository, OrderRepository>();
builder.Services.AddScoped<IOrderService, OrderService>();
builder.Services.AddTransient<IValidator<CreateOrderRequest>, CreateOrderRequestValidator>();
builder.Services.AddSingleton<ICacheService, MemoryCacheService>();

// DON'T - Captive dependency (singleton depends on scoped)
builder.Services.AddSingleton<IOrderService, OrderService>(); // OrderService depends on scoped DbContext!
```

### Registration Patterns

Use extension methods to group related registrations.

```csharp
// DO
public static class OrdersServiceExtensions
{
    public static IServiceCollection AddOrdersModule(this IServiceCollection services)
    {
        services.AddScoped<IOrderRepository, OrderRepository>();
        services.AddScoped<IOrderService, OrderService>();
        services.AddTransient<IValidator<CreateOrderRequest>, CreateOrderRequestValidator>();
        return services;
    }
}

// In Program.cs
builder.Services.AddOrdersModule();
```

### Constructor Injection Only

Always use constructor injection. Avoid `[FromServices]` in controller actions (except Minimal APIs where it is the norm) and never use the service locator pattern.

```csharp
// DO
public class OrderService : IOrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly ILogger<OrderService> _logger;

    public OrderService(IOrderRepository orderRepository, ILogger<OrderService> logger)
    {
        _orderRepository = orderRepository;
        _logger = logger;
    }
}

// DON'T
public class OrderService : IOrderService
{
    private readonly IServiceProvider _serviceProvider;

    public OrderService(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider; // service locator anti-pattern
    }

    public void DoWork()
    {
        var repo = _serviceProvider.GetRequiredService<IOrderRepository>();
    }
}
```

---

## Entity Framework Core

### DbContext Configuration

Keep `DbContext` lean. Configure entities in separate `IEntityTypeConfiguration<T>` classes.

```csharp
// DO
public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<Order> Orders => Set<Order>();
    public DbSet<Customer> Customers => Set<Customer>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly);
    }
}

// Separate configuration file: OrderConfiguration.cs
public class OrderConfiguration : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> builder)
    {
        builder.HasKey(o => o.Id);
        builder.Property(o => o.CustomerName).HasMaxLength(200).IsRequired();
        builder.HasMany(o => o.Lines).WithOne().HasForeignKey(l => l.OrderId);
        builder.HasIndex(o => o.CreatedAt);
    }
}
```

### Migrations

- Name migrations descriptively: `AddOrderStatusColumn`, `CreateCustomerTable`
- Always review generated migration code before applying
- Never edit applied migrations
- Include both `Up` and `Down` methods

```bash
# DO
dotnet ef migrations add AddOrderStatusColumn
dotnet ef database update

# DON'T
dotnet ef migrations add Migration1  # meaningless name
```

### Query Optimization

- Use `AsNoTracking()` for read-only queries
- Use projections (`Select`) to fetch only needed columns
- Avoid loading entire entities when you only need a subset
- Use `Include`/`ThenInclude` intentionally -- never eagerly load everything

```csharp
// DO - Projection for read-only
var orderSummaries = await _dbContext.Orders
    .AsNoTracking()
    .Where(o => o.CustomerId == customerId)
    .Select(o => new OrderSummaryResponse
    {
        Id = o.Id,
        TotalAmount = o.TotalAmount,
        Status = o.Status.ToString(),
        CreatedAt = o.CreatedAt
    })
    .ToListAsync(cancellationToken);

// DON'T - Loading entire entity graph
var orders = await _dbContext.Orders
    .Include(o => o.Lines)
        .ThenInclude(l => l.Product)
            .ThenInclude(p => p.Category)
    .Include(o => o.Customer)
        .ThenInclude(c => c.Addresses)
    .ToListAsync(cancellationToken);
```

### Split Queries

Use `AsSplitQuery()` when loading collections to avoid cartesian explosion.

```csharp
// DO - Split query for collection includes
var order = await _dbContext.Orders
    .Include(o => o.Lines)
    .Include(o => o.Payments)
    .AsSplitQuery()
    .FirstOrDefaultAsync(o => o.Id == orderId, cancellationToken);
```

---

## Configuration and Options Pattern

### Use the Options Pattern

Bind configuration sections to strongly typed classes. Never read `IConfiguration` directly in services.

```csharp
// DO - Options class
public class EmailOptions
{
    public const string SectionName = "Email";

    public required string SmtpHost { get; init; }
    public required int SmtpPort { get; init; }
    public required string FromAddress { get; init; }
    public int TimeoutSeconds { get; init; } = 30;
}

// Registration
builder.Services.Configure<EmailOptions>(builder.Configuration.GetSection(EmailOptions.SectionName));

// Usage via IOptions<T>
public class EmailService
{
    private readonly EmailOptions _options;

    public EmailService(IOptions<EmailOptions> options)
    {
        _options = options.Value;
    }
}
```

### IOptions vs IOptionsSnapshot vs IOptionsMonitor

| Type | Lifetime | Reloads on Change |
|------|----------|-------------------|
| `IOptions<T>` | Singleton | No |
| `IOptionsSnapshot<T>` | Scoped | Yes (per request) |
| `IOptionsMonitor<T>` | Singleton | Yes (via callback) |

```csharp
// DO - Use IOptionsSnapshot for settings that may change at runtime
public class FeatureFlagService
{
    private readonly FeatureFlags _flags;

    public FeatureFlagService(IOptionsSnapshot<FeatureFlags> flags)
    {
        _flags = flags.Value;
    }
}
```

### Validation at Startup

Validate options at startup to fail fast.

```csharp
builder.Services.AddOptions<EmailOptions>()
    .BindConfiguration(EmailOptions.SectionName)
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

---

## Exception Handling

### Custom Exception Types

Create custom exceptions for distinct error categories. Derive from `Exception`, not `ApplicationException`.

```csharp
// DO
public class NotFoundException : Exception
{
    public string ResourceType { get; }
    public object ResourceId { get; }

    public NotFoundException(string resourceType, object resourceId)
        : base($"{resourceType} with id '{resourceId}' was not found.")
    {
        ResourceType = resourceType;
        ResourceId = resourceId;
    }
}

public class ConflictException : Exception
{
    public ConflictException(string message) : base(message) { }
}

public class ValidationException : Exception
{
    public IReadOnlyDictionary<string, string[]> Errors { get; }

    public ValidationException(IReadOnlyDictionary<string, string[]> errors)
        : base("One or more validation errors occurred.")
    {
        Errors = errors;
    }
}
```

### Global Exception Handler

Use ASP.NET Core's `IExceptionHandler` (available in .NET 8+) to map exceptions to ProblemDetails.

```csharp
public class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger;

    public GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
    {
        _logger = logger;
    }

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        var (statusCode, title) = exception switch
        {
            NotFoundException => (StatusCodes.Status404NotFound, "Not Found"),
            ConflictException => (StatusCodes.Status409Conflict, "Conflict"),
            ValidationException => (StatusCodes.Status422UnprocessableEntity, "Validation Error"),
            UnauthorizedAccessException => (StatusCodes.Status401Unauthorized, "Unauthorized"),
            _ => (StatusCodes.Status500InternalServerError, "Internal Server Error")
        };

        _logger.LogError(exception, "Unhandled exception: {Message}", exception.Message);

        httpContext.Response.StatusCode = statusCode;
        await httpContext.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = statusCode,
            Title = title,
            Detail = exception.Message,
            Instance = httpContext.Request.Path
        }, cancellationToken);

        return true;
    }
}

// Registration
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

app.UseExceptionHandler();
```

---

## Logging

### Use ILogger<T>

Always inject `ILogger<T>` where `T` is the containing class. Never use `ILoggerFactory` directly in services.

```csharp
// DO
public class OrderService
{
    private readonly ILogger<OrderService> _logger;

    public OrderService(ILogger<OrderService> logger)
    {
        _logger = logger;
    }

    public async Task ProcessOrderAsync(Order order, CancellationToken cancellationToken)
    {
        _logger.LogInformation("Processing order {OrderId} for customer {CustomerId}",
            order.Id, order.CustomerId);
    }
}
```

### Structured Logging

Always use structured logging with message templates. Never use string interpolation in log messages.

```csharp
// DO - Structured logging with named placeholders
_logger.LogInformation("Order {OrderId} created for customer {CustomerName} with total {TotalAmount}",
    order.Id, order.CustomerName, order.TotalAmount);

// DON'T - String interpolation (loses structure for log aggregation)
_logger.LogInformation($"Order {order.Id} created for customer {order.CustomerName}");

// DON'T - String concatenation
_logger.LogInformation("Order " + order.Id + " created");
```

### Log Levels

| Level | Use For |
|-------|---------|
| `Trace` | Detailed diagnostic information (method entry/exit) |
| `Debug` | Development-time diagnostics |
| `Information` | Business events (order created, user logged in) |
| `Warning` | Abnormal or unexpected events that don't cause failure |
| `Error` | Errors that affect the current operation but not the application |
| `Critical` | Unrecoverable errors that require immediate attention |

```csharp
_logger.LogDebug("Querying orders with filter {Filter}", filter);
_logger.LogInformation("Order {OrderId} shipped to {Address}", orderId, address);
_logger.LogWarning("Payment retry {RetryCount} for order {OrderId}", retryCount, orderId);
_logger.LogError(exception, "Failed to process order {OrderId}", orderId);
_logger.LogCritical("Database connection lost. Connection string: [REDACTED]");
```

### High-Performance Logging

For hot paths, use `LoggerMessage.Define` or the source generator approach to avoid boxing and allocation.

```csharp
// DO - Source generator (C# 12+ / .NET 8+)
public static partial class LogMessages
{
    [LoggerMessage(Level = LogLevel.Information, Message = "Order {OrderId} created for customer {CustomerId}")]
    public static partial void OrderCreated(ILogger logger, Guid orderId, Guid customerId);

    [LoggerMessage(Level = LogLevel.Error, Message = "Failed to process order {OrderId}")]
    public static partial void OrderProcessingFailed(ILogger logger, Guid orderId, Exception exception);
}

// Usage
LogMessages.OrderCreated(_logger, order.Id, order.CustomerId);
```

---

## API Design

### RESTful Conventions

Follow standard HTTP methods and status codes.

| Method | Route | Purpose | Success Status |
|--------|-------|---------|----------------|
| `GET` | `/api/orders` | List orders | 200 OK |
| `GET` | `/api/orders/{id}` | Get single order | 200 OK |
| `POST` | `/api/orders` | Create order | 201 Created |
| `PUT` | `/api/orders/{id}` | Full update | 200 OK or 204 No Content |
| `PATCH` | `/api/orders/{id}` | Partial update | 200 OK |
| `DELETE` | `/api/orders/{id}` | Delete order | 204 No Content |

### API Versioning

Use URL-based versioning as the primary strategy.

```csharp
// DO
builder.Services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;
    options.ApiVersionReader = new UrlSegmentApiVersionReader();
});

[ApiController]
[Route("api/v{version:apiVersion}/orders")]
[ApiVersion("1.0")]
public class OrdersV1Controller : ControllerBase { }

[ApiController]
[Route("api/v{version:apiVersion}/orders")]
[ApiVersion("2.0")]
public class OrdersV2Controller : ControllerBase { }
```

### Pagination

Always paginate list endpoints. Use cursor-based or offset-based pagination.

```csharp
// DO - Pagination request
public record PaginationRequest(int Page = 1, int PageSize = 20)
{
    public int Page { get; init; } = Page < 1 ? 1 : Page;
    public int PageSize { get; init; } = PageSize > 100 ? 100 : (PageSize < 1 ? 20 : PageSize);
}

// DO - Paginated response
public record PaginatedResponse<T>(
    IReadOnlyList<T> Items,
    int Page,
    int PageSize,
    int TotalCount,
    int TotalPages);

// Usage in repository
public async Task<PaginatedResponse<OrderSummary>> GetOrdersAsync(
    PaginationRequest pagination,
    CancellationToken cancellationToken = default)
{
    var query = _dbContext.Orders.AsNoTracking();

    var totalCount = await query.CountAsync(cancellationToken);
    var items = await query
        .OrderByDescending(o => o.CreatedAt)
        .Skip((pagination.Page - 1) * pagination.PageSize)
        .Take(pagination.PageSize)
        .Select(o => new OrderSummary(o.Id, o.CustomerName, o.TotalAmount, o.CreatedAt))
        .ToListAsync(cancellationToken);

    return new PaginatedResponse<OrderSummary>(
        items, pagination.Page, pagination.PageSize, totalCount,
        (int)Math.Ceiling(totalCount / (double)pagination.PageSize));
}
```

### Filtering and Sorting

Accept filter and sort parameters as query strings. Validate all filter values.

```csharp
// DO
public record OrderFilterRequest
{
    public OrderStatus? Status { get; init; }
    public DateTime? FromDate { get; init; }
    public DateTime? ToDate { get; init; }
    public string? CustomerName { get; init; }
    public string? SortBy { get; init; } = "createdAt";
    public string? SortDirection { get; init; } = "desc";
}

// GET /api/orders?status=Shipped&fromDate=2024-01-01&sortBy=totalAmount&sortDirection=asc
```

---

## Model Validation

### FluentValidation (Preferred)

Use FluentValidation for complex validation rules. Register validators automatically.

```csharp
// DO
public class CreateOrderRequestValidator : AbstractValidator<CreateOrderRequest>
{
    public CreateOrderRequestValidator()
    {
        RuleFor(x => x.CustomerName)
            .NotEmpty().WithMessage("Customer name is required.")
            .MaximumLength(200).WithMessage("Customer name must not exceed 200 characters.");

        RuleFor(x => x.Lines)
            .NotEmpty().WithMessage("Order must contain at least one line.");

        RuleForEach(x => x.Lines).SetValidator(new OrderLineRequestValidator());
    }
}

public class OrderLineRequestValidator : AbstractValidator<OrderLineRequest>
{
    public OrderLineRequestValidator()
    {
        RuleFor(x => x.ProductId).NotEmpty();
        RuleFor(x => x.Quantity).GreaterThan(0).LessThanOrEqualTo(999);
        RuleFor(x => x.UnitPrice).GreaterThan(0);
    }
}

// Registration
builder.Services.AddValidatorsFromAssemblyContaining<CreateOrderRequestValidator>();
```

### DataAnnotations (Simple Cases)

Use DataAnnotations for simple DTOs where FluentValidation is overkill.

```csharp
// DO - Simple request DTO
public class UpdateProfileRequest
{
    [Required]
    [StringLength(100, MinimumLength = 2)]
    public required string DisplayName { get; init; }

    [EmailAddress]
    public string? Email { get; init; }

    [Phone]
    public string? PhoneNumber { get; init; }
}
```

---

## DTO Mapping

### Manual Mapping (Preferred for Small Projects)

Use extension methods for explicit, debuggable mapping.

```csharp
// DO
public static class OrderMappingExtensions
{
    public static OrderResponse ToResponse(this Order order) => new(
        Id: order.Id,
        CustomerName: order.CustomerName,
        TotalAmount: order.Lines.Sum(l => l.Price * l.Quantity),
        Status: order.Status.ToString(),
        CreatedAt: order.CreatedAt,
        Lines: order.Lines.Select(l => l.ToResponse()).ToList());

    public static OrderLineResponse ToResponse(this OrderLine line) => new(
        ProductName: line.ProductName,
        Quantity: line.Quantity,
        UnitPrice: line.Price,
        LineTotal: line.Price * line.Quantity);
}
```

### AutoMapper (Larger Projects)

When using AutoMapper, define explicit profiles. Never rely on convention-based mapping for complex scenarios.

```csharp
// DO
public class OrderMappingProfile : Profile
{
    public OrderMappingProfile()
    {
        CreateMap<Order, OrderResponse>()
            .ForMember(dest => dest.TotalAmount,
                opt => opt.MapFrom(src => src.Lines.Sum(l => l.Price * l.Quantity)))
            .ForMember(dest => dest.Status,
                opt => opt.MapFrom(src => src.Status.ToString()));

        CreateMap<OrderLine, OrderLineResponse>()
            .ForMember(dest => dest.LineTotal,
                opt => opt.MapFrom(src => src.Price * src.Quantity));
    }
}

// Registration
builder.Services.AddAutoMapper(typeof(OrderMappingProfile).Assembly);
```

---

## Background Services

### IHostedService and BackgroundService

Use `BackgroundService` for long-running background tasks. Use `IHostedService` for startup/shutdown hooks.

```csharp
// DO - Long-running background worker
public class OrderProcessingWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<OrderProcessingWorker> _logger;

    public OrderProcessingWorker(
        IServiceScopeFactory scopeFactory,
        ILogger<OrderProcessingWorker> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Order processing worker started.");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = _scopeFactory.CreateScope();
                var processor = scope.ServiceProvider.GetRequiredService<IOrderProcessor>();
                await processor.ProcessPendingOrdersAsync(stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                _logger.LogError(ex, "Error processing orders. Retrying in 30 seconds.");
            }

            await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken);
        }
    }
}

// Registration
builder.Services.AddHostedService<OrderProcessingWorker>();
```

Important: Always create a new scope inside background services. The `BackgroundService` is a singleton, so scoped services (like `DbContext`) must be resolved from a new scope.

---

## Health Checks

### Implement Health Checks for All External Dependencies

```csharp
// DO
builder.Services.AddHealthChecks()
    .AddDbContextCheck<AppDbContext>("database")
    .AddRedis(builder.Configuration.GetConnectionString("Redis")!, "redis")
    .AddUrlGroup(new Uri("https://api.payment-gateway.com/health"), "payment-gateway")
    .AddCheck<CustomHealthCheck>("custom-check");

app.MapHealthChecks("/health", new HealthCheckOptions
{
    ResponseWriter = UIResponseWriter.WriteHealthCheckUIResponse
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});

app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false // liveness: just checks the app is running
});
```

### Custom Health Checks

```csharp
public class CustomHealthCheck : IHealthCheck
{
    private readonly IExternalService _externalService;

    public CustomHealthCheck(IExternalService externalService)
    {
        _externalService = externalService;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var isHealthy = await _externalService.PingAsync(cancellationToken);
            return isHealthy
                ? HealthCheckResult.Healthy("External service is reachable.")
                : HealthCheckResult.Degraded("External service is slow.");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("External service is unreachable.", ex);
        }
    }
}
```

---

## Caching Patterns

### IMemoryCache for Single-Instance

```csharp
// DO
public class ProductCacheService
{
    private readonly IMemoryCache _cache;
    private readonly IProductRepository _repository;
    private static readonly TimeSpan CacheDuration = TimeSpan.FromMinutes(10);

    public ProductCacheService(IMemoryCache cache, IProductRepository repository)
    {
        _cache = cache;
        _repository = repository;
    }

    public async Task<Product?> GetProductAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var cacheKey = $"product:{id}";
        if (_cache.TryGetValue(cacheKey, out Product? product))
        {
            return product;
        }

        product = await _repository.GetByIdAsync(id, cancellationToken);

        if (product is not null)
        {
            _cache.Set(cacheKey, product, new MemoryCacheEntryOptions
            {
                AbsoluteExpirationRelativeToNow = CacheDuration,
                SlidingExpiration = TimeSpan.FromMinutes(2)
            });
        }

        return product;
    }
}
```

### IDistributedCache for Multi-Instance

```csharp
// DO
public class DistributedProductCacheService
{
    private readonly IDistributedCache _cache;
    private readonly IProductRepository _repository;

    public async Task<Product?> GetProductAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var cacheKey = $"product:{id}";
        var cached = await _cache.GetStringAsync(cacheKey, cancellationToken);

        if (cached is not null)
        {
            return JsonSerializer.Deserialize<Product>(cached);
        }

        var product = await _repository.GetByIdAsync(id, cancellationToken);

        if (product is not null)
        {
            await _cache.SetStringAsync(cacheKey,
                JsonSerializer.Serialize(product),
                new DistributedCacheEntryOptions
                {
                    AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(10)
                },
                cancellationToken);
        }

        return product;
    }
}
```

---

## Response Compression and Performance

### Enable Response Compression

```csharp
builder.Services.AddResponseCompression(options =>
{
    options.EnableForHttps = true;
    options.Providers.Add<BrotliCompressionProvider>();
    options.Providers.Add<GzipCompressionProvider>();
    options.MimeTypes = ResponseCompressionDefaults.MimeTypes.Concat(new[]
    {
        "application/json",
        "application/xml",
        "text/plain"
    });
});

builder.Services.Configure<BrotliCompressionProviderOptions>(options =>
{
    options.Level = CompressionLevel.Fastest;
});

app.UseResponseCompression();
```

### Output Caching (.NET 7+)

```csharp
builder.Services.AddOutputCache(options =>
{
    options.AddBasePolicy(builder => builder.Expire(TimeSpan.FromMinutes(5)));
    options.AddPolicy("ProductList", builder =>
        builder.Expire(TimeSpan.FromMinutes(10))
               .Tag("products"));
});

app.UseOutputCache();

// Usage
app.MapGet("/api/products", async (IProductService service, CancellationToken ct) =>
    Results.Ok(await service.GetAllAsync(ct)))
    .CacheOutput("ProductList");
```

### Performance Best Practices

- Use `System.Text.Json` instead of `Newtonsoft.Json` for serialization
- Use `ReadOnlySpan<T>` and `Memory<T>` for high-performance string and buffer operations
- Pool objects with `ObjectPool<T>` for frequently allocated objects
- Use `ArrayPool<T>.Shared` for temporary buffers
- Enable HTTP/2 and HTTP/3
- Use `IAsyncEnumerable<T>` for streaming large datasets

```csharp
// DO - Streaming large results
[HttpGet("export")]
public async IAsyncEnumerable<OrderResponse> ExportOrders(
    [EnumeratorCancellation] CancellationToken cancellationToken)
{
    await foreach (var order in _orderRepository.StreamAllAsync(cancellationToken))
    {
        yield return order.ToResponse();
    }
}
```

### JSON Serialization Configuration

```csharp
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.CamelCase));
    options.SerializerOptions.ReferenceHandler = ReferenceHandler.IgnoreCycles;
});
```

---

## Summary Checklist

Before generating or reviewing .NET code, verify:

- [ ] Nullable reference types are enabled
- [ ] All naming follows C# conventions (PascalCase, _camelCase, etc.)
- [ ] File-scoped namespaces match folder structure
- [ ] One type per file
- [ ] All public members have XML documentation
- [ ] Async methods accept `CancellationToken` and are suffixed with `Async`
- [ ] No blocking calls (`.Result`, `.Wait()`)
- [ ] Dependency injection uses correct lifetimes
- [ ] EF Core queries use `AsNoTracking()` for reads and projections where possible
- [ ] Configuration uses the Options pattern with validation
- [ ] Exceptions are handled globally with ProblemDetails
- [ ] Logging uses structured message templates
- [ ] APIs follow RESTful conventions with pagination
- [ ] Validation uses FluentValidation or DataAnnotations
- [ ] Background services create their own DI scopes
- [ ] Health checks cover all external dependencies
- [ ] Response compression is enabled
