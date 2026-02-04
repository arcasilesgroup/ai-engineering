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

See `context/architecture.md` for full architectural details.

## Reconnaissance Before Writing

Before implementing new code, you MUST search for existing patterns:

1. **Search** for 2+ existing examples of similar patterns in the codebase.
2. **Read** the matching standards file (`standards/*.md`) for the stack you are working in.
3. **Read** the matching learnings file (`learnings/*.md`) for known pitfalls and team decisions.
4. **Explain** the pattern you found and confirm you will follow it.
5. **Implement** following that exact pattern.

If no similar pattern exists, state that explicitly and propose an approach before writing code.

### Standards Reference

Before making changes to any stack, consult the relevant standards file:

| File | Scope |
|------|-------|
| `standards/global.md` | Universal rules: git, naming, security basics |
| `standards/dotnet.md` | C#/.NET: coding, Result pattern, error mapping, testing |
| `standards/typescript.md` | TypeScript/React: components, hooks, testing |
| `standards/python.md` | Python: coding conventions, testing |
| `standards/terraform.md` | Infrastructure as Code: Terraform, Azure |
| `standards/security.md` | OWASP, secret scanning, dependency scanning |
| `standards/quality-gates.md` | SonarQube thresholds, linter rules |
| `standards/cicd.md` | GitHub Actions, Azure Pipelines standards |
| `standards/testing.md` | Cross-stack testing philosophy |
| `standards/api-design.md` | REST conventions, versioning, error responses |

### Learnings Reference

Before working on a stack, check for known pitfalls and team decisions:

- `learnings/global.md` - Cross-cutting learnings
- `learnings/dotnet.md` - .NET-specific learnings
- `learnings/typescript.md` - TypeScript learnings
- `learnings/terraform.md` - Terraform learnings

## Verification Protocol

Never say "should work" or "looks right." Verify with exact commands.

### .NET
```bash
dotnet build --no-restore
dotnet test --no-build --verbosity normal
dotnet format --verify-no-changes
```

### TypeScript
```bash
npx tsc --noEmit
npm test
npx eslint .
```

### Python
```bash
python -m py_compile <file>
pytest
ruff check .
```

### Terraform
```bash
terraform validate
terraform fmt -check
terraform plan
```

If any command fails, fix the issue before moving on. Do not skip verification.

## Danger Zones

These areas require extra caution. Read the full context, check blast radius, and verify thoroughly.

| Zone | Risk | Rules |
|------|------|-------|
| **Authentication / Authorization** | Security breach | Never bypass auth checks. Test both authorized and unauthorized paths. |
| **Database Schemas / Migrations** | Data loss | Always create reversible migrations. Test rollback. Never drop columns without data migration plan. |
| **Payment / Billing** | Financial loss | Idempotency required. Log all transactions. Test edge cases: timeouts, duplicates, partial failures. |
| **Permissions / RBAC** | Privilege escalation | Default deny. Test every role. Never grant admin implicitly. |
| **Configuration / Environment** | Outages | Never hardcode environment values. Validate config at startup. Test with missing/invalid config. |
| **API Contracts** | Breaking clients | Version the API. Never remove or rename fields without deprecation. |
| **CI/CD Pipelines** | Broken deploys | Test pipeline changes in a branch first. Never modify main pipeline directly. |

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
- Full conventions in `standards/dotnet.md`

### TypeScript (React / Node.js)

- Enable `strict: true` in tsconfig.json
- Never use `any` -- use `unknown` with type guards instead
- Explicit return types for all exported functions
- Use interfaces for object shapes, types for unions/intersections
- React: functional components, typed props interfaces, hooks prefixed with `use`
- Testing: Vitest with React Testing Library
- Files: kebab-case (`user-service.ts`), Components: PascalCase (`UserCard.tsx`)
- Full conventions in `standards/typescript.md`

### Python

- Type hints required on all public functions
- Follow PEP 8, enforced by Ruff
- Use dataclasses or Pydantic for data structures
- Google-style docstrings for public APIs
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Testing: pytest with fixtures, use `@pytest.mark.parametrize` for data-driven tests
- Never use mutable default arguments
- Full conventions in `standards/python.md`

### Terraform

- File organization: `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`
- Resource naming: `{prefix}-{project}-{environment}-{type}-{suffix}`
- Always validate variables with `validation` blocks
- Use remote state with locking (Azure Storage backend)
- Tag all resources with project, environment, owner, and managed-by
- Use `for_each` over `count` when iterating
- Full conventions in `standards/terraform.md`

## Testing Requirements

- Write tests alongside code, not after
- Minimum 80% coverage on new code
- Tests co-located with source where possible
- Test naming must describe scenario and expected outcome
- Use Arrange/Act/Assert pattern
- Test both success and error paths
- No hardcoded dates in tests (use relative dates)
- Full testing philosophy in `standards/testing.md`

## Security Reminders

- Never hardcode secrets, tokens, API keys, or credentials
- Use environment variables or secret managers (Azure Key Vault)
- Validate all inputs at system boundaries
- Use structured logging -- never log passwords, tokens, or PII
- Follow principle of least privilege
- Error responses must not expose stack traces or internal details
- Run gitleaks before committing
- All dependencies scanned by Snyk and CodeQL
- Full security standards in `standards/security.md`

## Quality Gates

Before merging, all code must pass:

- **SonarQube**: Coverage >= 80%, duplications <= 3%, all ratings A
- **Security**: No critical/high vulnerabilities (Snyk, CodeQL, OWASP)
- **Secrets**: Zero secrets detected (gitleaks)
- **Tests**: All passing, coverage thresholds met per layer

Full thresholds and rules in `standards/quality-gates.md`.

## Git Conventions

- Branch naming: `feature/`, `bugfix/`, `hotfix/`, `chore/`, `docs/`
- Commit messages: Conventional Commits format (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`)
- Pull requests: clear title, linked issues, test coverage included
