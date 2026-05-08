<!-- source: contexts/languages/go.md @ affdef6d3235a65039813845a467340fa4f70803 -->

# Go — Build Conventions

Authoritative reference for the `ai-build` agent when generating Go
code. Distilled from `contexts/languages/go.md`.

## Toolchain

- **Go version**: latest stable (1.22+). Pin in `go.mod` `go` directive.
- **Module**: every repo is a module; `go workspaces` only when there
  are multi-module needs.
- **Linter**: `golangci-lint` with `staticcheck`, `errcheck`,
  `govet`, `revive`, `gosec` enabled.
- **Formatter**: `gofmt` is non-optional; CI runs `gofmt -l . && exit
  $?`.

## Layout

```
cmd/<binary>/main.go
internal/<domain>/...
pkg/<reusable>/...    # only when truly reusable
go.mod
go.sum
```

- `internal/` for everything you don't want imported externally.
- Organise by domain (`internal/markets/`), not by layer
  (no `models/`, `controllers/`).
- `cmd/` holds entry points only — no business logic.

## Naming

| Element | Convention | Example |
|---|---|---|
| Files | `lower_snake.go` | `market_repo.go` |
| Packages | single lowercase word | `markets` (not `market_data`) |
| Exported funcs / types | UpperCamel | `LookupMarket` |
| Internal | lowerCamel | `lookupCache` |
| Interfaces | noun + er suffix | `Reader`, `Lookuper` |
| Receivers | 1-2 letter | `m *Market`, not `market *Market` |

## Errors

- Always check; never `_` an error you intend to ignore.
- Wrap with `%w`: `fmt.Errorf("load market: %w", err)`.
- `errors.Is` / `errors.As` for typed checks; never `err.Error() ==
  "..."` string compare.
- Library code never `panic`s for expected failures. Return error.
- `recover()` only at goroutine boundary or top-level handler.

## Concurrency

- Pass `context.Context` as the first argument of any blocking call.
- Goroutines have a defined exit (context cancellation, channel
  close). No fire-and-forget without a supervisor.
- `sync.WaitGroup` for join; channels for hand-off; `sync.Mutex` for
  shared state.
- Don't capture range variables in goroutines (Go 1.22+ fixes the
  most common form, but pass explicitly anyway for clarity).

## Interfaces

- Define interfaces where they're consumed, not where the
  implementation lives.
- Small interfaces — 1-2 methods is ideal (`io.Reader`).
- Accept interfaces, return concrete types.

## Slices & maps

- Pre-allocate with `make([]T, 0, n)` when capacity is known.
- Never modify a slice while ranging over it.
- Always check map presence with the two-value form: `v, ok := m[k]`.

## Quality gate (pre-commit)

1. `gofmt -l .` (must be empty)
2. `go vet ./...`
3. `golangci-lint run`
4. `go test ./... -race` — see `tdd_harness.md`
