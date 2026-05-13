# Go — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through `go test`. Tests are
deterministic, race-checked, and never reach the network.

## Runner

- `go test ./...` is the canonical command.
- `-race` always enabled in CI; locally during TDD too unless test
  performance is a problem.
- `gotestsum` optional for richer output; not required.

## Layout

- Co-locate test files: `markets/market.go` paired with
  `markets/market_test.go`.
- External tests live in package `markets_test` to enforce the public
  API surface; internal tests stay in `markets`.
- Test fixtures under `markets/testdata/` — `go test` skips this
  directory automatically.

## Naming

- File: `<unit>_test.go`.
- Function: `TestUpperCamel` for unit tests, `BenchmarkX` for benches,
  `ExampleX` for runnable docs.
- Sub-tests: `t.Run("descriptive name", func(t *testing.T) { ... })`.

## RED → GREEN → REFACTOR

1. **RED** — write the failing test. Run `go test ./markets/ -run
   TestX -v`. Confirm the failure message matches the assertion.
2. **GREEN** — minimum code to pass. Do not modify the test.
3. **REFACTOR** — clean up; suite stays green.

## Table-driven tests

The idiomatic Go pattern:

```go
func TestParse(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    Market
        wantErr bool
    }{
        {"empty", "", Market{}, true},
        {"simple", `{"symbol":"BTC"}`, Market{Symbol: "BTC"}, false},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()
            got, err := Parse(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("Parse(%q): err=%v wantErr=%v", tt.input, err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("Parse(%q) = %+v, want %+v", tt.input, got, tt.want)
            }
        })
    }
}
```

## Flags

- `-run <regex>` filter by test name.
- `-v` verbose output.
- `-count=1` defeats the test cache when you need a fresh run.
- `-cover` coverage; combine with `-coverprofile=c.out` and
  `go tool cover -html=c.out`.
- `-race` data-race detector; non-negotiable in CI.

## Helpers

- `t.Helper()` in helper functions so failure points to the caller.
- `t.Cleanup()` over `defer` for teardown; runs in LIFO order, even
  on `t.Fatal`.
- `t.TempDir()` for filesystem isolation.

## Mocks

- Prefer interfaces + small fakes over mock generators.
- When a generator is justified: `mockgen` (gomock) or `moq`. Pin the
  version in `tools/tools.go`.

## Coverage

- `go test -cover ./...`.
- Floor: 80 % statement coverage on touched files.
