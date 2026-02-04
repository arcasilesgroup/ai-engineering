# Azure Functions Standards

> Patterns and conventions for Azure Functions (.NET Isolated Worker).

---

## Project Structure

```
{YourProject}.Functions/
├── Program.cs              # Host configuration
├── Functions/
│   ├── HttpTriggers/       # HTTP-triggered functions
│   │   └── UserFunctions.cs
│   ├── TimerTriggers/      # Scheduled functions
│   │   └── CleanupFunction.cs
│   ├── QueueTriggers/      # Queue-triggered functions
│   │   └── ProcessMessageFunction.cs
│   └── EventTriggers/      # Event Grid/Hub triggers
├── Business/               # Providers (shared with API)
├── Services/               # External integrations
├── Domain/                 # Models
└── Extensions/             # DI and helpers
```

---

## Function Patterns

### HTTP Trigger

```csharp
public class UserFunctions
{
    private readonly IUserProvider _provider;
    private readonly IErrorMapper _errorMapper;
    private readonly ILogger<UserFunctions> _logger;
    
    public UserFunctions(
        IUserProvider provider,
        IErrorMapper errorMapper,
        ILogger<UserFunctions> logger)
    {
        _provider = provider;
        _errorMapper = errorMapper;
        _logger = logger;
    }
    
    [Function("GetUser")]
    public async Task<HttpResponseData> GetUser(
        [HttpTrigger(AuthorizationLevel.Function, "get", Route = "users/{userId}")] 
        HttpRequestData req,
        string userId)
    {
        _logger.LogMethodExecutionStart();
        
        Result<UserResponse> result = await _provider.GetUserAsync(userId);
        
        return await result.ToHttpResponseAsync(req, _errorMapper, 
            response => req.CreateJsonResponse(response, HttpStatusCode.OK));
    }
    
    [Function("CreateUser")]
    public async Task<HttpResponseData> CreateUser(
        [HttpTrigger(AuthorizationLevel.Function, "post", Route = "users")] 
        HttpRequestData req)
    {
        CreateUserRequest? request = await req.ReadFromJsonAsync<CreateUserRequest>();
        
        if (request is null)
        {
            return req.CreateErrorResponse(
                new InvalidInputError("Request body is required"),
                _errorMapper);
        }
        
        Result<UserResponse> result = await _provider.CreateAsync(request);
        
        return await result.ToHttpResponseAsync(req, _errorMapper,
            response => req.CreateJsonResponse(response, HttpStatusCode.Created));
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
    public async Task Run(
        [TimerTrigger("0 0 2 * * *")] TimerInfo timer)  // 2 AM daily
    {
        _logger.LogInformation("Cleanup started at {Time}", DateTime.UtcNow);
        
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
public class ProcessMessageFunction
{
    private readonly IMessageProcessor _processor;
    private readonly ILogger<ProcessMessageFunction> _logger;
    
    public ProcessMessageFunction(
        IMessageProcessor processor,
        ILogger<ProcessMessageFunction> logger)
    {
        _processor = processor;
        _logger = logger;
    }
    
    [Function("ProcessMessage")]
    public async Task Run(
        [QueueTrigger("incoming-messages", Connection = "StorageConnection")] 
        QueueMessage message)
    {
        _logger.LogInformation("Processing message {MessageId}", message.MessageId);
        
        Result result = await _processor.ProcessAsync(message.Body.ToString());
        
        if (result.IsError)
        {
            _logger.LogError("Failed to process message {MessageId}: {Error}", 
                message.MessageId, result.Error.Message);
            throw new InvalidOperationException(result.Error.Message);  // Triggers retry
        }
    }
}
```

---

## Host Configuration (Program.cs)

```csharp
var host = new HostBuilder()
    .ConfigureFunctionsWorkerDefaults(worker =>
    {
        worker.UseNewtonsoftJson();  // Use Newtonsoft for consistency with API
    })
    .ConfigureServices((context, services) =>
    {
        IConfiguration configuration = context.Configuration;
        
        // Application Insights
        services.AddApplicationInsightsTelemetryWorkerService();
        services.ConfigureFunctionsApplicationInsights();
        
        // Remove default AI logger rule
        services.Configure<LoggerFilterOptions>(options =>
        {
            LoggerFilterRule? defaultRule = options.Rules
                .FirstOrDefault(rule => rule.ProviderName == 
                    "Microsoft.Extensions.Logging.ApplicationInsights.ApplicationInsightsLoggerProvider");
            if (defaultRule is not null)
            {
                options.Rules.Remove(defaultRule);
            }
        });
        
        // Business dependencies
        services.AddBusinessDependencies();
        services.AddServiceDependencies(configuration);
        services.AddErrorMappings();
    })
    .Build();

await host.RunAsync();
```

---

## Error Handling in Functions

### Extension Method for HttpResponseData

```csharp
public static class HttpResponseExtensions
{
    public static async Task<HttpResponseData> ToHttpResponseAsync<T>(
        this Result<T> result,
        HttpRequestData request,
        IErrorMapper errorMapper,
        Func<T, HttpResponseData> onSuccess)
    {
        if (result.IsError)
        {
            return CreateErrorResponse(request, result.Error, errorMapper);
        }
        
        return onSuccess(result.Value);
    }
    
    public static HttpResponseData CreateErrorResponse(
        HttpRequestData request,
        BaseError error,
        IErrorMapper errorMapper)
    {
        ErrorMappingResult mapping = errorMapper.Map(error);
        HttpResponseData response = request.CreateResponse((HttpStatusCode)mapping.StatusCode);
        await response.WriteAsJsonAsync(mapping.Response);
        return response;
    }
    
    public static HttpResponseData CreateJsonResponse<T>(
        this HttpRequestData request,
        T data,
        HttpStatusCode statusCode = HttpStatusCode.OK)
    {
        HttpResponseData response = request.CreateResponse(statusCode);
        await response.WriteAsJsonAsync(data);
        return response;
    }
}
```

---

## Model Validation

### Custom Invalid Model State Handler

```csharp
// In DI configuration
services.Configure<ApiBehaviorOptions>(options =>
{
    options.InvalidModelStateResponseFactory = context =>
    {
        var errors = context.ModelState
            .Where(e => e.Value?.Errors.Count > 0)
            .Select(e => new ValidationError(e.Key, e.Value!.Errors.First().ErrorMessage))
            .ToList();
        
        var error = new InvalidInputDetailedError("Validation failed", errors);
        return new ErrorActionResult(error);
    };
});
```

---

## Serialization (Newtonsoft)

Functions project uses Newtonsoft.Json for consistency with API:

```csharp
// In ConfigureFunctionsWorkerDefaults
worker.UseNewtonsoftJson(settings =>
{
    settings.NullValueHandling = NullValueHandling.Ignore;
    settings.Converters.Add(new StringEnumConverter());
    settings.ContractResolver = new CamelCasePropertyNamesContractResolver();
});
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Function class | `{Feature}Functions` | `UserFunctions`, `OrderFunctions` |
| Function name | PascalCase verb | `GetUser`, `CreateOrder`, `ProcessMessage` |
| Route | kebab-case | `users/{userId}`, `api-versions` |

---

## Best Practices

### Do

- ✅ Use constructor injection for dependencies
- ✅ Share Providers with API project
- ✅ Use Result pattern consistently
- ✅ Log at appropriate levels
- ✅ Configure retry policies for queue triggers

### Don't

- ❌ Use static methods for business logic
- ❌ Mix System.Text.Json and Newtonsoft.Json
- ❌ Swallow exceptions in queue triggers (prevents retry)
- ❌ Hardcode connection strings
