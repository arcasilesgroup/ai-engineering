# .NET Testing Standards

All .NET test code must follow these conventions. Tests use **xUnit** as the test framework, **NSubstitute** for mocking, **FluentAssertions** for assertions, and **AutoFixture** for test data generation. Follow these rules for every test you write.

---

## Test Project Structure

### Separate Test Projects Per Layer

Mirror the production project structure with dedicated test projects.

```
tests/
  MyApp.Domain.UnitTests/
  MyApp.Application.UnitTests/
  MyApp.Infrastructure.IntegrationTests/
  MyApp.Api.IntegrationTests/
  MyApp.Architecture.Tests/
```

### File Mirroring

Each test file mirrors the production file it tests. Place tests in the same namespace structure.

```
src/MyApp.Application/Orders/Commands/CreateOrder/CreateOrderHandler.cs
tests/MyApp.Application.UnitTests/Orders/Commands/CreateOrder/CreateOrderHandlerTests.cs
```

### Project References

```xml
<!-- MyApp.Application.UnitTests.csproj -->
<ItemGroup>
    <ProjectReference Include="..\..\src\MyApp.Application\MyApp.Application.csproj" />
</ItemGroup>

<ItemGroup>
    <PackageReference Include="xunit" Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.*" />
    <PackageReference Include="NSubstitute" Version="5.*" />
    <PackageReference Include="FluentAssertions" Version="7.*" />
    <PackageReference Include="AutoFixture" Version="4.*" />
    <PackageReference Include="AutoFixture.AutoNSubstitute" Version="4.*" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
</ItemGroup>
```

---

## Test Naming Convention

### Format: MethodName_Scenario_ExpectedBehavior

Every test method follows the `MethodName_Scenario_ExpectedBehavior` convention using PascalCase with underscores separating the three parts.

```csharp
// DO
[Fact]
public async Task GetByIdAsync_OrderExists_ReturnsOrder()

[Fact]
public async Task GetByIdAsync_OrderDoesNotExist_ReturnsNull()

[Fact]
public async Task CreateAsync_ValidRequest_CreatesOrderAndReturnsId()

[Fact]
public async Task CreateAsync_EmptyLines_ThrowsValidationException()

[Fact]
public async Task Confirm_OrderIsPending_SetsStatusToConfirmed()

[Fact]
public async Task Confirm_OrderIsAlreadyShipped_ThrowsInvalidOperationException()
```

```csharp
// DON'T
[Fact]
public async Task Test1()                           // meaningless name

[Fact]
public async Task TestGetById()                     // no scenario or expectation

[Fact]
public async Task It_Should_Return_Order()          // BDD style mixed with xUnit

[Fact]
public async Task GetByIdAsyncShouldReturnOrder()   // missing underscores
```

---

## xUnit Conventions

### Fact for Single-Case Tests

Use `[Fact]` for tests with a single set of inputs.

```csharp
[Fact]
public async Task GetByIdAsync_OrderExists_ReturnsOrder()
{
    // Arrange
    var orderId = Guid.NewGuid();
    var expectedOrder = new Order { Id = orderId, CustomerName = "John Doe" };
    _orderRepository.GetByIdAsync(orderId, Arg.Any<CancellationToken>())
        .Returns(expectedOrder);

    // Act
    var result = await _sut.GetByIdAsync(orderId);

    // Assert
    result.Should().NotBeNull();
    result!.Id.Should().Be(orderId);
    result.CustomerName.Should().Be("John Doe");
}
```

### Theory for Parameterized Tests

Use `[Theory]` with `[InlineData]` for testing multiple inputs.

```csharp
[Theory]
[InlineData(0)]
[InlineData(-1)]
[InlineData(-100)]
public void SetQuantity_NonPositiveValue_ThrowsArgumentException(int quantity)
{
    // Arrange
    var orderLine = new OrderLine();

    // Act
    var act = () => orderLine.SetQuantity(quantity);

    // Assert
    act.Should().Throw<ArgumentException>()
        .WithParameterName("quantity");
}

[Theory]
[InlineData(100, 0.0)]
[InlineData(500, 0.05)]
[InlineData(1000, 0.10)]
[InlineData(5000, 0.15)]
public void CalculateDiscount_VariousAmounts_ReturnsCorrectRate(
    decimal amount, decimal expectedRate)
{
    // Arrange
    var calculator = new DiscountCalculator();

    // Act
    var rate = calculator.Calculate(amount);

    // Assert
    rate.Should().Be(expectedRate);
}
```

