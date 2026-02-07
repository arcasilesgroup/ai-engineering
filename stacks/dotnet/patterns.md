# .NET Recommended Patterns

These are the architectural and design patterns to use when generating .NET code. Apply these patterns by default unless the developer explicitly chooses a different approach.

---

## Clean Architecture / Onion Architecture

### Layer Structure

Organize projects into four concentric layers. Inner layers never depend on outer layers.

```
src/
  MyApp.Domain/            # Innermost: entities, value objects, domain events, interfaces
  MyApp.Application/       # Use cases: commands, queries, handlers, DTOs, interfaces
  MyApp.Infrastructure/    # External concerns: EF Core, email, file storage, HTTP clients
  MyApp.Api/               # Outermost: controllers, middleware, Program.cs, DI wiring
```

### Dependency Rule

Dependencies point inward only.

```
Api --> Application --> Domain
Api --> Infrastructure --> Application --> Domain
```

```csharp
// Domain layer - ZERO external dependencies
// MyApp.Domain/Orders/IOrderRepository.cs
namespace MyApp.Domain.Orders;

public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task AddAsync(Order order, CancellationToken cancellationToken = default);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}
```

```csharp
// Application layer - depends only on Domain
// MyApp.Application/Orders/Commands/CreateOrder/CreateOrderHandler.cs
namespace MyApp.Application.Orders.Commands.CreateOrder;

public class CreateOrderHandler : IRequestHandler<CreateOrderCommand, Guid>
{
    private readonly IOrderRepository _orderRepository;

    public CreateOrderHandler(IOrderRepository orderRepository)
    {
        _orderRepository = orderRepository;
    }

    public async Task<Guid> Handle(CreateOrderCommand request, CancellationToken cancellationToken)
    {
        var order = Order.Create(request.CustomerId, request.Lines);
        await _orderRepository.AddAsync(order, cancellationToken);
        await _orderRepository.SaveChangesAsync(cancellationToken);
        return order.Id;
    }
}
```

```csharp
// Infrastructure layer - implements Domain interfaces using external libraries
// MyApp.Infrastructure/Persistence/OrderRepository.cs
namespace MyApp.Infrastructure.Persistence;

public class OrderRepository : IOrderRepository
{
    private readonly AppDbContext _dbContext;

    public OrderRepository(AppDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<Order?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _dbContext.Orders
            .Include(o => o.Lines)
            .FirstOrDefaultAsync(o => o.Id == id, cancellationToken);
    }

    public async Task AddAsync(Order order, CancellationToken cancellationToken = default)
    {
        await _dbContext.Orders.AddAsync(order, cancellationToken);
    }

    public async Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        await _dbContext.SaveChangesAsync(cancellationToken);
    }
}
```

### Project References

```xml
<!-- MyApp.Application.csproj -->
<ItemGroup>
    <ProjectReference Include="..\MyApp.Domain\MyApp.Domain.csproj" />
</ItemGroup>

<!-- MyApp.Infrastructure.csproj -->
<ItemGroup>
    <ProjectReference Include="..\MyApp.Application\MyApp.Application.csproj" />
</ItemGroup>

<!-- MyApp.Api.csproj -->
<ItemGroup>
    <ProjectReference Include="..\MyApp.Application\MyApp.Application.csproj" />
    <ProjectReference Include="..\MyApp.Infrastructure\MyApp.Infrastructure.csproj" />
</ItemGroup>
```

---

## Repository Pattern

### Generic Repository (Base)

Provide a generic base for common CRUD operations. Extend with specific repository interfaces for domain-specific queries.

```csharp
// Domain layer
public interface IRepository<T> where T : Entity
{
    Task<T?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<T>> GetAllAsync(CancellationToken cancellationToken = default);
    Task AddAsync(T entity, CancellationToken cancellationToken = default);
    void Update(T entity);
    void Remove(T entity);
}

// Domain-specific extension
public interface IOrderRepository : IRepository<Order>
{
    Task<IReadOnlyList<Order>> GetByCustomerIdAsync(Guid customerId, CancellationToken cancellationToken = default);
    Task<Order?> GetWithLinesAsync(Guid id, CancellationToken cancellationToken = default);
}
```

