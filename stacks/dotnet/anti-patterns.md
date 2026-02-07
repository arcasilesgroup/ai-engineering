# .NET Anti-Patterns

Never generate code that uses these anti-patterns. When you encounter them in existing code, refactor toward the correct approach. Each section explains what is wrong, why, and what to do instead.

---

## Service Locator

Injecting `IServiceProvider` and resolving services manually hides dependencies, makes code untestable, and defeats the purpose of dependency injection.

```csharp
// DON'T - Service locator
public class OrderService
{
    private readonly IServiceProvider _serviceProvider;

    public OrderService(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    public async Task ProcessAsync(Guid orderId, CancellationToken cancellationToken)
    {
        var repository = _serviceProvider.GetRequiredService<IOrderRepository>();
        var logger = _serviceProvider.GetRequiredService<ILogger<OrderService>>();
        // Dependencies are hidden -- caller has no idea what this class needs
    }
}
```

```csharp
// DO - Constructor injection
public class OrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly ILogger<OrderService> _logger;

    public OrderService(IOrderRepository orderRepository, ILogger<OrderService> logger)
    {
        _orderRepository = orderRepository;
        _logger = logger;
    }

    public async Task ProcessAsync(Guid orderId, CancellationToken cancellationToken)
    {
        // Dependencies are explicit, testable, and visible in the constructor
    }
}
```

The only exception is `BackgroundService` or factory classes that need to create scopes for scoped services.

---

## Anemic Domain Models

An anemic domain model is a class that holds data but no behavior. All logic lives in external services, turning the model into a dumb data bag. This leads to scattered business rules and duplicated logic.

```csharp
// DON'T - Anemic model with external service doing all the work
public class Order
{
    public Guid Id { get; set; }
    public OrderStatus Status { get; set; }
    public List<OrderLine> Lines { get; set; } = new();
    public decimal TotalAmount { get; set; }
}

public class OrderService
{
    public void ConfirmOrder(Order order)
    {
        if (order.Status != OrderStatus.Pending)
            throw new InvalidOperationException("Only pending orders can be confirmed.");
        if (order.Lines.Count == 0)
            throw new InvalidOperationException("Cannot confirm order with no lines.");

        order.Status = OrderStatus.Confirmed;
        order.TotalAmount = order.Lines.Sum(l => l.Price * l.Quantity);
    }
}
```

```csharp
// DO - Rich domain model with behavior
public class Order
{
    public Guid Id { get; private set; }
    public OrderStatus Status { get; private set; }
    public decimal TotalAmount { get; private set; }

    private readonly List<OrderLine> _lines = new();
    public IReadOnlyCollection<OrderLine> Lines => _lines.AsReadOnly();

    public void Confirm()
    {
        if (Status != OrderStatus.Pending)
            throw new InvalidOperationException("Only pending orders can be confirmed.");
        if (_lines.Count == 0)
            throw new InvalidOperationException("Cannot confirm order with no lines.");

        Status = OrderStatus.Confirmed;
    }

    public void AddLine(Guid productId, string name, int quantity, decimal unitPrice)
    {
        if (Status != OrderStatus.Pending)
            throw new InvalidOperationException("Cannot modify a non-pending order.");

        _lines.Add(new OrderLine(productId, name, quantity, unitPrice));
        RecalculateTotal();
    }

    private void RecalculateTotal()
    {
        TotalAmount = _lines.Sum(l => l.UnitPrice * l.Quantity);
    }
}
```

---

## God Classes

A god class handles too many responsibilities. It grows indefinitely, becomes impossible to test, and changes for many unrelated reasons.

```csharp
// DON'T - God class doing everything
public class OrderManager
{
    public async Task<Order> CreateOrderAsync(/* ... */) { /* creates orders */ }
    public async Task SendConfirmationEmailAsync(/* ... */) { /* sends emails */ }
    public async Task CalculateTaxAsync(/* ... */) { /* tax calculation */ }
    public async Task GenerateInvoicePdfAsync(/* ... */) { /* PDF generation */ }
    public async Task UpdateInventoryAsync(/* ... */) { /* inventory management */ }
    public async Task ProcessPaymentAsync(/* ... */) { /* payment processing */ }
    public async Task NotifyWarehouseAsync(/* ... */) { /* warehouse notification */ }
    // 2000 more lines...
}
```

