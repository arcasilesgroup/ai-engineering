# Handler: Language -- Go

## Purpose

Language-specific review for Go code. Supplements the 8-concern review agents with Go-idiomatic checks, concurrency safety patterns, and diagnostic tool integration.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Go Scope

1. Identify `.go` files in the diff
2. If no Go files, skip this handler entirely
3. Check `go.mod` for module path and Go version
4. Detect frameworks from imports:
   - `net/http` / `gin` / `echo` / `chi` -> enable HTTP handler checks
   - `database/sql` / `gorm` / `sqlx` -> enable database checks
   - `grpc` -> enable gRPC checks
5. Read `.ai-engineering/contexts/languages/go.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**SQL string concatenation**
```go
// BAD: SQL injection
db.Query("SELECT * FROM users WHERE id = '" + userID + "'")
db.Query(fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userID))

// GOOD: parameterized
db.Query("SELECT * FROM users WHERE id = $1", userID)
db.QueryRow("SELECT * FROM users WHERE id = ?", userID)
```

**Blank identifier discarding errors**
```go
// BAD: error silently ignored
result, _ := riskyOperation()
_ = file.Close() // in cases where close errors matter (writes)

// GOOD: handle the error
result, err := riskyOperation()
if err != nil {
    return fmt.Errorf("risky operation failed: %w", err)
}
```
- Confidence 90% for I/O, network, database operations
- Confidence 50% for known-safe operations (e.g., `fmt.Fprintf` to `bytes.Buffer`)

**panic() for recoverable errors**
```go
// BAD: crashes the process
if config == nil {
    panic("config is nil")
}

// GOOD: return error
if config == nil {
    return nil, fmt.Errorf("config must not be nil")
}
```
- Acceptable in `init()` functions and test helpers only

**Missing errors.Is / errors.As for error comparison**
```go
// BAD: breaks error wrapping
if err == sql.ErrNoRows {

// GOOD: unwraps wrapped errors
if errors.Is(err, sql.ErrNoRows) {
```

**Unchecked type assertions**
```go
// BAD: panics if wrong type
value := iface.(ConcreteType)

// GOOD: comma-ok pattern
value, ok := iface.(ConcreteType)
if !ok {
    return fmt.Errorf("expected ConcreteType, got %T", iface)
}
```

### Step 3 -- High Findings (severity: major)

**Goroutine leaks**
```go
// BAD: goroutine never terminates
go func() {
    for {
        data := <-ch // blocks forever if ch is never closed
        process(data)
    }
}()

// GOOD: context cancellation or done channel
go func() {
    for {
        select {
        case data, ok := <-ch:
            if !ok {
                return
            }
            process(data)
        case <-ctx.Done():
            return
        }
    }
}()
```

**Unbuffered channel deadlock potential**
- Sending on unbuffered channel without a guaranteed receiver
- Channel created but never read from in any visible code path

**Missing sync.WaitGroup for goroutine coordination**
- Multiple goroutines launched without WaitGroup, errgroup, or other synchronization
- Goroutines outliving the function that spawned them without lifecycle management

**Mutex misuse**
```go
// BAD: Lock without guaranteed Unlock
mu.Lock()
doWork() // if this panics, mutex stays locked

// GOOD: defer immediately
mu.Lock()
defer mu.Unlock()
doWork()
```
- Also flag: copying a mutex (passed by value instead of pointer)

**Missing error wrapping context**
```go
// BAD: no context
if err != nil {
    return err
}

// GOOD: context for debugging
if err != nil {
    return fmt.Errorf("loading user %d: %w", id, err)
}
```

### Step 4 -- Medium Findings (severity: minor)

**String building in loops**
```go
// BAD: O(n^2) string allocation
result := ""
for _, s := range items {
    result += s
}

// GOOD: strings.Builder
var b strings.Builder
for _, s := range items {
    b.WriteString(s)
}
result := b.String()
```

**Slice pre-allocation**
```go
// BAD: multiple reallocations
var result []Item
for _, raw := range rawItems {
    result = append(result, convert(raw))
}

// GOOD: pre-allocate
result := make([]Item, 0, len(rawItems))
for _, raw := range rawItems {
    result = append(result, convert(raw))
}
```

**Context as first parameter**
```go
// BAD: ctx not first
func ProcessOrder(order Order, ctx context.Context) error {

// GOOD: ctx first, per convention
func ProcessOrder(ctx context.Context, order Order) error {
```

**Table-driven tests**
- Test functions with repeated setup/assertion patterns -> suggest table-driven format
- Confidence 50% (style preference, not a bug)

**Exported functions missing doc comments**
- Per `go doc` conventions, exported names should have comments starting with the name

### Step 5 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| go vet | `go vet ./...` | Correctness findings (printf args, struct tags, unreachable code) |
| staticcheck | `staticcheck ./...` | Style, performance, correctness |
| go build -race | `go build -race ./...` | Data race findings |
| govulncheck | `govulncheck ./...` | Known vulnerabilities in dependencies |
| golangci-lint | `golangci-lint run` | Aggregated linting |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-go-N
    severity: critical|major|minor
    confidence: 0-100
    file: path
    line: N
    finding: "description"
    evidence: "code snippet"
    remediation: "how to fix"
    self_challenge:
      counter: "why this might be wrong"
      resolution: "why it stands or adjustment"
      adjusted_confidence: N
```