### MemberData for Complex Test Data

Use `[MemberData]` when test data is too complex for `[InlineData]`.

```csharp
public class CreateOrderHandlerTests
{
    public static IEnumerable<object[]> InvalidOrderData()
    {
        yield return new object[]
        {
            new CreateOrderCommand(Guid.Empty, new List<OrderLineDto>()),
            "CustomerId"
        };
        yield return new object[]
        {
            new CreateOrderCommand(Guid.NewGuid(), new List<OrderLineDto>()),
            "Lines"
        };
        yield return new object[]
        {
            new CreateOrderCommand(Guid.NewGuid(), new List<OrderLineDto>
            {
                new(Guid.NewGuid(), "Product", -1, 10m)
            }),
            "Quantity"
        };
    }

    [Theory]
    [MemberData(nameof(InvalidOrderData))]
    public async Task Handle_InvalidData_ReturnsValidationError(
        CreateOrderCommand command,
        string expectedErrorField)
    {
        // Act
        var result = await _sut.Handle(command, CancellationToken.None);

        // Assert
        result.IsFailure.Should().BeTrue();
        result.Error.Code.Should().Contain(expectedErrorField);
    }
}
```

### ClassData for Shared Test Data

Use `[ClassData]` when test data is reused across multiple test classes.

```csharp
public class ValidOrderTestData : IEnumerable<object[]>
{
    public IEnumerator<object[]> GetEnumerator()
    {
        yield return new object[] { 1, 10.00m, 10.00m };
        yield return new object[] { 5, 20.00m, 100.00m };
        yield return new object[] { 10, 5.50m, 55.00m };
    }

    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();
}

[Theory]
[ClassData(typeof(ValidOrderTestData))]
public void CalculateLineTotal_ValidInputs_ReturnsCorrectTotal(
    int quantity, decimal unitPrice, decimal expectedTotal)
{
    var line = new OrderLine { Quantity = quantity, UnitPrice = unitPrice };
    line.LineTotal.Should().Be(expectedTotal);
}
```

---

## Arrange-Act-Assert Pattern

Every test body follows the Arrange-Act-Assert pattern with clear section comments.

```csharp
[Fact]
public async Task CreateAsync_ValidRequest_CreatesOrderAndReturnsId()
{
    // Arrange
    var command = new CreateOrderCommand(
        CustomerId: Guid.NewGuid(),
        Lines: new List<OrderLineDto>
        {
            new(Guid.NewGuid(), "Widget", 2, 25.00m)
        });

    _orderRepository.AddAsync(Arg.Any<Order>(), Arg.Any<CancellationToken>())
        .Returns(Task.CompletedTask);

    _unitOfWork.SaveChangesAsync(Arg.Any<CancellationToken>())
        .Returns(Task.CompletedTask);

    // Act
    var result = await _sut.Handle(command, CancellationToken.None);

    // Assert
    result.IsSuccess.Should().BeTrue();
    result.Value.Should().NotBeEmpty();

    await _orderRepository.Received(1).AddAsync(
        Arg.Is<Order>(o => o.CustomerId == command.CustomerId),
        Arg.Any<CancellationToken>());

    await _unitOfWork.Received(1).SaveChangesAsync(Arg.Any<CancellationToken>());
}
```

---

## FluentAssertions Usage

### Basic Assertions

```csharp
// Equality
result.Should().Be(expected);
result.Should().NotBe(unexpected);

// Null checks
result.Should().NotBeNull();
result.Should().BeNull();

// Boolean
isActive.Should().BeTrue();
isDeleted.Should().BeFalse();

// Strings
name.Should().Be("John Doe");
name.Should().StartWith("John");
name.Should().Contain("Doe");
name.Should().NotBeNullOrWhiteSpace();
email.Should().MatchRegex(@"^[\w.-]+@[\w.-]+\.\w+$");
```