```csharp
// DO - Single Responsibility: one class per concern
public class OrderService { /* creates and manages orders */ }
public class EmailService { /* sends emails */ }
public class TaxCalculator { /* calculates tax */ }
public class InvoiceGenerator { /* generates PDFs */ }
public class InventoryService { /* manages inventory */ }
public class PaymentService { /* processes payments */ }
public class WarehouseNotifier { /* notifies warehouse */ }
```

If a class has more than 5-7 injected dependencies, it is doing too much. Split it.

---

## Catching Generic Exception

Catching `Exception` swallows all errors, including `OutOfMemoryException`, `StackOverflowException`, and `ThreadAbortException`. It hides bugs and makes debugging impossible.

```csharp
// DON'T - Catching everything
try
{
    await ProcessOrderAsync(order, cancellationToken);
}
catch (Exception ex)
{
    _logger.LogError(ex, "Something went wrong");
    // Swallowed: was it a network error? A null reference? A business rule violation?
}
```

```csharp
// DO - Catch specific exceptions
try
{
    await ProcessOrderAsync(order, cancellationToken);
}
catch (HttpRequestException ex) when (ex.StatusCode == HttpStatusCode.ServiceUnavailable)
{
    _logger.LogWarning(ex, "Payment gateway unavailable for order {OrderId}. Will retry.", order.Id);
    await ScheduleRetryAsync(order, cancellationToken);
}
catch (ValidationException ex)
{
    _logger.LogWarning("Validation failed for order {OrderId}: {Errors}", order.Id, ex.Errors);
    throw; // Let the global handler return 422
}
// Let unexpected exceptions propagate to the global exception handler
```

Use exception filters (`when`) to narrow catches further.

---

## String Concatenation in Loops

String concatenation with `+` inside loops creates a new string object on every iteration, leading to O(n^2) memory allocation.

```csharp
// DON'T - O(n^2) string allocation
var result = "";
foreach (var line in orderLines)
{
    result += $"{line.ProductName}: {line.Quantity} x {line.UnitPrice}\n";
}
```

```csharp
// DO - StringBuilder for building strings in loops
var builder = new StringBuilder();
foreach (var line in orderLines)
{
    builder.AppendLine($"{line.ProductName}: {line.Quantity} x {line.UnitPrice}");
}
var result = builder.ToString();

// DO - String.Join for simple concatenation
var result = string.Join(Environment.NewLine,
    orderLines.Select(l => $"{l.ProductName}: {l.Quantity} x {l.UnitPrice}"));
```

---

## Synchronous Over Async (Sync-Over-Async)

Calling `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` on a `Task` blocks the calling thread. This can cause deadlocks, thread pool starvation, and severely degrade performance.

```csharp
// DON'T - Blocking on async code
public Order GetOrder(Guid id)
{
    return _orderRepository.GetByIdAsync(id).Result;  // DEADLOCK RISK
}

public void SendEmail(EmailMessage message)
{
    _emailService.SendAsync(message).Wait();  // BLOCKS THREAD
}

public string FetchData()
{
    return _httpClient.GetStringAsync("/api/data").GetAwaiter().GetResult();  // STILL BLOCKING
}
```

```csharp
// DO - Async all the way
public async Task<Order> GetOrderAsync(Guid id, CancellationToken cancellationToken = default)
{
    return await _orderRepository.GetByIdAsync(id, cancellationToken);
}

public async Task SendEmailAsync(EmailMessage message, CancellationToken cancellationToken = default)
{
    await _emailService.SendAsync(message, cancellationToken);
}
```

If you must call async from sync (e.g., `Main` method in a console app), use `async Task Main`.

---

## Static Abuse

Excessive use of static classes and methods creates hidden dependencies, makes unit testing impossible, and couples code tightly.

