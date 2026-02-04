# Dependency Injection Patterns

> DI patterns and conventions for .NET 8 projects.

---

## Overview

The project uses constructor injection with Microsoft.Extensions.DependencyInjection. Dependencies are organized into extension methods for clean registration.

---

## Registration Pattern

### Business Dependencies

```csharp
// In Extensions/DependencyInjectionExtensions.cs
public static class DependencyInjectionExtensions
{
    public static IServiceCollection AddBusinessDependencies(this IServiceCollection services)
    {
        // Providers (business logic orchestrators)
        services.AddScoped<IUserProvider, UserProvider>();
        services.AddScoped<IOrderProvider, OrderProvider>();
        services.AddScoped<IProductProvider, ProductProvider>();
        
        return services;
    }
}
```

### Service Dependencies

```csharp
public static IServiceCollection AddServiceDependencies(
    this IServiceCollection services,
    IConfiguration configuration)
{
    // External service integrations
    ConfigureExternalApiService(services, configuration);
    ConfigureNotificationService(services, configuration);
    ConfigureStorageService(services, configuration);
    
    return services;
}

private static void ConfigureExternalApiService(
    IServiceCollection services,
    IConfiguration configuration)
{
    services.Configure<ExternalApiOptions>(
        configuration.GetSection("ExternalApiService"));
    
    services.AddHttpClient<IExternalApiService, ExternalApiService>((sp, client) =>
    {
        var options = sp.GetRequiredService<IOptions<ExternalApiOptions>>().Value;
        client.BaseAddress = new Uri(options.BaseUrl);
    }).AddHttpMessageHandler<DependencyHandler>();
}
```

---

## HTTP Client Configuration

### Using AddHttpClient (Standard)

```csharp
services.AddHttpClient<IExternalService, ExternalService>((sp, client) =>
{
    var options = sp.GetRequiredService<IOptions<ExternalServiceOptions>>().Value;
    client.BaseAddress = new Uri(options.BaseUrl);
    client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
}).AddHttpMessageHandler<DependencyHandler>();
```

### Manual HttpClient Configuration

```csharp
services.Configure<ExternalServiceOptions>(
    configuration.GetSection("ExternalService"));

services.AddHttpClient<IExternalService, ExternalService>((sp, client) =>
{
    ExternalServiceOptions options = sp
        .GetRequiredService<IOptions<ExternalServiceOptions>>()
        .Value;
    
    client.BaseAddress = new Uri(options.BaseUrl);
    client.DefaultRequestHeaders.Add("X-Api-Key", options.ApiKey);
    client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
})
.AddHttpMessageHandler<DependencyHandler>();
```

---

## Options Pattern

### Options Class

```csharp
// In Infrastructure/Options/
public class ExternalApiOptions
{
    public required string BaseUrl { get; init; }
    public required string ApiKey { get; init; }
    public int TimeoutSeconds { get; init; } = 30;
    public int MaxRetries { get; init; } = 3;
}
```

### appsettings.json

```json
{
  "ExternalApiService": {
    "BaseUrl": "https://api.example.com",
    "ApiKey": "from-keyvault",
    "TimeoutSeconds": 30,
    "MaxRetries": 3
  }
}
```

### Injecting Options

```csharp
public class ExternalApiService : IExternalApiService
{
    private readonly HttpClient _httpClient;
    private readonly ExternalApiOptions _options;
    
    public ExternalApiService(
        HttpClient httpClient,
        IOptions<ExternalApiOptions> options)
    {
        _httpClient = httpClient;
        _options = options.Value;
    }
}
```

---

## Lifetime Guidelines

| Lifetime | Use For | Example |
|----------|---------|---------|
| **Singleton** | Stateless, thread-safe services | `IMemoryCache`, Configuration |
| **Scoped** | Per-request state, DB contexts | Providers, Services, `DbContext` |
| **Transient** | Lightweight, stateless helpers | Validators, Factories |

### Common Registrations

```csharp
// Scoped (default for business logic)
services.AddScoped<IUserProvider, UserProvider>();

// Singleton (stateless, shared)
services.AddSingleton<IConfiguration>(configuration);
services.AddSingleton<IMemoryCache, MemoryCache>();

// Transient (new instance each time)
services.AddTransient<IValidator<CreateUserRequest>, CreateUserRequestValidator>();
```

---

## Naming Conventions

| Type | Naming | Interface Naming |
|------|--------|------------------|
| Provider | `{Feature}Provider` | `I{Feature}Provider` |
| Service | `{External}Service` | `I{External}Service` |
| Repository | `{Entity}Repository` | `I{Entity}Repository` |
| Options | `{Feature}Options` | - |
| Handler | `{Purpose}Handler` | `I{Purpose}Handler` |

---

## Layered Architecture

```
┌─────────────────────────────────┐
│       Controllers/Functions     │  ← Inject: Providers, ErrorMapper
├─────────────────────────────────┤
│           Providers             │  ← Inject: Services, Options, Cache
├─────────────────────────────────┤
│            Services             │  ← Inject: HttpClient, Options
├─────────────────────────────────┤
│     Infrastructure/External     │
└─────────────────────────────────┘
```

### Controller Example

```csharp
public class UsersController : ControllerBase
{
    private readonly IUserProvider _provider;
    private readonly IErrorMapper _errorMapper;
    
    public UsersController(
        IUserProvider provider,
        IErrorMapper errorMapper)
    {
        _provider = provider;
        _errorMapper = errorMapper;
    }
}
```

### Provider Example

```csharp
public class UserProvider : IUserProvider
{
    private readonly IUserService _userService;
    private readonly INotificationService _notificationService;
    private readonly IMemoryCache _cache;
    private readonly ILogger<UserProvider> _logger;
    
    public UserProvider(
        IUserService userService,
        INotificationService notificationService,
        IMemoryCache cache,
        ILogger<UserProvider> logger)
    {
        _userService = userService;
        _notificationService = notificationService;
        _cache = cache;
        _logger = logger;
    }
}
```

---

## Common Pitfalls

### ❌ Forgetting DependencyHandler

```csharp
// ❌ BAD: Missing resilience and telemetry
services.AddHttpClient<IExternalService, ExternalService>();

// ✅ GOOD: With handler
services.AddHttpClient<IExternalService, ExternalService>()
    .AddHttpMessageHandler<DependencyHandler>();
```

### ❌ Injecting Scoped into Singleton

```csharp
// ❌ BAD: Captive dependency
services.AddSingleton<SingletonService>();  // Captures scoped service

public class SingletonService
{
    private readonly IScopedService _scoped;  // Becomes singleton lifetime!
}

// ✅ GOOD: Use IServiceScopeFactory
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

### ❌ Not Validating Options

```csharp
// ✅ GOOD: Validate on startup
services.AddOptions<ApiCenterOptions>()
    .Bind(configuration.GetSection("ApiCenterService"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

---

## Testing with DI

```csharp
[TestFixture]
public class UserProviderTests
{
    private Mock<IUserService> _userServiceMock;
    private Mock<ILogger<UserProvider>> _loggerMock;
    private UserProvider _sut;
    
    [SetUp]
    public void SetUp()
    {
        _userServiceMock = new Mock<IUserService>();
        _loggerMock = new Mock<ILogger<UserProvider>>();
        
        _sut = new UserProvider(
            _userServiceMock.Object,
            _loggerMock.Object);
    }
}
```