```csharp
// Infrastructure layer
public class Repository<T> : IRepository<T> where T : Entity
{
    protected readonly AppDbContext DbContext;

    public Repository(AppDbContext dbContext)
    {
        DbContext = dbContext;
    }

    public virtual async Task<T?> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await DbContext.Set<T>().FindAsync(new object[] { id }, cancellationToken);
    }

    public virtual async Task<IReadOnlyList<T>> GetAllAsync(CancellationToken cancellationToken = default)
    {
        return await DbContext.Set<T>().ToListAsync(cancellationToken);
    }

    public async Task AddAsync(T entity, CancellationToken cancellationToken = default)
    {
        await DbContext.Set<T>().AddAsync(entity, cancellationToken);
    }

    public void Update(T entity)
    {
        DbContext.Set<T>().Update(entity);
    }

    public void Remove(T entity)
    {
        DbContext.Set<T>().Remove(entity);
    }
}
```

### Specification Pattern

Use specifications to encapsulate query logic and keep repositories clean.

```csharp
// Base specification
public abstract class Specification<T> where T : class
{
    public abstract Expression<Func<T, bool>> ToExpression();

    public bool IsSatisfiedBy(T entity)
    {
        return ToExpression().Compile()(entity);
    }
}

// Concrete specification
public class ActiveOrdersForCustomerSpec : Specification<Order>
{
    private readonly Guid _customerId;

    public ActiveOrdersForCustomerSpec(Guid customerId)
    {
        _customerId = customerId;
    }

    public override Expression<Func<Order, bool>> ToExpression()
    {
        return order => order.CustomerId == _customerId
                     && order.Status != OrderStatus.Cancelled
                     && order.Status != OrderStatus.Delivered;
    }
}

// Repository method accepting specifications
public interface IRepository<T> where T : Entity
{
    Task<IReadOnlyList<T>> FindAsync(
        Specification<T> specification,
        CancellationToken cancellationToken = default);
}

// Usage
var spec = new ActiveOrdersForCustomerSpec(customerId);
var orders = await _orderRepository.FindAsync(spec, cancellationToken);
```

---

## CQRS with MediatR

### Command / Query Separation

Commands mutate state and return at most an identifier. Queries read state and return data. Never mix them.

```csharp
// Command - changes state
public record CreateOrderCommand(
    Guid CustomerId,
    List<OrderLineDto> Lines) : IRequest<Result<Guid>>;

// Query - reads state
public record GetOrderByIdQuery(Guid OrderId) : IRequest<Result<OrderResponse>>;
```

### Command Handler

```csharp
public class CreateOrderHandler : IRequestHandler<CreateOrderCommand, Result<Guid>>
{
    private readonly IOrderRepository _orderRepository;
    private readonly IUnitOfWork _unitOfWork;

    public CreateOrderHandler(IOrderRepository orderRepository, IUnitOfWork unitOfWork)
    {
        _orderRepository = orderRepository;
        _unitOfWork = unitOfWork;
    }

    public async Task<Result<Guid>> Handle(
        CreateOrderCommand request,
        CancellationToken cancellationToken)
    {
        var order = Order.Create(request.CustomerId, request.Lines);

        await _orderRepository.AddAsync(order, cancellationToken);
        await _unitOfWork.SaveChangesAsync(cancellationToken);

        return Result.Success(order.Id);
    }
}
```

### Query Handler

```csharp
public class GetOrderByIdHandler : IRequestHandler<GetOrderByIdQuery, Result<OrderResponse>>
{
    private readonly AppDbContext _dbContext;

    public GetOrderByIdHandler(AppDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<Result<OrderResponse>> Handle(
        GetOrderByIdQuery request,
        CancellationToken cancellationToken)
    {
        var order = await _dbContext.Orders
            .AsNoTracking()
            .Where(o => o.Id == request.OrderId)
            .Select(o => new OrderResponse(
                o.Id,
                o.CustomerName,
                o.TotalAmount,
                o.Status.ToString(),
                o.CreatedAt))
            .FirstOrDefaultAsync(cancellationToken);

        return order is not null
            ? Result.Success(order)
            : Result.Failure<OrderResponse>(OrderErrors.NotFound(request.OrderId));
    }
}
```

### Pipeline Behaviors

Use MediatR pipeline behaviors for cross-cutting concerns like validation, logging, and performance monitoring.