```csharp
// DON'T - Static helper used everywhere
public static class OrderHelper
{
    public static decimal CalculateDiscount(Order order)
    {
        var config = ConfigurationManager.AppSettings["DiscountRate"];  // hidden dependency
        return order.TotalAmount * decimal.Parse(config!);
    }
}

// Calling code -- impossible to mock or test in isolation
var discount = OrderHelper.CalculateDiscount(order);
```

```csharp
// DO - Injectable service
public interface IDiscountCalculator
{
    decimal Calculate(Order order);
}

public class DiscountCalculator : IDiscountCalculator
{
    private readonly DiscountOptions _options;

    public DiscountCalculator(IOptions<DiscountOptions> options)
    {
        _options = options.Value;
    }

    public decimal Calculate(Order order)
    {
        return order.TotalAmount * _options.Rate;
    }
}
```

Static methods are acceptable for:

- Pure utility functions with no dependencies (e.g., `Math.Round`, extension methods)
- Factory methods on domain objects (e.g., `Order.Create(...)`)

---

## Over-Abstracting (Interface for Every Class)

Creating an interface for every class "just in case" adds indirection without value. Only create interfaces when you need polymorphism, testability via mocking, or a dependency inversion boundary.

```csharp
// DON'T - Interface for a class with exactly one implementation and no testing need
public interface IEmailMessageBuilder
{
    EmailMessage Build(string to, string subject, string body);
}

public class EmailMessageBuilder : IEmailMessageBuilder
{
    public EmailMessage Build(string to, string subject, string body)
    {
        return new EmailMessage(to, subject, body);
    }
}
```

```csharp
// DO - Interface where it adds value (external dependency, multiple implementations, testability)
public interface IEmailSender  // Wraps an external SMTP service; needs mocking in tests
{
    Task SendAsync(EmailMessage message, CancellationToken cancellationToken = default);
}

// No interface needed for a pure in-process builder
public class EmailMessageBuilder
{
    public EmailMessage Build(string to, string subject, string body)
    {
        return new EmailMessage(to, subject, body);
    }
}
```

Rules for when to create an interface:

- The class wraps an external dependency (database, HTTP, file system, email)
- You have or plan to have multiple implementations
- You need to mock it in unit tests
- You are crossing an architectural boundary (e.g., Application -> Infrastructure)

---

## N+1 Queries in Entity Framework Core

Loading related entities inside a loop triggers one query per iteration instead of a single query with a join or include.

```csharp
// DON'T - N+1: one query per order to get lines
var orders = await _dbContext.Orders.ToListAsync(cancellationToken);
foreach (var order in orders)
{
    var lines = await _dbContext.OrderLines
        .Where(l => l.OrderId == order.Id)
        .ToListAsync(cancellationToken);
    // N additional queries!
}
```

```csharp
// DO - Eager loading with Include
var orders = await _dbContext.Orders
    .Include(o => o.Lines)
    .ToListAsync(cancellationToken);

// DO - Projection to avoid loading entire entity graph
var orderSummaries = await _dbContext.Orders
    .Select(o => new OrderSummary
    {
        Id = o.Id,
        CustomerName = o.CustomerName,
        LineCount = o.Lines.Count,
        TotalAmount = o.Lines.Sum(l => l.Price * l.Quantity)
    })
    .ToListAsync(cancellationToken);

// DO - Split query for multiple collection includes
var orders = await _dbContext.Orders
    .Include(o => o.Lines)
    .Include(o => o.Payments)
    .AsSplitQuery()
    .ToListAsync(cancellationToken);
```

---

## Mutable DTOs

DTOs that allow mutation after creation lead to defensive programming, accidental data corruption, and unclear ownership of data transformations.

```csharp
// DON'T - Mutable DTO
public class OrderResponse
{
    public Guid Id { get; set; }
    public string CustomerName { get; set; } = string.Empty;
    public decimal TotalAmount { get; set; }
    public string Status { get; set; } = string.Empty;
}

// Anywhere in the codebase, someone can silently modify the response:
response.TotalAmount = 0; // accidental or malicious mutation
```

