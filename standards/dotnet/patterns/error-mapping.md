# Error Mapping

> Transforming domain errors to HTTP responses.

---

## Overview

Error Mapping provides centralized conversion of domain errors (`BaseError`) to HTTP responses with consistent status codes and response formats.

**Implementation Options:**
- Create your own `IErrorMapper` abstraction in a shared library
- Use middleware for centralized exception handling
- Implement ProblemDetails factory for RFC 7807 compliance

---

## Configuration

### API (Startup.cs)

```csharp
services.AddErrorMappings(mappings =>
{
    // Standard mappings
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

### Functions (Startup.ErrorMapping.cs)

```csharp
public static IServiceCollection AddErrorMappings(this IServiceCollection services)
{
    services.AddErrorMappings(mappings =>
    {
        // Same mappings as API
        mappings.Map<NotFoundError>()
            .To<NotFoundResponse>(StatusCodes.Status404NotFound)
            .AfterMap((error, response, context) =>
            {
                // Tag for telemetry
                context.HttpContext?.Items.Add(
                    RequestLoggerFilter.ResponseBodyType, 
                    typeof(NotFoundResponse));
            });
        
        // Additional mappings...
    });
    
    return services;
}
```

---

## Standard Mapping Table

| Domain Error | HTTP Status | Response Type | Use Case |
|--------------|-------------|---------------|----------|
| `NotFoundError` | 404 | `NotFoundResponse` | Resource doesn't exist |
| `InvalidInputError` | 400 | `BadRequestResponse` | Simple validation failure |
| `InvalidInputDetailedError` | 400 | `BadRequestResponse` | Validation with field errors |
| `UnauthorizedError` | 401 | `UnauthorizedResponse` | Authentication required |
| `ForbiddenError` | 403 | `ForbiddenResponse` | Insufficient permissions |
| `ConflictError` | 409 | `ConflictResponse` | State conflict (duplicate, etc.) |
| `BaseError` (fallback) | 500 | `InternalErrorResponse` | Unmapped/unexpected errors |

---

## Usage in Controllers

### With ToActionResult Extension

```csharp
[HttpGet("{id}")]
public async Task<IActionResult> GetUser(string id)
{
    Result<UserResponse> result = await _provider.GetUserAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}
```

### Manual Mapping

```csharp
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

---

## Response Format

All error responses follow Problem Details format (RFC 7807):

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.4",
  "title": "Not Found",
  "status": 404,
  "detail": "User with ID 'user-123' was not found.",
  "traceId": "00-abc123def456-789xyz-00"
}
```

### Validation Errors (with details)

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

---

## Adding New Error Types

### Step 1: Create Domain Error

```csharp
// In Domain/Errors/
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

### Step 2: Create Response Type (if needed)

```csharp
public class RateLimitResponse
{
    public string Message { get; init; }
    public int RetryAfterSeconds { get; init; }
}
```

### Step 3: Register Mapping

```csharp
mappings.Map<RateLimitExceededError>()
    .To<RateLimitResponse>(StatusCodes.Status429TooManyRequests)
    .AfterMap((error, response, context) =>
    {
        // Add Retry-After header
        context.HttpContext?.Response.Headers.Add(
            "Retry-After", 
            error.RetryAfterSeconds.ToString());
    });
```

---

## ⚠️ Common Pitfall

### Missing Mapping Throws Exception

If you return an error type without a registered mapping:

```csharp
// This will throw ArgumentException at runtime:
// "Unable to find mapping for type MyNewError"
return new MyNewError("Something went wrong");
```

**Always register mappings for new error types!**

---

## AfterMap Hook

Use `AfterMap` for post-mapping operations like:

- Adding response headers
- Telemetry tagging
- Logging

```csharp
mappings.Map<NotFoundError>()
    .To<NotFoundResponse>(StatusCodes.Status404NotFound)
    .AfterMap((error, response, context) =>
    {
        // Telemetry
        context.HttpContext?.Items.Add("ErrorType", nameof(NotFoundError));
        
        // Logging
        var logger = context.HttpContext?.RequestServices
            .GetService<ILogger<ErrorMapper>>();
        logger?.LogWarning("Resource not found: {Message}", error.Message);
    });
```

---

## Testing Error Mappings

```csharp
[Test]
public void Map_NotFoundError_Returns404()
{
    // Arrange
    var error = new NotFoundError("User not found");
    IErrorMapper mapper = CreateMapper();
    
    // Act
    ErrorMappingResult result = mapper.Map(error);
    
    // Assert
    using (Assert.EnterMultipleScope())
    {
        Assert.That(result.StatusCode, Is.EqualTo(404));
        Assert.That(result.Response, Is.TypeOf<NotFoundResponse>());
    }
}
```