### Collection Assertions

```csharp
// Count
orders.Should().HaveCount(3);
orders.Should().NotBeEmpty();
orders.Should().BeEmpty();
orders.Should().ContainSingle();

// Content
orders.Should().Contain(o => o.Id == expectedId);
orders.Should().AllSatisfy(o => o.Status.Should().Be(OrderStatus.Active));
orders.Should().BeInDescendingOrder(o => o.CreatedAt);
orders.Should().OnlyContain(o => o.TotalAmount > 0);

// Equivalence (deep comparison)
actualOrders.Should().BeEquivalentTo(expectedOrders, options =>
    options.Excluding(o => o.CreatedAt));
```

### Exception Assertions

```csharp
// Synchronous
var act = () => order.Confirm();
act.Should().Throw<InvalidOperationException>()
    .WithMessage("*pending*");

// Asynchronous
var act = async () => await service.GetByIdAsync(Guid.Empty);
await act.Should().ThrowAsync<ArgumentException>()
    .WithParameterName("id");

// No exception
var act = () => order.AddLine(productId, "Widget", 1, 10.00m);
act.Should().NotThrow();
```

### Type Assertions

```csharp
result.Should().BeOfType<OrderResponse>();
result.Should().BeAssignableTo<IEntity>();
```

### Execution Time Assertions

```csharp
var act = () => service.ProcessAsync(data);
act.ExecutionTime().Should().BeLessThan(TimeSpan.FromSeconds(5));
```

---

## NSubstitute Mocking

### Creating Substitutes

```csharp
public class CreateOrderHandlerTests
{
    private readonly IOrderRepository _orderRepository;
    private readonly IUnitOfWork _unitOfWork;
    private readonly ILogger<CreateOrderHandler> _logger;
    private readonly CreateOrderHandler _sut;

    public CreateOrderHandlerTests()
    {
        _orderRepository = Substitute.For<IOrderRepository>();
        _unitOfWork = Substitute.For<IUnitOfWork>();
        _logger = Substitute.For<ILogger<CreateOrderHandler>>();
        _sut = new CreateOrderHandler(_orderRepository, _unitOfWork, _logger);
    }
}
```

### Configuring Returns

```csharp
// Simple return
_orderRepository.GetByIdAsync(orderId, Arg.Any<CancellationToken>())
    .Returns(expectedOrder);

// Async return
_orderRepository.GetByIdAsync(orderId, Arg.Any<CancellationToken>())
    .Returns(Task.FromResult<Order?>(expectedOrder));

// Return based on input
_orderRepository.GetByIdAsync(Arg.Any<Guid>(), Arg.Any<CancellationToken>())
    .Returns(callInfo =>
    {
        var id = callInfo.ArgAt<Guid>(0);
        return orders.FirstOrDefault(o => o.Id == id);
    });

// Sequential returns
_orderRepository.GetByIdAsync(orderId, Arg.Any<CancellationToken>())
    .Returns(null as Order, expectedOrder);  // first call returns null, second returns order

// Throwing exceptions
_orderRepository.GetByIdAsync(Arg.Any<Guid>(), Arg.Any<CancellationToken>())
    .ThrowsAsync(new TimeoutException("Database timed out"));
```

### Verifying Calls (Received)

```csharp
// Verify a method was called
await _orderRepository.Received(1).AddAsync(
    Arg.Any<Order>(),
    Arg.Any<CancellationToken>());

// Verify method was called with specific arguments
await _orderRepository.Received(1).AddAsync(
    Arg.Is<Order>(o =>
        o.CustomerId == expectedCustomerId &&
        o.Lines.Count == 2),
    Arg.Any<CancellationToken>());

// Verify a method was NOT called
await _emailService.DidNotReceive().SendAsync(
    Arg.Any<EmailMessage>(),
    Arg.Any<CancellationToken>());

// Verify call count
await _orderRepository.Received(3).SaveChangesAsync(Arg.Any<CancellationToken>());
```

