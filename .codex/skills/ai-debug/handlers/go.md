# Handler: Go Build Resolver

## Purpose

Resolves Go compilation errors, module dependency failures, and static analysis warnings. Covers the full diagnostic chain from `go build` through `go vet`, `staticcheck`, and `golangci-lint`, including module resolution with `go mod verify` and `go mod tidy`. Targets Go 1.21+ projects using Go modules.

## Activation

Activate this handler when:

- The project contains `go.mod` at the repository root or in the target directory
- Source files have the `.go` extension
- Build errors reference Go compiler messages (e.g., `cannot use`, `undefined`, `imported and not used`)
- The user reports issues with `go build`, `go test`, or `go run`

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Go installation and version
go version

# 2. Verify module integrity
go mod verify

# 3. Ensure dependencies are consistent
go mod tidy -diff   # Go 1.21+; shows what would change without modifying files

# 4. Compile all packages (fast feedback, no binary output)
go build ./...

# 5. Run the Go vet suite (catches suspicious constructs)
go vet ./...

# 6. Run staticcheck (if installed)
staticcheck ./...

# 7. Run golangci-lint (if installed and .golangci.yml exists)
golangci-lint run ./...

# 8. Run tests to confirm behavioral correctness
go test -count=1 -race ./...
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined: X` | Symbol `X` not declared in the current package or not exported from the imported package. | Check spelling and capitalization. Exported symbols start with uppercase. Verify the correct package is imported. |
| `cannot use X (type T1) as type T2` | Type mismatch in assignment, function argument, or return value. | Cast explicitly if safe (`T2(X)`), or change the variable/parameter declaration to match. For interfaces, ensure `T1` implements `T2`. |
| `import cycle not allowed` | Package A imports B which imports A (directly or transitively). | Extract shared types into a third package that both can import. Use `go list -f '{{.Imports}}' ./pkg/...` to trace the cycle. |
| `cannot find package "X"` | Module not downloaded, wrong import path, or missing `go.mod` require. | Run `go mod tidy`. If the package is external, run `go get X@latest`. Verify the import path matches the module path exactly. |
| `X declared but not used` | Local variable or import is declared but never referenced. | Remove the unused variable or import. Use `_` for intentionally discarded values. For imports used only for side effects, use `import _ "pkg"`. |
| `multiple-value X() in single-value context` | Calling a function that returns (T, error) but only capturing one value. | Capture both values: `val, err := X()`. Handle the error explicitly. |
| `cannot use X (type T) as type S in map key` | Struct used as map key contains fields that are not comparable (slices, maps, functions). | Remove non-comparable fields from the key struct, or use a string/int derived key instead. |
| `invalid type assertion: X.(T)` | The interface value does not hold type T, or X is not an interface. | Use the comma-ok pattern: `v, ok := X.(T)`. Verify X is declared as an interface type. |
| `too many arguments in call to X` | Function called with more arguments than its signature accepts. | Check the function signature. Common cause: API changed in a dependency update. Run `go doc pkg.X`. |
| `cannot assign to X` | Attempting to assign to an unexported field, a map value field, or a constant. | For map struct values, assign the entire struct: `m[k] = newStruct`. For unexported fields, use the package's setter methods. |
| `missing return at end of function` | Not all code paths return a value in a function with a declared return type. | Add the missing return statement. Check that all branches of if/switch/select return. |
| `init function must have no arguments and no return values` | `init()` declared with parameters or return type. | Remove all parameters and return types from `func init()`. |

## Module Troubleshooting

```bash
# Why is a specific module required?
go mod why -m github.com/example/pkg

# Pin a dependency to a specific version
go get github.com/example/pkg@v1.2.3

# Replace a module with a local copy (development only)
# Add to go.mod: replace github.com/example/pkg => ../local-pkg

# Clear the module cache (last resort)
go clean -modcache

# List all direct and indirect dependencies
go list -m all

# Check for available updates
go list -m -u all

# Verify checksums match go.sum
go mod verify

# Download all dependencies without building
go mod download

# Visualize the dependency graph
go mod graph | head -30

# Find why a specific version was selected
go mod graph | grep "example/pkg"
```

## Build Cache Troubleshooting

```bash
# Clear the build cache (resolves stale object issues)
go clean -cache

# Clear test cache only
go clean -testcache

# Rebuild everything from scratch
go build -a ./...

# Check GOPATH and GOROOT
go env GOPATH GOROOT GOMODCACHE

# Verify CGO is configured correctly (if using C bindings)
go env CGO_ENABLED CC CXX
```

## Hard Rules

- **NEVER** add `//nolint` directives to suppress linter findings. Fix the code or refactor to satisfy the linter.
- **NEVER** add `//go:nosplit`, `//go:noescape`, or other compiler directives to work around build errors.
- **NEVER** use `replace` directives in `go.mod` for production code. They are for local development only and must be removed before commit.
- **NEVER** vendor dependencies without explicit user approval (`go mod vendor`).
- **ALWAYS** handle errors explicitly. Do not discard errors with `_`.
- **ALWAYS** run `go mod tidy` after adding or removing imports.
- **ALWAYS** use `go vet ./...` as part of the verification cycle after a fix.

## Stop Conditions

- The build error requires changes to a third-party dependency that the team does not control. Escalate with the module path and version.
- The error involves CGO or platform-specific build constraints that cannot be reproduced in the current environment. Document the constraint and escalate.
- Two fix attempts have failed for the same error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | go build ./... | go vet ./... | go test -race ./...
```