```csharp
// Validation behavior - runs FluentValidation before every handler
public class ValidationBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IRequest<TResponse>
{
    private readonly IEnumerable<IValidator<TRequest>> _validators;

    public ValidationBehavior(IEnumerable<IValidator<TRequest>> validators)
    {
        _validators = validators;
    }

    public async Task<TResponse> Handle(
        TRequest request,
        RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        if (!_validators.Any())
        {
            return await next();
        }

        var context = new ValidationContext<TRequest>(request);
        var validationResults = await Task.WhenAll(
            _validators.Select(v => v.ValidateAsync(context, cancellationToken)));

        var failures = validationResults
            .SelectMany(r => r.Errors)
            .Where(f => f is not null)
            .ToList();

        if (failures.Count > 0)
        {
            throw new ValidationException(failures);
        }

        return await next();
    }
}

// Logging behavior
public class LoggingBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IRequest<TResponse>
{
    private readonly ILogger<LoggingBehavior<TRequest, TResponse>> _logger;

    public LoggingBehavior(ILogger<LoggingBehavior<TRequest, TResponse>> logger)
    {
        _logger = logger;
    }

    public async Task<TResponse> Handle(
        TRequest request,
        RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        var requestName = typeof(TRequest).Name;
        _logger.LogInformation("Handling {RequestName}: {@Request}", requestName, request);

        var stopwatch = Stopwatch.StartNew();
        var response = await next();
        stopwatch.Stop();

        _logger.LogInformation("Handled {RequestName} in {ElapsedMs}ms",
            requestName, stopwatch.ElapsedMilliseconds);

        return response;
    }
}

// Registration
builder.Services.AddMediatR(cfg =>
{
    cfg.RegisterServicesFromAssembly(typeof(CreateOrderHandler).Assembly);
    cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(LoggingBehavior<,>));
    cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(ValidationBehavior<,>));
});
```

---

## Domain-Driven Design Basics

### Entity Base Class

Entities have identity and mutable state. Use a base class for common concerns.

```csharp
public abstract class Entity
{
    public Guid Id { get; protected set; }

    private readonly List<IDomainEvent> _domainEvents = new();
    public IReadOnlyCollection<IDomainEvent> DomainEvents => _domainEvents.AsReadOnly();

    protected void RaiseDomainEvent(IDomainEvent domainEvent)
    {
        _domainEvents.Add(domainEvent);
    }

    public void ClearDomainEvents()
    {
        _domainEvents.Clear();
    }

    public override bool Equals(object? obj)
    {
        if (obj is not Entity other) return false;
        if (ReferenceEquals(this, other)) return true;
        if (GetType() != other.GetType()) return false;
        return Id == other.Id;
    }

    public override int GetHashCode() => Id.GetHashCode();
}
```

### Value Objects

Value objects have no identity. They are defined by their attributes and are immutable.

```csharp
public record Money
{
    public decimal Amount { get; }
    public string Currency { get; }

    public Money(decimal amount, string currency)
    {
        if (amount < 0) throw new ArgumentException("Amount cannot be negative.", nameof(amount));
        if (string.IsNullOrWhiteSpace(currency)) throw new ArgumentException("Currency is required.", nameof(currency));

        Amount = amount;
        Currency = currency.ToUpperInvariant();
    }

    public Money Add(Money other)
    {
        if (Currency != other.Currency)
            throw new InvalidOperationException($"Cannot add {Currency} and {other.Currency}.");
        return new Money(Amount + other.Amount, Currency);
    }

    public Money Multiply(int factor) => new(Amount * factor, Currency);
}

public record Address(
    string Street,
    string City,
    string State,
    string ZipCode,
    string Country);
```

### Aggregates

Aggregates are clusters of entities and value objects treated as a single unit. The aggregate root controls all access.

