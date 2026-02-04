# Skill: Create API Endpoint

---
id: dotnet/create-endpoint
name: Create API Endpoint
complexity: medium
estimated_time: 5-10 minutes
---

## Description

Creates a versioned ASP.NET Core API endpoint following project conventions including error mapping, Result pattern, and proper HTTP semantics.

## Prerequisites

- Existing controller or decision to create new controller
- Understanding of the resource being exposed
- Knowledge of required request/response models

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Endpoint name | Yes | Action method name (e.g., `GetUser`) |
| HTTP method | Yes | GET, POST, PUT, DELETE, PATCH |
| Route | Yes | URL path (e.g., `/users/{userId}`) |
| API version | Yes | Version namespace (e.g., `V1`, `V2`) |
| Request model | Conditional | Required for POST/PUT/PATCH |
| Response model | Yes | Return type for success case |
| Error scenarios | Yes | Possible error types |

## Outputs

- Controller action method
- Request DTO (if needed)
- Response DTO (if needed)
- Error mapping registration (if new errors)
- Provider method (if business logic needed)

## Execution Steps

### Step 1: Determine Controller Location

```
src/{YourProject}/Controllers/V{version}/{Feature}Controller.cs
```

Decide: New controller or add to existing?

### Step 2: Create/Update Request Model (if POST/PUT/PATCH)

```csharp
// In Domain/Contracts/Requests/
public class CreateUserRequest
{
    [Required]
    [StringLength(100)]
    public required string Name { get; init; }
    
    [Required]
    [EmailAddress]
    public required string Email { get; init; }
}
```

### Step 3: Create/Update Response Model

```csharp
// In Domain/Contracts/Responses/
public class UserResponse
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string Email { get; init; }
    public DateTime CreatedAt { get; init; }
}
```

### Step 4: Create Controller Action

```csharp
/// <summary>
/// Gets a user by ID.
/// </summary>
/// <param name="userId">The user identifier.</param>
/// <returns>The user details.</returns>
[HttpGet("{userId}")]
[ProducesResponseType(typeof(UserResponse), StatusCodes.Status200OK)]
[ProducesResponseType(typeof(NotFoundResponse), StatusCodes.Status404NotFound)]
[ProducesResponseType(typeof(BadRequestResponse), StatusCodes.Status400BadRequest)]
public async Task<IActionResult> GetUser(string userId)
{
    Result<UserResponse> result = await _provider.GetUserAsync(userId);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}
```

### Step 5: Create/Update Provider Method

```csharp
public async Task<Result<UserResponse>> GetUserAsync(string userId)
{
    if (string.IsNullOrEmpty(userId))
        return new InvalidInputError("User ID is required");
    
    Result<User> userResult = await _userService.GetByIdAsync(userId);
    if (userResult.IsError)
        return userResult.Error;
    
    User user = userResult.Value;
    return new UserResponse
    {
        Id = user.Id,
        Name = user.Name,
        Email = user.Email,
        CreatedAt = user.CreatedAt
    };
}
```

### Step 6: Register Error Mappings (if new errors)

Check `Startup.ErrorMapping.cs` for any missing mappings.

### Step 7: Add Unit Tests

Create test file following `BaseTest` pattern.

## Checklist

- [ ] Controller action created with correct attributes
- [ ] Route follows kebab-case convention
- [ ] All `ProducesResponseType` attributes present
- [ ] Result pattern used correctly (check before access)
- [ ] Request validation attributes applied
- [ ] Response model has `required` on mandatory properties
- [ ] Error mappings registered
- [ ] Provider method follows early return pattern
- [ ] Unit tests created
- [ ] XML documentation added

## Anti-patterns to Avoid

| Don't | Do Instead |
|-------|------------|
| Access `result.Value` without check | Check `result.IsError` first |
| Use try/catch for flow control | Use Result pattern |
| Return generic error messages | Return specific domain errors |
| Skip `ProducesResponseType` | Document all possible responses |

## Related Skills

- [Create Provider](../create-provider/skill.md)
- [Add Error Mapping](../add-error-mapping/skill.md)
- [Generate Tests](../generate-tests/skill.md)

## Example Invocation

```
Create a GET endpoint to retrieve API deprecation status:
- Route: /apis/{apiId}/deprecation-status
- Response: DeprecationStatusResponse with status, date, replacementApiId
- Errors: NotFoundError if API doesn't exist
- Version: V1
```
