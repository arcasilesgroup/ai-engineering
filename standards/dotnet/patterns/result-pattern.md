# Result Pattern

> Railway-oriented programming for explicit error handling.

---

## Overview

The Result Pattern provides type-safe error handling without exceptions. It wraps operations that can fail, making success and failure paths explicit in the type system.

**Implementation Options:**
- Create your own `Result<T>` type (see example below)
- Use a library like [FluentResults](https://github.com/altmann/FluentResults)
- Use [ErrorOr](https://github.com/amantinband/error-or)

---

## Core Types

```csharp
// For operations with a return value
Result<T>

// For operations without a return value
Result
```

---

## Basic Usage

### Returning Success

```csharp
public Result<User> GetUser(string id)
{
    User user = _repository.Find(id);
    return user;  // Implicit conversion to Result<User>.Success(user)
}

public Result SaveUser(User user)
{
    _repository.Save(user);
    return Result.Success();
}
```

### Returning Errors

```csharp
public Result<User> GetUser(string id)
{
    if (string.IsNullOrEmpty(id))
        return new InvalidInputError("User ID is required");  // Implicit conversion
    
    User? user = _repository.Find(id);
    if (user is null)
        return new NotFoundError($"User {id} not found");
    
    return user;
}
```

---

## ⚠️ CRITICAL: Always Check Before Accessing Value

```csharp
// ❌ DANGEROUS: Will throw InvalidOperationException if IsError is true
Result<User> result = await GetUserAsync(id);
User user = result.Value;  // NEVER DO THIS

// ✅ SAFE: Always check first
Result<User> result = await GetUserAsync(id);
if (result.IsError)
    return result.Error;

User user = result.Value;  // Safe to access after check
```

---

## Early Return Pattern (Preferred)

The early return pattern keeps code flat and readable:

```csharp
public async Task<Result<OrderResponse>> ProcessOrderAsync(string orderId, string customerId)
{
    // Validate input
    if (string.IsNullOrEmpty(orderId))
        return new InvalidInputError("Order ID is required");
    
    // Get customer
    Result<Customer> customerResult = await _customerService.GetAsync(customerId);
    if (customerResult.IsError)
        return customerResult.Error;
    
    // Get order
    Result<Order> orderResult = await _orderService.GetAsync(orderId);
    if (orderResult.IsError)
        return orderResult.Error;
    
    // Business logic with valid values
    Customer customer = customerResult.Value;
    Order order = orderResult.Value;
    
    if (!order.BelongsTo(customer))
        return new ForbiddenError("Order does not belong to customer");
    
    // Process and return
    OrderResponse response = CreateResponse(order, customer);
    return response;
}
```

---

## Domain Error Types

| Error Type | HTTP Status | Use Case |
|------------|-------------|----------|
| `NotFoundError` | 404 | Resource doesn't exist |
| `InvalidInputError` | 400 | Simple validation failure |
| `InvalidInputDetailedError` | 400 | Validation with field details |
| `UnauthorizedError` | 401 | Authentication required |
| `ForbiddenError` | 403 | Insufficient permissions |
| `ConflictError` | 409 | State conflict |
| `InternalError` | 500 | Unexpected failures |

### Creating Errors

```csharp
// Simple errors
new NotFoundError("User not found");
new InvalidInputError("Invalid email format");

// Error with details
new InvalidInputDetailedError("Validation failed", new[]
{
    new ValidationError("Email", "Invalid format"),
    new ValidationError("Age", "Must be positive")
});

// With inner exception (for logging)
new InternalError("Database operation failed", exception);
```

---

## Implicit Conversions

The Result pattern supports implicit conversions for cleaner code:

```csharp
// Value to Result<T>
public Result<User> GetUser() => new User();  // Works!

// Error to Result<T>
public Result<User> GetUser() => new NotFoundError("...");  // Works!

// Result<T>.Error to different Result<T>
Result<Customer> customerResult = await GetCustomerAsync();
if (customerResult.IsError)
    return customerResult.Error;  // Returns Result<Order> with same error
```

---

## Method Chaining (Advanced)

For simple transformations, use `Bind` and `Map`:

```csharp
// Map: Transform value without additional error handling
Result<UserDto> dtoResult = userResult.Map(user => new UserDto(user));

// Bind: Chain operations that can fail
Result<Order> orderResult = await customerResult
    .Bind(customer => GetPrimaryOrderAsync(customer));
```

### Bind Lambda Parameter Rule

⚠️ Always declare the lambda parameter, even if unused:

```csharp
// ✅ CORRECT: Parameter declared
result.Bind(version => GetNextStepAsync());

// ❌ WRONG: Compiler cannot infer generic types
result.Bind(_ => GetNextStepAsync());
```

---

## Controller Integration

Use `ToActionResult` extension for clean controller code:

```csharp
[HttpGet("{id}")]
public async Task<IActionResult> GetUser(string id)
{
    Result<UserResponse> result = await _provider.GetUserAsync(id);
    return result.ToActionResult(_errorMapper, response => Ok(response));
}

[HttpDelete("{id}")]
public async Task<IActionResult> DeleteUser(string id)
{
    Result result = await _provider.DeleteUserAsync(id);
    return result.ToActionResult(_errorMapper, () => NoContent());
}
```

---

## Anti-Patterns

### ❌ Using Try/Catch for Flow Control

```csharp
// ❌ BAD
try
{
    var user = await _service.GetUserAsync(id);
    return Ok(user);
}
catch (NotFoundException ex)
{
    return NotFound(ex.Message);
}

// ✅ GOOD
Result<User> result = await _service.GetUserAsync(id);
return result.ToActionResult(_errorMapper, user => Ok(user));
```

### ❌ Checking Result After Accessing Value

```csharp
// ❌ BAD: Value accessed before check
var user = result.Value;
if (result.IsError)
    return result.Error;

// ✅ GOOD: Check first
if (result.IsError)
    return result.Error;
var user = result.Value;
```

### ❌ Nested If Statements

```csharp
// ❌ BAD: Deep nesting
if (!customerResult.IsError)
{
    if (!orderResult.IsError)
    {
        // Deep nesting
    }
}

// ✅ GOOD: Early returns
if (customerResult.IsError)
    return customerResult.Error;
if (orderResult.IsError)
    return orderResult.Error;
// Flat code continues
```
