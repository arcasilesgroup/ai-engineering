# Standards Overview

> Coding standards that AI agents read and enforce automatically.

## What Are Standards?

Standards are markdown files that define coding rules for each technology stack. Claude reads these files and enforces the rules when reviewing or generating code.

## Available Standards (10)

| Standard | Scope |
|----------|-------|
| `global.md` | Universal conventions (git, naming, security basics) |
| `dotnet.md` | C#/.NET: coding, Result pattern, error mapping, testing |
| `typescript.md` | TypeScript/React: components, hooks, testing |
| `python.md` | Python: coding conventions, testing |
| `terraform.md` | Infrastructure as Code: Terraform, Azure |
| `security.md` | OWASP, secret scanning, dependency scanning |
| `quality-gates.md` | SonarQube thresholds, linter rules |
| `cicd.md` | GitHub Actions, Azure Pipelines standards |
| `testing.md` | Cross-stack testing philosophy |
| `api-design.md` | REST conventions, versioning, error responses |

## How Standards Work

1. **Claude reads standards** at session start
2. **Code generation** follows the standards
3. **Code review** checks against standards
4. **Violations flagged** with specific rule references

## Standards Location

Standards are stored in `standards/`:

```
standards/
├── global.md
├── dotnet.md
├── typescript.md
├── python.md
├── terraform.md
├── security.md
├── quality-gates.md
├── cicd.md
├── testing.md
└── api-design.md
```

## Standards Structure

Each standards file follows this format:

```markdown
# [Stack] Standards

## Overview
Brief description of the stack and philosophy.

## Coding Conventions
Specific coding rules.

## Patterns
Required patterns (e.g., Result pattern for .NET).

## Testing
Testing requirements for this stack.

## Common Mistakes
Things to avoid.
```

## Example: .NET Critical Rules

From `standards/dotnet.md`:

```markdown
## Critical Rules

1. **Result Pattern**
   - All service methods return `Result<T>` or `Result`
   - NEVER access `Result.Value` without checking `Result.IsError` first
   - Use `ErrorOr` or similar library

2. **Error Mapping**
   - Map internal errors to HTTP status codes in controllers
   - Never expose stack traces in API responses
   - Register all error types in ErrorMapper

3. **Async/Await**
   - Use `async/await` throughout the call chain
   - Never use `.Result` or `.Wait()` on tasks
   - Use `ConfigureAwait(false)` in library code
```

## How Claude Uses Standards

### During Code Generation

```
You: Create a new user service

Claude:
1. Reads standards/dotnet.md
2. Identifies required patterns (Result<T>)
3. Generates code following the patterns
4. Includes proper error handling
```

### During Code Review

```
You: /review src/services/UserService.cs

Claude:
1. Reads standards/dotnet.md
2. Checks code against each rule
3. Reports violations with rule references
4. Suggests fixes
```

## Customizing Standards

### Adding Team Rules

Add to the existing standards file:

```markdown
## Team-Specific Rules

### Logging
- All service methods must log entry and exit
- Use structured logging: `_logger.LogInformation("Processing {OrderId}", orderId)`
- Never log sensitive data (passwords, tokens, PII)

### Naming
- Services: `{Entity}Service` (e.g., `OrderService`)
- Providers: `{Entity}Provider` (e.g., `OrderProvider`)
- Controllers: `{Entity}Controller` (e.g., `OrderController`)
```

### Creating New Standards

For a stack not covered, create a new file:

```markdown
# Go Standards

## Overview
Go coding standards for this project.

## Conventions
- Use gofmt for formatting
- Package names: lowercase, single word
...
```

---
**See also:** [By Stack](Standards-By-Stack) | [Quality Gates](Standards-Quality-Gates)
