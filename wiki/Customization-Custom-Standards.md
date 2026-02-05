# Custom Standards

> Extend or create coding standards for your team.

## Overview

Standards are markdown files that Claude reads and enforces. You can:

1. **Extend existing standards** — Add team rules to framework files
2. **Create new standards** — For stacks not covered

## Extending Existing Standards

Add team-specific rules to the bottom of existing standards files.

### Example: Extending dotnet.md

```markdown
# .NET Standards

[... existing framework content ...]

---

## Team-Specific Rules

### Logging
- All service methods must log entry and exit
- Use structured logging: `_logger.LogInformation("Processing {OrderId}", orderId)`
- Never log sensitive data (passwords, tokens, PII)
- Include correlation ID in all logs

### Naming Conventions
- Services: `{Entity}Service` (e.g., `OrderService`)
- Providers: `{Entity}Provider` (e.g., `OrderProvider`)
- DTOs: `{Entity}Dto` (e.g., `OrderDto`)
- Requests: `{Action}{Entity}Request` (e.g., `CreateOrderRequest`)

### Entity Framework
- Always use async methods: `ToListAsync()`, `FirstOrDefaultAsync()`
- Disable lazy loading in production
- Use explicit includes: `.Include(o => o.Items)`
- Maximum 3 levels of includes

### Dependency Injection
- Register services in feature-specific extension methods
- Use `AddScoped` for services with database context
- Use `AddSingleton` only for stateless utilities

### Our Exceptions
Despite the Result pattern, we DO throw exceptions for:
- Configuration errors at startup
- Unrecoverable infrastructure failures
```

## Creating New Standards

For stacks not covered by the framework, create a new file.

### Example: Go Standards

**File:** `standards/go.md`

```markdown
# Go Standards

## Overview
Go coding standards for this project.

## Formatting
- Use `gofmt` for all files
- Use `goimports` for import organization
- Maximum line length: 120 characters

## Naming
- Package names: lowercase, single word
- Exported functions: PascalCase
- Unexported functions: camelCase
- Acronyms: all caps (HTTP, URL, ID)

## Error Handling
- Always check errors: `if err != nil { ... }`
- Wrap errors with context: `fmt.Errorf("failed to create user: %w", err)`
- Use custom error types for domain errors

## Concurrency
- Prefer channels over mutexes
- Always close channels when done sending
- Use `context.Context` for cancellation

## Testing
- Test files: `*_test.go`
- Test functions: `Test{FunctionName}_{Scenario}`
- Use table-driven tests for multiple cases
- Minimum 80% coverage

## Project Structure
```
cmd/           # Main applications
internal/      # Private application code
pkg/           # Public libraries
api/           # API definitions (protobuf, OpenAPI)
```

## Dependencies
- Use Go modules
- Pin major versions in go.mod
- Run `go mod tidy` before commit
```

### Example: Rust Standards

**File:** `standards/rust.md`

```markdown
# Rust Standards

## Overview
Rust coding standards for this project.

## Formatting
- Use `rustfmt` with default settings
- Use `clippy` for linting

## Error Handling
- Use `Result<T, E>` for recoverable errors
- Use `?` operator for error propagation
- Create custom error types with `thiserror`

## Ownership
- Prefer borrowing over ownership transfer
- Use `Clone` sparingly — document why
- Avoid `unsafe` unless absolutely necessary

## Concurrency
- Use `tokio` for async runtime
- Prefer message passing over shared state
- Use `Arc<Mutex<T>>` only when necessary

## Testing
- Unit tests in same file as code
- Integration tests in `tests/` directory
- Use `#[cfg(test)]` for test modules
```

## Standards Structure

Follow this structure for consistency:

```markdown
# {Stack} Standards

## Overview
Brief description of the stack and philosophy.

## Critical Rules
Rules that must NEVER be violated.

## Coding Conventions
Style and formatting rules.

## Patterns
Required patterns (e.g., Result pattern, error handling).

## Testing
Testing requirements for this stack.

## Common Mistakes
Anti-patterns to avoid.

## Team-Specific Rules (if extending)
Your custom additions.
```

## Referencing Standards in CLAUDE.md

After creating a new standard, reference it in CLAUDE.md:

```markdown
## Standards

| File | Scope |
|------|-------|
| [standards/global.md](standards/global.md) | Universal rules |
| [standards/dotnet.md](standards/dotnet.md) | C#/.NET |
| [standards/go.md](standards/go.md) | Go |  <!-- Add new -->
```

## Standards Updates

When framework updates, your extensions may conflict:

1. **Backup your additions** before updating
2. **Merge carefully** after `install.sh --update`
3. **Consider separate file** for team-specific rules

### Alternative: Separate Team Standards

Instead of modifying framework files:

```
standards/
├── dotnet.md           # Framework (overwritten on update)
├── dotnet-team.md      # Team-specific (preserved)
└── ...
```

Reference both in CLAUDE.md:

```markdown
| [standards/dotnet.md](standards/dotnet.md) | .NET core rules |
| [standards/dotnet-team.md](standards/dotnet-team.md) | .NET team rules |
```

---
**See also:** [Standards Overview](Standards-Overview) | [Custom Hooks](Customization-Custom-Hooks)
