# Skill: Add HTTP Client

---
id: dotnet/add-http-client
name: Add HTTP Client
complexity: medium
estimated_time: 10 minutes
---

## Description

Configures a typed HTTP client for external service integration with proper options binding, resilience, and telemetry.

## Prerequisites

- External service API specification
- Configuration section in appsettings.json

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Service name | Yes | Name of the external service |
| Base URL | Yes | API base URL |
| Authentication | Yes | Auth method (API key, OAuth, etc.) |
| Timeout | No | Request timeout (default 30s) |

## Outputs

- Options class
- Service interface
- Service implementation
- DI registration
- appsettings configuration

## Execution Steps

### Step 1: Create Options Class

```csharp
// In Infrastructure/Options/
namespace {YourProject}.Infrastructure.Options;

public class ExternalApiOptions
{
    public required string BaseUrl { get; init; }
    public required string ApiKey { get; init; }
    public int TimeoutSeconds { get; init; } = 30;
    public int MaxRetries { get; init; } = 3;
}
```

### Step 2: Add Configuration

```json
// appsettings.json
{
  "ExternalApiService": {
    "BaseUrl": "https://api.external.com",
    "ApiKey": "from-keyvault-reference",
    "TimeoutSeconds": 30,
    "MaxRetries": 3
  }
}
```

### Step 3: Create Service Interface

```csharp
// In Services/Interfaces/
namespace {YourProject}.Services.Interfaces;

public interface IExternalApiService
{
    Task<Result<ExternalData>> GetDataAsync(string id);
    Task<Result<IReadOnlyList<ExternalData>>> SearchAsync(SearchRequest request);
    Task<Result> CreateAsync(CreateRequest request);
}
```

### Step 4: Create Service Implementation

```csharp
// In Services/
namespace {YourProject}.Services;

public class ExternalApiService : IExternalApiService
{
    private readonly HttpClient _httpClient;
    private readonly ExternalApiOptions _options;
    private readonly ILogger<ExternalApiService> _logger;

    public ExternalApiService(
        HttpClient httpClient,
        IOptions<ExternalApiOptions> options,
        ILogger<ExternalApiService> logger)
    {
        _httpClient = httpClient;
        _options = options.Value;
        _logger = logger;
    }

    public async Task<Result<ExternalData>> GetDataAsync(string id)
    {
        try
        {
            HttpResponseMessage response = await _httpClient.GetAsync($"data/{id}");
            
            if (response.StatusCode == HttpStatusCode.NotFound)
                return new NotFoundError($"Data {id} not found");
            
            response.EnsureSuccessStatusCode();
            
            ExternalData? data = await response.Content
                .ReadFromJsonAsync<ExternalData>();
            
            if (data is null)
                return new InternalError("Failed to deserialize response");
            
            return data;
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Failed to get data {Id}", id);
            return new InternalError($"External service error: {ex.Message}");
        }
    }
}
```

### Step 5: Register in DI

```csharp
// In Extensions/ServiceDependencyExtensions.cs
public static IServiceCollection AddServiceDependencies(
    this IServiceCollection services,
    IConfiguration configuration)
{
    ConfigureExternalApiService(services, configuration);
    // ... other services
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
        ExternalApiOptions options = sp
            .GetRequiredService<IOptions<ExternalApiOptions>>()
            .Value;

        client.BaseAddress = new Uri(options.BaseUrl);
        client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
        client.DefaultRequestHeaders.Add("X-Api-Key", options.ApiKey);
        client.DefaultRequestHeaders.Add("Accept", "application/json");
    })
    .AddHttpMessageHandler<DependencyHandler>();
}
```

### Step 6: Add Resilience (Optional - Polly)

```csharp
.AddHttpMessageHandler<DependencyHandler>()
.AddPolicyHandler(GetRetryPolicy())
.AddPolicyHandler(GetCircuitBreakerPolicy());

private static IAsyncPolicy<HttpResponseMessage> GetRetryPolicy()
{
    return HttpPolicyExtensions
        .HandleTransientHttpError()
        .WaitAndRetryAsync(3, retryAttempt => 
            TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)));
}

private static IAsyncPolicy<HttpResponseMessage> GetCircuitBreakerPolicy()
{
    return HttpPolicyExtensions
        .HandleTransientHttpError()
        .CircuitBreakerAsync(5, TimeSpan.FromSeconds(30));
}
```

## Checklist

- [ ] Options class created
- [ ] Configuration added to appsettings.json
- [ ] Service interface defined with Result returns
- [ ] Service implementation handles errors properly
- [ ] DI registration with HttpClient
- [ ] DependencyHandler added
- [ ] Timeout configured
- [ ] Authentication headers set
- [ ] Retry policy added (if needed)

## Common Mistakes

| Mistake | Consequence |
|---------|-------------|
| Missing DependencyHandler | No telemetry/resilience |
| Hardcoded URLs | Environment issues |
| Missing timeout | Hanging requests |
| Not handling HTTP errors | Unhandled exceptions |

## Related Skills

- [Create Provider](../create-provider/skill.md)
- [Add Error Mapping](../add-error-mapping/skill.md)

## Example Invocation

```
Add HTTP client for API Center:
- Service: ApiCenterService
- Base URL: https://apicenter.azure.com
- Auth: Azure AD token
- Operations: GetApis, GetApiVersions, RegisterApi
```