### Argument Matchers

```csharp
// Any value
Arg.Any<Guid>()
Arg.Any<CancellationToken>()

// Matching conditions
Arg.Is<Order>(o => o.Status == OrderStatus.Pending)
Arg.Is<string>(s => s.Contains("error"))
Arg.Is<decimal>(d => d > 0 && d < 1000)

// Do action when called
_orderRepository.AddAsync(Arg.Do<Order>(o => capturedOrder = o), Arg.Any<CancellationToken>());
```

---

## AutoFixture for Test Data Generation

### Basic Usage

```csharp
public class OrderServiceTests
{
    private readonly IFixture _fixture;

    public OrderServiceTests()
    {
        _fixture = new Fixture().Customize(new AutoNSubstituteCustomization());
    }

    [Fact]
    public async Task GetByIdAsync_OrderExists_ReturnsOrder()
    {
        // Arrange - AutoFixture generates realistic test data
        var expectedOrder = _fixture.Create<OrderResponse>();
        var orderId = expectedOrder.Id;

        var orderRepository = _fixture.Freeze<IOrderRepository>();
        orderRepository.GetByIdAsync(orderId, Arg.Any<CancellationToken>())
            .Returns(expectedOrder);

        var sut = _fixture.Create<OrderService>();

        // Act
        var result = await sut.GetByIdAsync(orderId);

        // Assert
        result.Should().BeEquivalentTo(expectedOrder);
    }
}
```

### Customizing Generated Data

```csharp
// Customize specific properties
var order = _fixture.Build<Order>()
    .With(o => o.Status, OrderStatus.Pending)
    .With(o => o.TotalAmount, 150.00m)
    .Without(o => o.Lines)  // exclude complex nested property
    .Create();

// Create many
var orders = _fixture.CreateMany<Order>(10).ToList();

// Register custom creation rules
_fixture.Customize<Order>(composer =>
    composer.With(o => o.Status, OrderStatus.Pending)
            .With(o => o.CreatedAt, DateTime.UtcNow));
```

### Freeze for Shared Dependencies

`Freeze` ensures the same instance is used everywhere within the fixture. Use it for dependencies that the SUT receives via constructor injection.

```csharp
[Fact]
public async Task Handle_ValidCommand_SavesOrder()
{
    // Freeze returns the same substitute for all IOrderRepository resolutions
    var repository = _fixture.Freeze<IOrderRepository>();
    var unitOfWork = _fixture.Freeze<IUnitOfWork>();

    var command = _fixture.Create<CreateOrderCommand>();
    var sut = _fixture.Create<CreateOrderHandler>();

    // Act
    await sut.Handle(command, CancellationToken.None);

    // Assert - "repository" is the same instance injected into "sut"
    await repository.Received(1).AddAsync(Arg.Any<Order>(), Arg.Any<CancellationToken>());
}
```

---

## Integration Testing

### WebApplicationFactory

Use `WebApplicationFactory<Program>` to spin up the full application pipeline for integration tests.

```csharp
public class OrdersApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    private readonly WebApplicationFactory<Program> _factory;

    public OrdersApiTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                // Replace real database with in-memory for testing
                var descriptor = services.SingleOrDefault(
                    d => d.ServiceType == typeof(DbContextOptions<AppDbContext>));

                if (descriptor is not null)
                {
                    services.Remove(descriptor);
                }

                services.AddDbContext<AppDbContext>(options =>
                    options.UseInMemoryDatabase("TestDb"));
            });
        });

        _client = _factory.CreateClient();
    }

    [Fact]
    public async Task CreateOrder_ValidRequest_Returns201()
    {
        // Arrange
        var request = new CreateOrderRequest
        {
            CustomerName = "John Doe",
            Lines = new List<OrderLineRequest>
            {
                new() { ProductId = Guid.NewGuid(), Quantity = 2, UnitPrice = 25.00m }
            }
        };

        // Act
        var response = await _client.PostAsJsonAsync("/api/orders", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        response.Headers.Location.Should().NotBeNull();

        var created = await response.Content.ReadFromJsonAsync<OrderResponse>();
        created.Should().NotBeNull();
        created!.CustomerName.Should().Be("John Doe");
    }

    [Fact]
    public async Task GetOrder_NonExistentId_Returns404()
    {
        // Act
        var response = await _client.GetAsync($"/api/orders/{Guid.NewGuid()}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }
}
```

