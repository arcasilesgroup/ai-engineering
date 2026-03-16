# Go Review Guidelines

## Update Metadata
- Rationale: Go-specific patterns for error handling, concurrency, and interface design.

## Idiomatic Patterns
- Always check errors — never `_` for error returns.
- Wrap errors with context: `fmt.Errorf("operation failed: %w", err)`.
- Small, focused interfaces: prefer `io.Reader` over large interface contracts.
- Use `context.Context` as first parameter for cancellation and deadlines.
- `defer` for cleanup — but beware of defer in loops.

## Performance Anti-Patterns
- **Goroutine leaks**: Always use `sync.WaitGroup` or `context` for lifecycle management.
- **Channel misuse**: Unbuffered channels blocking unexpectedly.
- **Map iteration in hot paths**: Maps are not ordered — don't depend on iteration order.

## Security Patterns
- Validate `context.Context` is not `nil` before use.
- Use `crypto/rand` for security-sensitive randomness, not `math/rand`.
- Set timeouts on all HTTP clients — no infinite waits.

## Testing Patterns
- Table-driven tests with `t.Run()` for subtests.
- Use `t.Helper()` in test helpers for clean stack traces.
- `httptest.NewServer()` for HTTP integration tests.

## Self-Challenge Questions
- Is the goroutine properly managed with WaitGroup or context?
- Does the error wrapping preserve the original error for `errors.Is()`?

## References
- Enforcement: `standards/framework/stacks/go.md` (if exists)
