# ADR-002: Error Mapping Strategy

## Status

**Accepted**

## Date

2024-06-15

## Context

With the Result Pattern adopted (ADR-001), we needed a consistent way to convert domain errors into HTTP responses. Each API endpoint could return different types of errors, and we wanted:

- Centralized error-to-response mapping
- Consistent HTTP status codes
- Structured error responses (Problem Details format)
- Automatic telemetry tagging

## Decision

We will implement centralized **Error Mapping** to convert domain errors to HTTP responses.

**Implementation Options:**
- Create an `IErrorMapper` interface in a shared library
- Use ASP.NET Core's built-in ProblemDetails
- Implement a middleware-based approach

### Configuration

Register mappings in `Startup.cs`:

```csharp
services.AddErrorMappings(mappings =>
{
    mappings.Map<NotFoundError>().To<NotFoundResponse>(StatusCodes.Status404NotFound);
    mappings.Map<InvalidInputError>().To<BadRequestResponse>(StatusCodes.Status400BadRequest);
    mappings.Map<InvalidInputDetailedError>().To<BadRequestResponse>(StatusCodes.Status400BadRequest);
    // ... additional mappings
});
```

### Usage in Controllers

```csharp
public async Task<IActionResult> GetUser(string id)
{
    Result<UserResponse> result = await _provider.GetUserAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}
```

### Standard Mappings

| Domain Error | HTTP Status | Response Type |
|--------------|-------------|---------------|
| NotFoundError | 404 | NotFoundResponse |
| InvalidInputError | 400 | BadRequestResponse |
| InvalidInputDetailedError | 400 | BadRequestResponse |
| UnauthorizedError | 401 | UnauthorizedResponse |
| ForbiddenError | 403 | ForbiddenResponse |
| ConflictError | 409 | ConflictResponse |
| BaseError (fallback) | 500 | InternalErrorResponse |

## Consequences

### Positive

- Centralized, consistent error responses
- Automatic Problem Details format
- Telemetry integration
- Easy to extend for new error types

### Negative

- Must remember to register new error types
- Runtime error if mapping is missing

### Neutral

- Error types must inherit from BaseError

## Related

- [ADR-001: Result Pattern](./ADR-001-result-pattern.md)
- [Error Mapping Standards](../../standards/dotnet/patterns/error-mapping.md)
