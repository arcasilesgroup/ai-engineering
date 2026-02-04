# ADR-001: Result Pattern for Error Handling

## Status

**Accepted**

## Date

2024-06-15

## Context

The platform needed a consistent approach to error handling across all .NET services. Traditional exception-based error handling had several issues:

- Exceptions are expensive and intended for exceptional circumstances
- Flow control with try/catch leads to deeply nested code
- Error types are not visible in method signatures
- Easy to forget to handle errors

We needed a pattern that:
- Makes error handling explicit in the type system
- Supports functional composition
- Integrates well with ASP.NET Core
- Is consistent across all services

## Decision

We will use the **Result Pattern** (Railway-Oriented Programming) for explicit error handling.

**Implementation Options:**
- Create your own `Result<T>` type in a shared library
- Use [FluentResults](https://github.com/altmann/FluentResults)
- Use [ErrorOr](https://github.com/amantinband/error-or)

### Key Rules

1. **Services return `Result` or `Result<T>`** instead of throwing exceptions
2. **Always check `result.IsError`** before accessing `result.Value`
3. **Use early return pattern** for cleaner code flow
4. **Use implicit conversion** from domain errors
5. **Map errors to HTTP responses** using `ErrorMapper`

### Code Pattern

```csharp
public async Task<Result<UserResponse>> GetUserAsync(string userId)
{
    Result<User> userResult = await _userService.FindByIdAsync(userId);
    
    if (userResult.IsError)
        return userResult.Error;  // Implicit conversion
    
    User user = userResult.Value;
    return new UserResponse(user);  // Implicit conversion
}
```

## Consequences

### Positive

- Error handling is explicit and type-safe
- Method signatures clearly indicate possible failures
- Eliminates try/catch for business logic flow
- Consistent pattern across all services
- Better testability

### Negative

- Learning curve for developers unfamiliar with functional patterns
- Slight verbosity compared to happy-path-only code
- Need to ensure all code paths check `IsError`

### Neutral

- Requires shared library or third-party package
- Need to update error mappings for new error types

## Related

- [ADR-002: Error Mapping Strategy](./ADR-002-error-mapping.md)
- [Result Pattern Standards](../../standards/dotnet/patterns/result-pattern.md)
