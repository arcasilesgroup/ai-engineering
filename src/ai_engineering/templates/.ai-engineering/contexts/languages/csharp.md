## C# Best Practices

### Modern C# Features

**Prefer modern syntax:**

- Use `var` for obvious types, explicit types when clarity needed
- Use expression-bodied members: `public int Age => _age;`
- Use pattern matching instead of type checking + casting
- Use null-coalescing: `??` and null-conditional: `?.`
- Use collection expressions: `int[] numbers = [1, 2, 3];` (C# 12+)

**Nullable reference types (C# 8+):**

- Enable nullable reference types in project
- Use `?` suffix for nullable types: `string? name`
- Avoid `!` (null-forgiving operator) unless absolutely necessary
- Check for null explicitly when needed

### Async/Await Patterns

**Proper async usage:**

- Always use `async`/`await`, never `.Result` or `.Wait()` (causes deadlocks)
- Use `ConfigureAwait(false)` in libraries to avoid context capture
- Return `Task` not `async void` (except event handlers)
- Use `ValueTask<T>` for hot paths that often complete synchronously

**Anti-patterns:**

```csharp
// ❌ BAD: Blocking async code
var result = SomeAsyncMethod().Result;  // Deadlock risk

// ✅ GOOD: Proper async
var result = await SomeAsyncMethod();

// ❌ BAD: Async void
public async void ProcessData() { }

// ✅ GOOD: Return Task
public async Task ProcessDataAsync() { }
```text

### LINQ Best Practices

**Efficient LINQ:**

- Prefer `Any()` over `Count() > 0`
- Use `First()` when you expect element, `FirstOrDefault()` when maybe not
- Avoid multiple enumeration - materialize once with `ToList()`/`ToArray()` if needed
- Use `Where()` before `OrderBy()` to reduce sorting work

**Common mistakes:**

```csharp
// ❌ BAD: Multiple enumeration
if (items.Any()) {
    foreach (var item in items.Where(x => x.Active)) { }
}

// ✅ GOOD: Single enumeration
var activeItems = items.Where(x => x.Active).ToList();
if (activeItems.Any()) {
    foreach (var item in activeItems) { }
}
```text

### Dispose Pattern

**IDisposable implementation:**

- Implement `IDisposable` for unmanaged resources
- Use `using` statements for automatic disposal
- Consider `IAsyncDisposable` for async cleanup (C# 8+)
- Use `using var` declarations for scope-based disposal (C# 8+)

**Pattern:**

```csharp
// ✅ GOOD: using statement
using (var connection = new SqlConnection(connectionString)) {
    // Use connection
}

// ✅ BETTER: using declaration (C# 8+)
using var connection = new SqlConnection(connectionString);
// Disposed at end of scope
```text

### Exception Handling

**Best practices:**

- Catch specific exceptions, not `Exception`
- Don't swallow exceptions without logging
- Use exception filters: `catch (Exception ex) when (ex.InnerException != null)`
- Throw exceptions, don't return error codes

**Anti-patterns:**

```csharp
// ❌ BAD: Catching and ignoring
try { } catch { }

// ❌ BAD: Rethrowing loses stack trace
catch (Exception ex) { throw ex; }

// ✅ GOOD: Rethrow preserves stack
catch (Exception ex) {
    Log(ex);
    throw;  // Preserves stack trace
}
```text

### Naming Conventions

**Follow .NET conventions:**

- PascalCase: Classes, methods, properties, public fields
- camelCase: Private fields (with `_` prefix), parameters, local variables
- UPPER_CASE: Constants only
- Avoid Hungarian notation (no `strName`, `intCount`)

### Performance

**Common optimizations:**

- Use `StringBuilder` for string concatenation in loops
- Use `Span<T>` and `Memory<T>` for zero-allocation scenarios
- Use `stackalloc` for small, temporary buffers
- Avoid boxing value types unnecessarily
- Use `struct` for small, immutable data (< 16 bytes)

**String handling:**

```csharp
// ❌ BAD: String concatenation in loop
string result = "";
foreach (var item in items) {
    result += item.ToString();
}

// ✅ GOOD: StringBuilder
var sb = new StringBuilder();
foreach (var item in items) {
    sb.Append(item);
}
```text

### Dependency Injection

**Constructor injection:**

- Prefer constructor injection over property injection
- Request interfaces, not concrete types
- Keep constructors focused on storing dependencies
- Avoid service locator pattern

### Records (C# 9+)

**When to use records:**

- Immutable data transfer objects (DTOs)
- Value objects in domain models
- Data that supports value-based equality

```csharp
// ✅ GOOD: Record for immutable data
public record User(string Name, string Email);

// Value equality works automatically
var user1 = new User("John", "john@example.com");
var user2 = new User("John", "john@example.com");
// user1 == user2 is true
```text

### Common Anti-Patterns

**Avoid:**

- Magic strings/numbers (use constants or enums)
- Large classes (> 500 lines)
- Deep inheritance hierarchies (prefer composition)
- Public fields (use properties)
- Mutating collections while iterating
- Using `goto` (almost never needed)
