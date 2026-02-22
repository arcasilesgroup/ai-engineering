# .NET Patterns

## Purpose

Comprehensive .NET/C# engineering skill providing patterns, anti-patterns, and best practices for AI-assisted code generation, review, and optimization in .NET projects.

## Trigger

- Command: agent invokes dotnet-patterns skill or references it during .NET code generation/review.
- Context: writing production .NET code, reviewing for quality, applying design patterns, configuring services.

## Domains

### 1) Project Structure

**Patterns**:
- Clean Architecture: `src/Domain/`, `src/Application/`, `src/Infrastructure/`, `src/WebApi/`.
- One project per bounded context concern.
- `Directory.Build.props` for shared project settings.
- `global.json` for SDK version pinning.
- Separate test projects per source project: `tests/<ProjectName>.Tests/`.

**Anti-patterns**:
- Monolithic projects mixing all concerns.
- Circular project references.
- Business logic in controller/endpoint handlers.

### 2) Dependency Injection

**Patterns**:
- Constructor injection for required dependencies.
- `IServiceCollection` extension methods for feature-based registration.
- `IOptions<T>` for configuration binding with validation.
- Scoped services for per-request state, Singleton for stateless services.
- `IHttpClientFactory` for HTTP clients (avoids socket exhaustion).

**Anti-patterns**:
- Service locator pattern (`IServiceProvider.GetService` in business logic).
- Injecting `IServiceProvider` directly.
- Transient services holding state.

### 3) API Design

**Patterns**:
- Minimal APIs for simple endpoints, Controllers for complex routing.
- `TypedResults` for compile-time result validation.
- Problem Details (RFC 9457) for error responses.
- API versioning via URL path or header.
- Input validation with `FluentValidation` or Data Annotations.
- `CancellationToken` propagation on all async endpoints.

**Anti-patterns**:
- Returning raw exception details to clients.
- Missing input validation on public endpoints.
- Synchronous I/O in request pipeline.

### 4) Data Access

**Patterns**:
- Entity Framework Core with Code-First migrations.
- Repository pattern only when abstracting multiple data sources.
- `AsNoTracking()` for read-only queries.
- Parameterized queries (EF Core handles this by default).
- Connection resiliency with `EnableRetryOnFailure()`.

**Anti-patterns**:
- N+1 query patterns (use `.Include()` or projection).
- Raw SQL with string concatenation.
- DbContext as singleton (must be scoped).

### 5) Error Handling

**Patterns**:
- Global exception handler middleware.
- Domain-specific exception types inheriting from a base.
- `Result<T>` pattern for operation outcomes without exceptions.
- `ILogger` for structured logging with scopes.
- Health checks (`IHealthCheck`) for dependency monitoring.

**Anti-patterns**:
- Catching `Exception` without specificity.
- Empty catch blocks.
- Logging and rethrowing without context.
- Using exceptions for control flow.

### 6) Security

**Patterns**:
- `[Authorize]` attribute on all protected endpoints.
- Policy-based authorization for complex rules.
- Data Protection API for encryption at rest.
- Anti-forgery tokens for form submissions.
- CORS configuration explicit and restrictive.
- Security headers middleware (HSTS, CSP, X-Content-Type-Options).

**Anti-patterns**:
- `[AllowAnonymous]` on sensitive endpoints.
- Storing secrets in appsettings.json (use User Secrets or Key Vault).
- Disabling HTTPS in production.

### 7) Testing

**Patterns**:
- xUnit with `[Fact]` and `[Theory]` attributes.
- `WebApplicationFactory<T>` for integration tests.
- `AutoFixture` or builders for test data.
- `NSubstitute` or `Moq` for mocking.
- Test naming: `MethodName_Scenario_ExpectedOutcome`.

**Anti-patterns**:
- Tests depending on database state.
- Mocking everything (test behavior, not implementation).
- Missing assertion messages on complex assertions.

## Output Contract

- Code following the patterns above.
- Nullable reference types enabled.
- XML documentation on public APIs.
- Tests using xUnit with appropriate fixtures.

## Governance Notes

- This skill is the definitive .NET reference for governed projects.
- `standards/framework/stacks/dotnet.md` contains the enforceable subset.
- This skill is advisory/aspirational beyond what standards mandate.

## References

- `standards/framework/stacks/dotnet.md` — enforceable .NET baseline.
- `standards/framework/quality/dotnet.md` — quality thresholds.
- `skills/review/security.md` — security-specific patterns.
