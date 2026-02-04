# AI Engineering Framework - GitHub Copilot Instructions

## Project Context

{{PROJECT_DESCRIPTION}}

This is a multi-stack enterprise project using layered architecture with the Result Pattern for error handling. All code must follow the standards defined in the `standards/` directory.

See `context/project.md` for full project details, `context/architecture.md` for system design, and `context/glossary.md` for domain terminology.

## Critical Rules

### NEVER

1. Access `Result.Value` without checking `Result.IsError` first
2. Hardcode secrets, tokens, or credentials in code
3. Use exceptions for flow control in .NET code
4. Commit code without tests for new functionality
5. Skip error mapping registration for new error types
6. Expose stack traces or internal errors in API responses
7. Use `var` with method returns where the type is not obvious (.NET)
8. Log sensitive data (passwords, tokens, PII)

### ALWAYS

1. Validate inputs at system boundaries
2. Use structured logging (never string concatenation)
3. Follow existing patterns in the codebase
4. Check for secrets before committing (gitleaks)
5. Run quality gates before creating PRs

## Architecture

Layered architecture with clear separation of concerns:

```
Controllers/Functions --> Providers --> Services --> External Systems
       |                    |             |
     Result              Result         Result
       |                    |             |
  ErrorMapper <--------- Error <------- Error
       |
  HTTP Response
```

- **Controllers/Functions**: Entry points. Receive HTTP requests, delegate to Providers, map Results to HTTP responses via ErrorMapper.
- **Providers**: Business orchestration. Coordinate multiple Services, apply business rules, return Results.
- **Services**: Data access and external integrations. Wrap external calls, return Results.
- **ErrorMapper**: Centralized mapping of domain errors to HTTP status codes and response bodies.

## Key Patterns

### Result Pattern

All operations that can fail return `Result<T>` instead of throwing exceptions.

```csharp
// ALWAYS check IsError before accessing Value
Result<User> result = await _service.GetUserAsync(id);
if (result.IsError)
    return result.Error;
User user = result.Value;  // Safe after check
```

### Error Mapping

Every domain error type must be registered in the error mapper. Missing mappings cause runtime exceptions.

| Error Type            | HTTP Status | Use Case                    |
|-----------------------|-------------|-----------------------------|
| NotFoundError         | 404         | Resource does not exist     |
| InvalidInputError     | 400         | Validation failure          |
| UnauthorizedError     | 401         | Authentication required     |
| ForbiddenError        | 403         | Insufficient permissions    |
| ConflictError         | 409         | State conflict              |
| InternalError         | 500         | Unexpected failure          |

### Guard Clauses

Flatten code by validating preconditions first with early returns. Avoid deep nesting.

```csharp
public async Task<Result<Order>> ProcessAsync(OrderRequest request)
{
    if (request is null)
        return new InvalidInputError("Request cannot be null");

    if (string.IsNullOrEmpty(request.CustomerId))
        return new InvalidInputError("CustomerId is required");

    // Happy path continues flat
    Result<Customer> customerResult = await _customerService.GetAsync(request.CustomerId);
    if (customerResult.IsError)
        return customerResult.Error;

    return await CreateOrderAsync(customerResult.Value, request);
}
```

## Technology Stack Quick Reference

### .NET (C# / ASP.NET Core / Azure Functions)

- Target: .NET 8
- Use explicit types (avoid `var` with method returns where type is not obvious)
- Async methods must have `Async` suffix: `GetUserAsync`, `ProcessOrderAsync`
- Use Result pattern, not exceptions for flow control
- Private fields: `_camelCase`, Classes: `PascalCase`, Interfaces: `IPrefix`
- Testing: NUnit with Moq, use `Assert.EnterMultipleScope()` for grouped assertions
- Test naming: `MethodName_Scenario_ExpectedResult`

### TypeScript (React / Node.js)

- Enable `strict: true` in tsconfig.json
- Never use `any` -- use `unknown` with type guards instead
- Explicit return types for all exported functions
- Use interfaces for object shapes, types for unions/intersections
- React: functional components, typed props interfaces, hooks prefixed with `use`
- Testing: Vitest with React Testing Library
- Files: kebab-case (`user-service.ts`), Components: PascalCase (`UserCard.tsx`)

### Python

- Type hints required on all public functions
- Follow PEP 8, enforced by Ruff
- Use dataclasses or Pydantic for data structures
- Google-style docstrings for public APIs
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Testing: pytest with fixtures, use `@pytest.mark.parametrize` for data-driven tests
- Never use mutable default arguments

### Terraform

- File organization: `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`
- Resource naming: `{prefix}-{project}-{environment}-{type}-{suffix}`
- Always validate variables with `validation` blocks
- Use remote state with locking (Azure Storage backend)
- Tag all resources with project, environment, owner, and managed-by
- Use `for_each` over `count` when iterating

## Testing Requirements

- Write tests alongside code, not after
- Minimum 80% coverage on new code
- Tests co-located with source where possible
- Test naming must describe scenario and expected outcome
- Use Arrange/Act/Assert pattern
- Test both success and error paths
- No hardcoded dates in tests (use relative dates)

## Security Reminders

- Never hardcode secrets, tokens, API keys, or credentials
- Use environment variables or secret managers (Azure Key Vault)
- Validate all inputs at system boundaries
- Use structured logging -- never log passwords, tokens, or PII
- Follow principle of least privilege
- Error responses must not expose stack traces or internal details
- Run gitleaks before committing
- All dependencies scanned by Snyk and CodeQL

## Quality Gates

Before merging, all code must pass:

- **SonarQube**: Coverage >= 80%, duplications <= 3%, all ratings A
- **Security**: No critical/high vulnerabilities (Snyk, CodeQL, OWASP)
- **Secrets**: Zero secrets detected (gitleaks)
- **Tests**: All passing, coverage thresholds met per layer

## Git Conventions

- Branch naming: `feature/`, `bugfix/`, `hotfix/`, `chore/`, `docs/`
- Commit messages: Conventional Commits format (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`)
- Pull requests: clear title, linked issues, test coverage included
