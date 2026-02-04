# Skill: Add Error Mapping

---
id: dotnet/add-error-mapping
name: Add Error Mapping
complexity: low
estimated_time: 5 minutes
---

## Description

Registers error mappings for new domain errors to ensure proper HTTP response conversion.

## Prerequisites

- New domain error type exists
- Understanding of appropriate HTTP status code

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Error type | Yes | Domain error class name |
| HTTP status | Yes | HTTP status code to return |
| Response type | No | Custom response type (optional) |

## Outputs

- Error mapping registration
- Response type (if new)

## Execution Steps

### Step 1: Create Domain Error (if new)

```csharp
// In Domain/Errors/
namespace {YourProject}.Domain.Errors;

public class RateLimitExceededError : BaseError
{
    public int RetryAfterSeconds { get; }

    public RateLimitExceededError(string message, int retryAfterSeconds = 60) 
        : base(message)
    {
        RetryAfterSeconds = retryAfterSeconds;
    }
}
```

### Step 2: Create Response Type (if custom needed)

```csharp
// In Domain/Contracts/Responses/
public class RateLimitResponse
{
    public string Message { get; init; }
    public int RetryAfterSeconds { get; init; }
}
```

### Step 3: Register Mapping (API)

```csharp
// In Startup.cs or Extensions/ErrorMappingExtensions.cs
services.AddErrorMappings(mappings =>
{
    // Existing mappings...
    
    // Add new mapping
    mappings.Map<RateLimitExceededError>()
        .To<RateLimitResponse>(StatusCodes.Status429TooManyRequests)
        .AfterMap((error, response, context) =>
        {
            // Add Retry-After header
            context.HttpContext?.Response.Headers.Add(
                "Retry-After", 
                ((RateLimitExceededError)error).RetryAfterSeconds.ToString());
        });
});
```

### Step 4: Register Mapping (Functions)

```csharp
// In Startup.ErrorMapping.cs
public static IServiceCollection AddErrorMappings(this IServiceCollection services)
{
    services.AddErrorMappings(mappings =>
    {
        // Existing mappings...
        
        mappings.Map<RateLimitExceededError>()
            .To<RateLimitResponse>(StatusCodes.Status429TooManyRequests)
            .AfterMap((error, response, context) =>
            {
                context.HttpContext?.Items.Add(
                    RequestLoggerFilter.ResponseBodyType,
                    typeof(RateLimitResponse));
            });
    });
    
    return services;
}
```

## Standard Mapping Reference

| Error Type | HTTP Status | Response Type |
|------------|-------------|---------------|
| NotFoundError | 404 | NotFoundResponse |
| InvalidInputError | 400 | BadRequestResponse |
| InvalidInputDetailedError | 400 | BadRequestResponse |
| UnauthorizedError | 401 | UnauthorizedResponse |
| ForbiddenError | 403 | ForbiddenResponse |
| ConflictError | 409 | ConflictResponse |
| BaseError (fallback) | 500 | InternalErrorResponse |

## Checklist

- [ ] Domain error created (inherits from BaseError)
- [ ] Response type created (if custom)
- [ ] Mapping registered in API project
- [ ] Mapping registered in Functions project (if used)
- [ ] AfterMap hook added for telemetry
- [ ] HTTP headers added if needed (e.g., Retry-After)

## Common Mistakes

| Mistake | Consequence |
|---------|-------------|
| Forgetting to register mapping | Runtime exception |
| Missing AfterMap for telemetry | Lost tracking data |
| Wrong status code | API contract violation |
| Not updating both API & Functions | Inconsistent behavior |

## Related Skills

- [Create Provider](../create-provider/skill.md)
- [Create Endpoint](../create-endpoint/skill.md)

## Example Invocation

```
Add error mapping for expired token:
- Error: TokenExpiredError
- Status: 401 Unauthorized
- Header: WWW-Authenticate with "Bearer error=expired_token"
```
