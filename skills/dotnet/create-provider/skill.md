# Skill: Create Business Provider

---
id: dotnet/create-provider
name: Create Business Provider
complexity: low
estimated_time: 5 minutes
---

## Description

Creates a Provider class that orchestrates business logic by coordinating multiple services. Providers sit between Controllers and Services in the architecture.

## Prerequisites

- Understanding of the business functionality
- Knowledge of required services

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Provider name | Yes | Feature name (e.g., `User`, `Order`) |
| Services needed | Yes | List of services to inject |
| Methods | Yes | Public methods to implement |

## Outputs

- Provider interface (`I{Feature}Provider`)
- Provider implementation (`{Feature}Provider`)
- DI registration

## Execution Steps

### Step 1: Create Interface

```csharp
// In Business/Interfaces/
namespace {YourProject}.Business.Interfaces;

public interface IUserProvider
{
    Task<Result<UserResponse>> GetUserAsync(string userId);
    Task<Result<UsersResponse>> GetAllUsersAsync(int pageSize = 20);
    Task<Result<UserResponse>> CreateUserAsync(CreateUserRequest request);
}
```

### Step 2: Create Implementation

```csharp
// In Business/Providers/
namespace {YourProject}.Business.Providers;

public class UserProvider : IUserProvider
{
    private readonly IUserService _userService;
    private readonly INotificationService _notificationService;
    private readonly ILogger<UserProvider> _logger;

    public UserProvider(
        IUserService userService,
        INotificationService notificationService,
        ILogger<UserProvider> logger)
    {
        _userService = userService;
        _notificationService = notificationService;
        _logger = logger;
    }

    public async Task<Result<UserResponse>> GetUserAsync(string userId)
    {
        _logger.LogMethodExecutionStart();

        if (string.IsNullOrEmpty(userId))
            return new InvalidInputError("User ID is required");

        Result<User> userResult = await _userService.GetByIdAsync(userId);
        if (userResult.IsError)
            return userResult.Error;

        User user = userResult.Value;
        
        _logger.LogInformation("Retrieved user {UserId}", userId);
        
        return new UserResponse
        {
            Id = user.Id,
            Name = user.Name,
            Email = user.Email
        };
    }

    public async Task<Result<UserResponse>> CreateUserAsync(CreateUserRequest request)
    {
        _logger.LogMethodExecutionStart();

        // Create user
        Result<User> createResult = await _userService.CreateAsync(request);
        if (createResult.IsError)
            return createResult.Error;

        User user = createResult.Value;

        // Send notification (non-critical, log but don't fail)
        Result notifyResult = await _notificationService.SendWelcomeAsync(user.Email);
        if (notifyResult.IsError)
        {
            _logger.LogWarning("Failed to send welcome email: {Error}", 
                notifyResult.Error.Message);
        }

        return new UserResponse
        {
            Id = user.Id,
            Name = user.Name,
            Email = user.Email
        };
    }
}
```

### Step 3: Register in DI

```csharp
// In Extensions/DependencyInjectionExtensions.cs
public static IServiceCollection AddBusinessDependencies(this IServiceCollection services)
{
    services.AddScoped<IUserProvider, UserProvider>();
    // ... other providers
    return services;
}
```

## Checklist

- [ ] Interface created with Result return types
- [ ] Implementation injects required services
- [ ] Logger injected and used
- [ ] Methods use early return pattern
- [ ] Logging at method start with `LogMethodExecutionStart`
- [ ] Business events logged at Information level
- [ ] DI registration added
- [ ] Unit tests created

## Provider Responsibilities

### Do in Providers

- ✅ Orchestrate multiple services
- ✅ Apply business rules
- ✅ Transform service results to responses
- ✅ Handle caching decisions
- ✅ Log business events

### Don't in Providers

- ❌ Direct HTTP calls (use Services)
- ❌ Direct database access (use Repositories)
- ❌ Complex validation (use FluentValidation)
- ❌ Response formatting for HTTP (Controllers do this)

## Related Skills

- [Create Endpoint](../create-endpoint/skill.md)
- [Generate Tests](../generate-tests/skill.md)

## Example Invocation

```
Create a provider for order processing:
- Name: OrderProcessing
- Services: IOrderService, IPaymentService, INotificationService
- Methods:
  - ProcessOrderAsync(string orderId, ProcessOrderRequest request)
  - GetOrderStatusAsync(string orderId)
```