```csharp
// DO - Immutable DTO using records
public record OrderResponse(
    Guid Id,
    string CustomerName,
    decimal TotalAmount,
    string Status,
    DateTime CreatedAt);

// Or init-only properties for classes
public class OrderResponse
{
    public required Guid Id { get; init; }
    public required string CustomerName { get; init; }
    public required decimal TotalAmount { get; init; }
    public required string Status { get; init; }
    public required DateTime CreatedAt { get; init; }
}
```

---

## Business Logic in Controllers

Controllers should only handle HTTP concerns: parsing requests, delegating to services, and formatting responses. Business rules in controllers are untestable without spinning up the full HTTP pipeline and become duplicated when the same logic is needed from another entry point.

```csharp
// DON'T - Business logic in controller
[HttpPost]
public async Task<IActionResult> CreateOrder(CreateOrderRequest request)
{
    if (request.Lines.Count == 0)
        return BadRequest("Order must have lines.");

    var customer = await _dbContext.Customers.FindAsync(request.CustomerId);
    if (customer == null)
        return NotFound("Customer not found.");

    if (customer.CreditLimit < request.Lines.Sum(l => l.Price * l.Quantity))
        return BadRequest("Exceeds credit limit.");

    var order = new Order
    {
        CustomerId = request.CustomerId,
        Status = OrderStatus.Pending,
        Lines = request.Lines.Select(l => new OrderLine
        {
            ProductId = l.ProductId,
            Quantity = l.Quantity,
            Price = l.Price
        }).ToList()
    };

    _dbContext.Orders.Add(order);
    await _dbContext.SaveChangesAsync();

    return Created($"/api/orders/{order.Id}", order);
}
```

```csharp
// DO - Controller delegates to service/handler
[HttpPost]
public async Task<IActionResult> CreateOrder(
    CreateOrderRequest request,
    CancellationToken cancellationToken)
{
    var result = await _mediator.Send(
        new CreateOrderCommand(request.CustomerId, request.Lines),
        cancellationToken);

    return result.Match<IActionResult>(
        orderId => Created($"/api/orders/{orderId}", new { id = orderId }),
        error => error.Code switch
        {
            "Customer.NotFound" => NotFound(error),
            "Customer.CreditLimitExceeded" => BadRequest(error),
            _ => BadRequest(error)
        });
}
```

---

## Other Anti-Patterns to Avoid

### Using `DateTime.Now` Directly

Inject `TimeProvider` (or `ISystemClock` pre-.NET 8) for testability.

```csharp
// DON'T
public class Order
{
    public DateTime CreatedAt { get; set; } = DateTime.Now; // untestable, uses local time
}

// DO
public class OrderService
{
    private readonly TimeProvider _timeProvider;

    public OrderService(TimeProvider timeProvider)
    {
        _timeProvider = timeProvider;
    }

    public Order Create()
    {
        return new Order { CreatedAt = _timeProvider.GetUtcNow().UtcDateTime };
    }
}
```

### Returning Null From Collections

Always return empty collections instead of null.

```csharp
// DON'T
public List<Order>? GetOrders() => hasOrders ? orders : null;

// DO
public IReadOnlyList<Order> GetOrders() => hasOrders ? orders : Array.Empty<Order>();
```

### Magic Strings and Numbers

Use constants, enums, or configuration for any value that has meaning.

```csharp
// DON'T
if (user.Role == "admin") { }
if (retryCount > 3) { }

// DO
if (user.Role == Roles.Admin) { }
if (retryCount > MaxRetryCount) { }
```

### Nested Try-Catch Blocks

Multiple nested try-catch blocks indicate poor error handling design. Consolidate or use the Result pattern.

```csharp
// DON'T
try
{
    try
    {
        try
        {
            await DoWorkAsync();
        }
        catch (IOException) { /* ... */ }
    }
    catch (HttpRequestException) { /* ... */ }
}
catch (Exception) { /* ... */ }

// DO - One try-catch or use Result pattern
try
{
    await DoWorkAsync();
}
catch (IOException ex)
{
    _logger.LogWarning(ex, "IO error during work.");
    throw new WorkFailedException("Failed due to IO error.", ex);
}
catch (HttpRequestException ex)
{
    _logger.LogWarning(ex, "HTTP error during work.");
    throw new WorkFailedException("Failed due to HTTP error.", ex);
}
```