```csharp
public class Order : Entity
{
    public Guid CustomerId { get; private set; }
    public OrderStatus Status { get; private set; }
    public Money TotalAmount { get; private set; }
    public DateTime CreatedAt { get; private set; }

    private readonly List<OrderLine> _lines = new();
    public IReadOnlyCollection<OrderLine> Lines => _lines.AsReadOnly();

    private Order() { } // EF Core constructor

    public static Order Create(Guid customerId, IEnumerable<OrderLineDto> lines)
    {
        var order = new Order
        {
            Id = Guid.NewGuid(),
            CustomerId = customerId,
            Status = OrderStatus.Pending,
            CreatedAt = DateTime.UtcNow,
            TotalAmount = new Money(0, "USD")
        };

        foreach (var line in lines)
        {
            order.AddLine(line.ProductId, line.ProductName, line.Quantity, line.UnitPrice);
        }

        order.RaiseDomainEvent(new OrderCreatedEvent(order.Id, customerId));
        return order;
    }

    public void AddLine(Guid productId, string productName, int quantity, decimal unitPrice)
    {
        if (Status != OrderStatus.Pending)
            throw new InvalidOperationException("Cannot add lines to a non-pending order.");

        var line = new OrderLine(productId, productName, quantity, new Money(unitPrice, "USD"));
        _lines.Add(line);
        RecalculateTotal();
    }

    public void Confirm()
    {
        if (Status != OrderStatus.Pending)
            throw new InvalidOperationException("Only pending orders can be confirmed.");
        if (!_lines.Any())
            throw new InvalidOperationException("Cannot confirm an order with no lines.");

        Status = OrderStatus.Confirmed;
        RaiseDomainEvent(new OrderConfirmedEvent(Id));
    }

    public void Cancel(string reason)
    {
        if (Status is OrderStatus.Shipped or OrderStatus.Delivered)
            throw new InvalidOperationException("Cannot cancel a shipped or delivered order.");

        Status = OrderStatus.Cancelled;
        RaiseDomainEvent(new OrderCancelledEvent(Id, reason));
    }

    private void RecalculateTotal()
    {
        var total = _lines.Sum(l => l.UnitPrice.Amount * l.Quantity);
        TotalAmount = new Money(total, "USD");
    }
}
```

---

## Result Pattern

Use the Result pattern to communicate success/failure without throwing exceptions for expected business failures.

### Result Type

```csharp
public class Result
{
    public bool IsSuccess { get; }
    public bool IsFailure => !IsSuccess;
    public Error Error { get; }

    protected Result(bool isSuccess, Error error)
    {
        IsSuccess = isSuccess;
        Error = error;
    }

    public static Result Success() => new(true, Error.None);
    public static Result Failure(Error error) => new(false, error);
    public static Result<TValue> Success<TValue>(TValue value) => new(value, true, Error.None);
    public static Result<TValue> Failure<TValue>(Error error) => new(default, false, error);
}

public class Result<TValue> : Result
{
    private readonly TValue? _value;

    public TValue Value => IsSuccess
        ? _value!
        : throw new InvalidOperationException("Cannot access Value on a failed result.");

    protected internal Result(TValue? value, bool isSuccess, Error error)
        : base(isSuccess, error)
    {
        _value = value;
    }

    public TResult Match<TResult>(Func<TValue, TResult> onSuccess, Func<Error, TResult> onFailure)
    {
        return IsSuccess ? onSuccess(_value!) : onFailure(Error);
    }
}

public record Error(string Code, string Message)
{
    public static readonly Error None = new(string.Empty, string.Empty);
}
```

### Usage in Handlers

```csharp
// Define domain-specific errors
public static class OrderErrors
{
    public static Error NotFound(Guid id) => new("Order.NotFound", $"Order '{id}' was not found.");
    public static Error AlreadyConfirmed => new("Order.AlreadyConfirmed", "Order is already confirmed.");
    public static Error EmptyLines => new("Order.EmptyLines", "Order must have at least one line.");
}

// Handler returning Result
public class ConfirmOrderHandler : IRequestHandler<ConfirmOrderCommand, Result>
{
    private readonly IOrderRepository _orderRepository;

    public ConfirmOrderHandler(IOrderRepository orderRepository)
    {
        _orderRepository = orderRepository;
    }

    public async Task<Result> Handle(ConfirmOrderCommand request, CancellationToken cancellationToken)
    {
        var order = await _orderRepository.GetByIdAsync(request.OrderId, cancellationToken);
        if (order is null)
            return Result.Failure(OrderErrors.NotFound(request.OrderId));

        if (order.Status != OrderStatus.Pending)
            return Result.Failure(OrderErrors.AlreadyConfirmed);

        order.Confirm();
        await _orderRepository.SaveChangesAsync(cancellationToken);
        return Result.Success();
    }
}

// Controller mapping Result to HTTP response
[HttpPost("{id:guid}/confirm")]
public async Task<IActionResult> Confirm(Guid id, CancellationToken cancellationToken)
{
    var result = await _mediator.Send(new ConfirmOrderCommand(id), cancellationToken);

    if (result.IsFailure)
    {
        return result.Error.Code switch
        {
            "Order.NotFound" => NotFound(result.Error),
            _ => BadRequest(result.Error)
        };
    }

    return NoContent();
}
```

