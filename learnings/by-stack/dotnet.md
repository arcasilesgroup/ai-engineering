# .NET Learnings

Stack-specific learnings for C# / .NET / ASP.NET Core development.

---

## Result Pattern

### [2024-01] Accessing Result.Value Without Check

**Context:** Working with `Result<T>` return types
**Learning:** NEVER access `.Value` without checking `.IsError` first - throws `InvalidOperationException`
**Correct Pattern:**
```csharp
if (result.IsError) return result.Error;
var data = result.Value; // Safe now
```

---

### [2024-02] Bind Generic Type Inference

**Context:** Chaining Result operations with `.Bind()`
**Learning:** Declare lambda parameter explicitly: `version => ...` not `_ => ...`
**Rationale:** Compiler needs the parameter for `Bind<TSource, TDestination>()` overload resolution
```csharp
// ❌ Won't compile
.Bind(_ => GetNext())

// ✅ Works
.Bind(version => GetNext())
```

---

## Error Mapping

### [2024-01] Unregistered Error Types

**Context:** Returning new domain errors from providers
**Learning:** Always register new error types in `Startup.ErrorMapping.cs`
**Consequence:** Unregistered errors cause `ArgumentException: "Unable to find mapping for type"`

---

## HTTP Clients

### [2024-02] DependencyHandler is Mandatory

**Context:** Configuring typed HTTP clients
**Learning:** Always add `.AddHttpMessageHandler<DependencyHandler>()` for telemetry and resilience
**Consequence:** Missing handler = no distributed tracing, no standardized retry policies

---

## Options Pattern

### [2024-01] Required Members for Request Models

**Context:** Models sent TO external services
**Learning:** Use `required` keyword (C# 11+) for compile-time enforcement without exceptions
```csharp
public class CreateApiRequest
{
    public required string Name { get; init; }
    public required string Version { get; init; }
}
```

---

### [2024-01] Nullable for Response Models

**Context:** Models received FROM external services  
**Learning:** Use nullable properties to prevent deserialization failures
```csharp
public class ApiResponse
{
    public string? Name { get; init; }
    public string? Version { get; init; }
}
```

---

## Testing

### [2024-01] Dynamic Dates in Tests

**Context:** Tests with date/time dependencies
**Learning:** Use `DateTime.UtcNow.AddDays(X)` instead of fixed dates or time abstractions
**Rationale:** Keeps tests simple, no production code changes needed

---

### [2024-02] Shared SetUp for NUnit

**Context:** Reducing test boilerplate
**Learning:** Use `[SetUp]` for common mock creation, prefer `Assert.EnterMultipleScope()` over `Assert.Multiple()`
**Example:**
```csharp
using (Assert.EnterMultipleScope())
{
    Assert.That(result.IsError, Is.False);
    Assert.That(result.Value, Is.Not.Null);
}
```

---

## Serialization

### [2024-01] Newtonsoft.Json is Project Standard

**Context:** JSON serialization in API and Functions
**Learning:** Project uses Newtonsoft.Json with specific settings, not System.Text.Json
**Settings:**
```csharp
NullValueHandling.Ignore
StringEnumConverter
```
**Consequence:** Mixing STJ types causes inconsistencies

---

## Adding New Learnings

When a .NET-specific pattern emerges:

1. Add entry with date header
2. Include context, learning, and code examples
3. Reference related standards if applicable
4. Consider if it should also be in `copilot-instructions.md`
