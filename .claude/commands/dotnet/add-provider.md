---
description: Create a new .NET provider with interface, implementation, and tests
---

## Context

Scaffolds a new provider layer component following the project's layered architecture pattern (Controller → Provider → Service).

## Inputs

$ARGUMENTS - Provider name and the service it wraps (e.g., "Order OrderService")

## Steps

### 1. Parse Arguments

Extract:
- **Provider name** (e.g., `Order` → `OrderProvider`)
- **Service name** (e.g., `OrderService`)

### 2. Read Standards

Read `standards/dotnet.md` for naming, Result pattern, and DI conventions.

### 3. Create Interface

```csharp
public interface I{Name}Provider
{
    Task<Result<{Response}>> {Method}Async({Request} request, CancellationToken cancellationToken);
}
```

### 4. Create Implementation

```csharp
public class {Name}Provider : I{Name}Provider
{
    private readonly I{Service} _{service};

    public {Name}Provider(I{Service} {service})
    {
        _{service} = {service};
    }

    public async Task<Result<{Response}>> {Method}Async({Request} request, CancellationToken cancellationToken)
    {
        Result<{Entity}> result = await _{service}.{Method}Async(request, cancellationToken);

        if (result.IsError)
        {
            return result.Error;
        }

        return new {Response}(result.Value);
    }
}
```

### 5. Register DI

Add scoped registration: `services.AddScoped<I{Name}Provider, {Name}Provider>();`

### 6. Generate Tests

Create tests for happy path and error path using Result pattern.

### 7. Verify

Run `dotnet build` and `dotnet test`.

## Verification

- Builds without errors
- Tests pass
- DI registration complete
- Result pattern correctly implemented