---

## Guard Clauses

Validate preconditions at the top of methods. Fail fast with clear messages.

```csharp
// DO - Guard clauses at method entry
public class OrderService
{
    public async Task<Order> CreateOrderAsync(
        Guid customerId,
        List<OrderLineDto> lines,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(lines);

        if (customerId == Guid.Empty)
            throw new ArgumentException("Customer ID must not be empty.", nameof(customerId));

        if (lines.Count == 0)
            throw new ArgumentException("Order must contain at least one line.", nameof(lines));

        if (lines.Any(l => l.Quantity <= 0))
            throw new ArgumentException("All line quantities must be positive.", nameof(lines));

        // Happy path starts here -- no more validation
        var order = Order.Create(customerId, lines);
        await _orderRepository.AddAsync(order, cancellationToken);
        await _unitOfWork.SaveChangesAsync(cancellationToken);
        return order;
    }
}
```

Use a guard clause library (e.g., Ardalis.GuardClauses) for common checks.

```csharp
using Ardalis.GuardClauses;

public void ProcessPayment(Payment payment, decimal amount)
{
    Guard.Against.Null(payment);
    Guard.Against.NegativeOrZero(amount);
    Guard.Against.OutOfRange(amount, nameof(amount), 0.01m, 1_000_000m);
    // ...
}
```

---

## Builder Pattern

Use the builder pattern for constructing complex objects with many optional parameters.

```csharp
public class EmailMessageBuilder
{
    private string _to = string.Empty;
    private string _from = string.Empty;
    private string _subject = string.Empty;
    private string _body = string.Empty;
    private bool _isHtml;
    private readonly List<string> _cc = new();
    private readonly List<Attachment> _attachments = new();

    public EmailMessageBuilder To(string to)
    {
        _to = to;
        return this;
    }

    public EmailMessageBuilder From(string from)
    {
        _from = from;
        return this;
    }

    public EmailMessageBuilder Subject(string subject)
    {
        _subject = subject;
        return this;
    }

    public EmailMessageBuilder HtmlBody(string body)
    {
        _body = body;
        _isHtml = true;
        return this;
    }

    public EmailMessageBuilder TextBody(string body)
    {
        _body = body;
        _isHtml = false;
        return this;
    }

    public EmailMessageBuilder AddCc(string cc)
    {
        _cc.Add(cc);
        return this;
    }

    public EmailMessageBuilder AddAttachment(Attachment attachment)
    {
        _attachments.Add(attachment);
        return this;
    }

    public EmailMessage Build()
    {
        if (string.IsNullOrWhiteSpace(_to)) throw new InvalidOperationException("Recipient is required.");
        if (string.IsNullOrWhiteSpace(_subject)) throw new InvalidOperationException("Subject is required.");

        return new EmailMessage(_to, _from, _subject, _body, _isHtml, _cc, _attachments);
    }
}

// Usage
var email = new EmailMessageBuilder()
    .To("customer@example.com")
    .From("orders@myapp.com")
    .Subject("Order Confirmation")
    .HtmlBody("<h1>Thank you for your order!</h1>")
    .AddCc("support@myapp.com")
    .Build();
```

---

## Strategy Pattern

Use the strategy pattern to swap algorithms at runtime. Register strategies in DI.