### TestContainers for Real Database Testing

Use TestContainers when you need to test against a real database engine (PostgreSQL, SQL Server, etc.).

```csharp
public class OrderRepositoryTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine")
        .Build();

    private AppDbContext _dbContext = null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();

        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(_postgres.GetConnectionString())
            .Options;

        _dbContext = new AppDbContext(options);
        await _dbContext.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await _dbContext.DisposeAsync();
        await _postgres.DisposeAsync();
    }

    [Fact]
    public async Task AddAsync_ValidOrder_PersistsToDatabase()
    {
        // Arrange
        var repository = new OrderRepository(_dbContext);
        var order = Order.Create(Guid.NewGuid(), new List<OrderLineDto>
        {
            new(Guid.NewGuid(), "Widget", 3, 15.00m)
        });

        // Act
        await repository.AddAsync(order);
        await _dbContext.SaveChangesAsync();

        // Assert
        var persisted = await _dbContext.Orders
            .Include(o => o.Lines)
            .FirstOrDefaultAsync(o => o.Id == order.Id);

        persisted.Should().NotBeNull();
        persisted!.Lines.Should().HaveCount(1);
        persisted.Lines.First().Quantity.Should().Be(3);
    }
}
```

---

## Database Testing Strategy

### When to Use Each Approach

| Approach | Use When | Trade-offs |
|----------|----------|------------|
| **In-Memory DB** | Fast unit-like tests for EF Core logic | Does not support all SQL features; no real query translation |
| **SQLite In-Memory** | Better SQL compatibility than in-memory | Still differs from production DB in edge cases |
| **TestContainers** | Full integration tests with real DB engine | Slower; requires Docker; most accurate |

```csharp
// SQLite in-memory for middle-ground tests
public class SqliteOrderRepositoryTests : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly AppDbContext _dbContext;

    public SqliteOrderRepositoryTests()
    {
        _connection = new SqliteConnection("DataSource=:memory:");
        _connection.Open();

        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseSqlite(_connection)
            .Options;

        _dbContext = new AppDbContext(options);
        _dbContext.Database.EnsureCreated();
    }

    public void Dispose()
    {
        _dbContext.Dispose();
        _connection.Dispose();
    }
}
```

---

## Architecture Testing with NetArchTest

Enforce architectural rules automatically so they cannot be violated.

```csharp
public class ArchitectureTests
{
    private const string DomainNamespace = "MyApp.Domain";
    private const string ApplicationNamespace = "MyApp.Application";
    private const string InfrastructureNamespace = "MyApp.Infrastructure";
    private const string ApiNamespace = "MyApp.Api";

    [Fact]
    public void Domain_ShouldNotDependOn_Application()
    {
        var result = Types.InAssembly(typeof(Order).Assembly)
            .ShouldNot()
            .HaveDependencyOn(ApplicationNamespace)
            .GetResult();

        result.IsSuccessful.Should().BeTrue(
            $"Domain layer must not depend on Application. Violating types: {string.Join(", ", result.FailingTypeNames ?? Array.Empty<string>())}");
    }

    [Fact]
    public void Domain_ShouldNotDependOn_Infrastructure()
    {
        var result = Types.InAssembly(typeof(Order).Assembly)
            .ShouldNot()
            .HaveDependencyOn(InfrastructureNamespace)
            .GetResult();

        result.IsSuccessful.Should().BeTrue();
    }

    [Fact]
    public void Application_ShouldNotDependOn_Infrastructure()
    {
        var result = Types.InAssembly(typeof(CreateOrderHandler).Assembly)
            .ShouldNot()
            .HaveDependencyOn(InfrastructureNamespace)
            .GetResult();

        result.IsSuccessful.Should().BeTrue();
    }

    [Fact]
    public void Application_ShouldNotDependOn_Api()
    {
        var result = Types.InAssembly(typeof(CreateOrderHandler).Assembly)
            .ShouldNot()
            .HaveDependencyOn(ApiNamespace)
            .GetResult();

        result.IsSuccessful.Should().BeTrue();
    }

    [Fact]
    public void Handlers_ShouldHaveCorrectNamingConvention()
    {
        var result = Types.InAssembly(typeof(CreateOrderHandler).Assembly)
            .That()
            .ImplementInterface(typeof(IRequestHandler<,>))
            .Should()
            .HaveNameEndingWith("Handler")
            .GetResult();

        result.IsSuccessful.Should().BeTrue();
    }

    [Fact]
    public void Controllers_ShouldInheritFromControllerBase()
    {
        var result = Types.InAssembly(typeof(Program).Assembly)
            .That()
            .HaveNameEndingWith("Controller")
            .Should()
            .Inherit(typeof(ControllerBase))
            .GetResult();

        result.IsSuccessful.Should().BeTrue();
    }
}
```

