---
name: "dotnet:add-error-mapping"
description: Add a new domain error type with HTTP status code mapping
disable-model-invocation: true
---

## Context

Creates a new domain error type and registers it in the error mapping configuration, following the Result pattern used in the project.

## Inputs

$ARGUMENTS - Error name, HTTP status code, and description (e.g., "OrderNotFound 404 Order was not found")

## Steps

### 1. Parse Arguments

Extract:
- **Error name** (e.g., `OrderNotFound` → `OrderNotFoundError`)
- **HTTP status code** (e.g., `404`)
- **Description** (e.g., "Order was not found")

### 2. Read Standards

Read `standards/dotnet.md` for error mapping patterns.

### 3. Create Error Class

```csharp
public class {Name}Error : IResultError
{
    public string Message { get; }

    public {Name}Error(string message = "{description}")
    {
        Message = message;
    }
}
```

### 4. Register Error Mapping

Add to error mapping configuration:

```csharp
mappings.Map<{Name}Error>()
    .To<ProblemDetails>(StatusCodes.Status{Code})
    .WithMapping((error, problemDetails) =>
    {
        problemDetails.Title = "{Human-readable title}";
        problemDetails.Detail = error.Message;
    });
```

### 5. Verify

- Run `dotnet build` to confirm compilation.
- Check that the error type is used correctly in existing Result returns.

## Verification

- Error class follows IResultError pattern
- Mapping registered with correct HTTP status code
- ProblemDetails format matches RFC 7807
- Build passes