```csharp
// Strategy interface
public interface IShippingCalculator
{
    string CarrierName { get; }
    Task<decimal> CalculateCostAsync(ShippingRequest request, CancellationToken cancellationToken = default);
}

// Concrete strategies
public class FedExShippingCalculator : IShippingCalculator
{
    public string CarrierName => "FedEx";

    public async Task<decimal> CalculateCostAsync(ShippingRequest request, CancellationToken cancellationToken = default)
    {
        // FedEx-specific calculation
        return request.Weight * 2.50m + 5.99m;
    }
}

public class UpsShippingCalculator : IShippingCalculator
{
    public string CarrierName => "UPS";

    public async Task<decimal> CalculateCostAsync(ShippingRequest request, CancellationToken cancellationToken = default)
    {
        // UPS-specific calculation
        return request.Weight * 2.25m + 7.49m;
    }
}

// Registration
builder.Services.AddTransient<IShippingCalculator, FedExShippingCalculator>();
builder.Services.AddTransient<IShippingCalculator, UpsShippingCalculator>();

// Consumer resolves all strategies
public class ShippingService
{
    private readonly IEnumerable<IShippingCalculator> _calculators;

    public ShippingService(IEnumerable<IShippingCalculator> calculators)
    {
        _calculators = calculators;
    }

    public async Task<ShippingQuote> GetBestQuoteAsync(
        ShippingRequest request,
        CancellationToken cancellationToken = default)
    {
        var quotes = new List<ShippingQuote>();

        foreach (var calculator in _calculators)
        {
            var cost = await calculator.CalculateCostAsync(request, cancellationToken);
            quotes.Add(new ShippingQuote(calculator.CarrierName, cost));
        }

        return quotes.MinBy(q => q.Cost)!;
    }
}
```

---

## Decorator Pattern

Use decorators to add cross-cutting concerns without modifying the original service. Wire them up through DI using Scrutor or manual registration.

```csharp
// Original service interface and implementation
public interface IOrderService
{
    Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default);
}

public class OrderService : IOrderService
{
    private readonly IOrderRepository _repository;

    public OrderService(IOrderRepository repository)
    {
        _repository = repository;
    }

    public async Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        return await _repository.GetByIdAsync(id, cancellationToken)
            ?? throw new NotFoundException(nameof(Order), id);
    }
}

// Caching decorator
public class CachedOrderService : IOrderService
{
    private readonly IOrderService _inner;
    private readonly IMemoryCache _cache;

    public CachedOrderService(IOrderService inner, IMemoryCache cache)
    {
        _inner = inner;
        _cache = cache;
    }

    public async Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        var cacheKey = $"order:{id}";
        if (_cache.TryGetValue(cacheKey, out Order? cached))
        {
            return cached!;
        }

        var order = await _inner.GetByIdAsync(id, cancellationToken);
        _cache.Set(cacheKey, order, TimeSpan.FromMinutes(5));
        return order;
    }
}

// Logging decorator
public class LoggedOrderService : IOrderService
{
    private readonly IOrderService _inner;
    private readonly ILogger<LoggedOrderService> _logger;

    public LoggedOrderService(IOrderService inner, ILogger<LoggedOrderService> logger)
    {
        _inner = inner;
        _logger = logger;
    }

    public async Task<Order> GetByIdAsync(Guid id, CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Getting order {OrderId}", id);
        var stopwatch = Stopwatch.StartNew();

        var order = await _inner.GetByIdAsync(id, cancellationToken);

        _logger.LogInformation("Retrieved order {OrderId} in {ElapsedMs}ms",
            id, stopwatch.ElapsedMilliseconds);
        return order;
    }
}

// Registration with Scrutor
builder.Services.AddScoped<IOrderService, OrderService>();
builder.Services.Decorate<IOrderService, CachedOrderService>();
builder.Services.Decorate<IOrderService, LoggedOrderService>();
// Resolution order: LoggedOrderService -> CachedOrderService -> OrderService
```

---

## Summary

When structuring a .NET project, apply these patterns in this priority:

1. **Clean Architecture** -- always use layered project structure with inward dependencies
2. **CQRS with MediatR** -- separate reads from writes for any non-trivial application
3. **Result pattern** -- return results instead of throwing exceptions for business logic failures
4. **Repository + Specification** -- encapsulate data access behind interfaces
5. **DDD basics** -- use entities with behavior, value objects, and aggregates for complex domains
6. **Guard clauses** -- validate preconditions at method entry
7. **Strategy/Decorator** -- apply for extensibility and cross-cutting concerns
8. **Builder** -- use for objects with many optional configuration parameters