---

## Test Organization Tips

### One Assertion Concept Per Test

A test should verify one logical concept. Multiple `Should()` calls are fine when they all relate to the same concept.

```csharp
// DO - Multiple assertions about the same concept (the created order)
[Fact]
public async Task CreateAsync_ValidRequest_ReturnsCompleteOrderResponse()
{
    // ...
    result.Should().NotBeNull();
    result.Id.Should().NotBeEmpty();
    result.Status.Should().Be("Pending");
    result.Lines.Should().HaveCount(2);
    result.TotalAmount.Should().Be(50.00m);
}

// DON'T - Multiple unrelated assertions testing different behaviors
[Fact]
public async Task CreateAsync_ValidRequest_WorksCorrectly()
{
    // ...
    result.Should().NotBeNull();                           // concept 1: creation
    await _emailService.Received(1).SendAsync(Arg.Any<EmailMessage>(), Arg.Any<CancellationToken>()); // concept 2: email
    await _inventoryService.Received(1).ReserveAsync(Arg.Any<ReserveRequest>(), Arg.Any<CancellationToken>());  // concept 3: inventory
    // These should be three separate tests
}
```

### Shared Test Setup

Use constructor for per-test setup. Use `IClassFixture<T>` for expensive shared setup. Use `ICollectionFixture<T>` for cross-class shared setup.

```csharp
// Per-test setup (constructor runs before each test)
public class OrderServiceTests
{
    private readonly IOrderRepository _repository;
    private readonly OrderService _sut;

    public OrderServiceTests()
    {
        _repository = Substitute.For<IOrderRepository>();
        _sut = new OrderService(_repository);
    }
}

// Shared expensive setup (database, HTTP server)
public class DatabaseFixture : IAsyncLifetime
{
    public AppDbContext DbContext { get; private set; } = null!;

    public async Task InitializeAsync()
    {
        // Expensive setup done once
    }

    public async Task DisposeAsync()
    {
        await DbContext.DisposeAsync();
    }
}

[CollectionDefinition("Database")]
public class DatabaseCollection : ICollectionFixture<DatabaseFixture> { }

[Collection("Database")]
public class OrderRepositoryTests
{
    private readonly DatabaseFixture _fixture;

    public OrderRepositoryTests(DatabaseFixture fixture)
    {
        _fixture = fixture;
    }
}
```

---

## Summary Checklist

Before submitting tests, verify:

- [ ] Test names follow `MethodName_Scenario_ExpectedBehavior` convention
- [ ] Tests follow Arrange-Act-Assert structure with comments
- [ ] FluentAssertions used for all assertions (no `Assert.Equal`)
- [ ] NSubstitute used for mocking (no Moq, no FakeItEasy)
- [ ] Each test verifies one logical concept
- [ ] `[Theory]` used for parameterized tests with `[InlineData]` or `[MemberData]`
- [ ] Integration tests use `WebApplicationFactory` or `TestContainers`
- [ ] Architecture tests enforce layer dependency rules
- [ ] No test depends on execution order
- [ ] No test depends on external state (files, databases, network) unless it is an integration test with proper setup/teardown
