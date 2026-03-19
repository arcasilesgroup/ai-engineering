## Go Best Practices

### Error Handling

**Explicit error checking:**

- Check every error, don't ignore with `_`
- Return errors, don't panic
- Wrap errors with context: `fmt.Errorf("failed to process: %w", err)`
- Use `errors.Is()` and `errors.As()` for error checking

**Pattern:**

```go
// ✅ GOOD: Proper error handling
result, err := doSomething()
if err != nil {
    return fmt.Errorf("do something failed: %w", err)
}

// ❌ BAD: Ignoring errors
result, _ := doSomething()
```text

### Goroutines and Concurrency

**Safe concurrency:**

- Always handle goroutine cleanup (use context or done channel)
- Use `sync.WaitGroup` to wait for goroutines
- Protect shared state with `sync.Mutex` or channels
- Prefer channels for communication, mutexes for state protection
- Close channels from sender side only

**Patterns:**

```go
// ✅ GOOD: Using WaitGroup
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()

// ✅ GOOD: Context for cancellation
ctx, cancel := context.WithCancel(context.Background())
defer cancel()
```text

**Common mistakes:**

```go
// ❌ BAD: Goroutine leak (no way to stop)
go func() {
    for {
        // Never exits
    }
}()

// ❌ BAD: Range variable capture
for _, item := range items {
    go func() {
        process(item)  // All goroutines use last item
    }()
}

// ✅ GOOD: Pass as parameter
for _, item := range items {
    go func(i Item) {
        process(i)
    }(item)
}
```text

### Defer, Panic, Recover

**Defer usage:**

- Use `defer` for cleanup (close files, unlock mutexes)
- Deferred functions run in LIFO order
- Be careful with defer in loops (accumulates)

**Panic and recover:**

- Use panic only for unrecoverable errors
- Recover only in library boundary or server handlers
- Don't use panic/recover for normal control flow

### Interfaces

**Interface design:**

- Keep interfaces small (often just 1-2 methods)
- Accept interfaces, return structs
- Define interfaces where they're used (consumer side)
- Use `io.Reader`/`io.Writer` for streaming data

**Pattern:**

```go
// ✅ GOOD: Small, focused interface
type Repository interface {
    Save(user User) error
    Get(id string) (User, error)
}

// ❌ BAD: Kitchen sink interface
type Repository interface {
    // 20 methods
}
```text

### Pointers vs Values

**When to use pointers:**

- Large structs (avoid copying)
- Need to modify the receiver
- Consistency (if some methods need pointer, all use pointer)

**Pattern:**

```go
// ✅ Use pointer for modification
func (u *User) SetName(name string) {
    u.Name = name
}

// ✅ Use value for read-only, small types
func (p Point) Distance() float64 {
    return math.Sqrt(p.X*p.X + p.Y*p.Y)
}
```text

### Naming Conventions

**Go style:**

- `camelCase` for unexported, `PascalCase` for exported
- Short variable names in small scopes: `i`, `err`, `ctx`
- Descriptive names in larger scopes
- No `get` prefix for getters: `user.Name()` not `user.GetName()`
- Use `New` prefix for constructors: `NewClient()`

### Package Organization

**Best practices:**

- One package per directory
- Organize by domain, not by layer (not `models/`, `controllers/`)
- Keep `main` package minimal
- Avoid circular dependencies
- Use internal/ for private packages

### Slices and Maps

**Common patterns:**

```go
// ✅ GOOD: Pre-allocate if size known
users := make([]User, 0, len(items))

// ✅ GOOD: Check map existence
if val, ok := myMap[key]; ok {
    // Use val
}

// ❌ BAD: Modifying slice while iterating
for i, item := range items {
    items = append(items, newItem)  // Undefined behavior
}
```text

### Context Usage

**Best practices:**

- First parameter in functions: `func Do(ctx context.Context, ...)`
- Pass down the call stack, don't store in structs
- Use for cancellation, deadlines, and request-scoped values
- Don't pass `nil` context, use `context.Background()` or `context.TODO()`

### Testing

**Go testing patterns:**

- Table-driven tests for multiple cases
- Use `t.Helper()` in test helpers
- Use `t.Parallel()` for parallel test execution
- Avoid test setup in `init()`

**Pattern:**

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.want {
                t.Errorf("got %d, want %d", got, tt.want)
            }
        })
    }
}
```text

### Common Anti-Patterns

**Avoid:**

- Empty interface (`interface{}`) when type can be specified
- Premature optimization
- Ignoring errors
- Using `panic` for normal error handling
- Global variables (use dependency injection)
- init() for anything complex
