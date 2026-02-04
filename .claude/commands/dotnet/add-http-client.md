---
description: Create a typed HTTP client with DelegatingHandler and DI registration
---

## Context

Scaffolds a typed HTTP client for calling external APIs, including the client interface, implementation, DelegatingHandler for cross-cutting concerns, and DI registration.

## Inputs

$ARGUMENTS - Client name and base URL (e.g., "PaymentGateway https://api.payment.com")

## Steps

### 1. Parse Arguments

Extract:
- **Client name** (e.g., `PaymentGateway`)
- **Base URL** (e.g., `https://api.payment.com`)

### 2. Read Standards

Read `standards/dotnet.md` for HTTP client patterns and DelegatingHandler usage.

### 3. Create Client Interface

```csharp
public interface I{Name}Client
{
    Task<Result<{Response}>> {Method}Async({Request} request, CancellationToken cancellationToken);
}
```

### 4. Create Client Implementation

```csharp
public class {Name}Client : I{Name}Client
{
    private readonly HttpClient _httpClient;

    public {Name}Client(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }
}
```

### 5. Create DelegatingHandler

```csharp
public class {Name}DelegatingHandler : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        // Add headers, logging, retry logic
        return await base.SendAsync(request, cancellationToken);
    }
}
```

### 6. Register DI

```csharp
services.AddTransient<{Name}DelegatingHandler>();
services.AddHttpClient<I{Name}Client, {Name}Client>(client =>
{
    client.BaseAddress = new Uri(configuration["{Name}:BaseUrl"]);
})
.AddHttpMessageHandler<{Name}DelegatingHandler>();
```

### 7. Add Configuration

Add to `appsettings.json`:
```json
"{Name}": {
  "BaseUrl": "{baseUrl}"
}
```

### 8. Generate Tests

Test client methods with mocked `HttpMessageHandler`.

### 9. Verify

Run `dotnet build` and `dotnet test`.

## Verification

- Builds without errors
- Tests pass
- DI registration uses `AddHttpClient`
- DelegatingHandler registered
- Configuration section added
