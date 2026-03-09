# Framework .NET Stack Standards

## Update Metadata

- Rationale: production-grade .NET standard with 10+ years equivalent depth across ASP.NET Core, EF Core, Azure Functions, testing, and performance patterns.
- Expected gain: AI agents generate and review .NET code with principal-engineer-level accuracy. All dev skills automatically consume expanded patterns.
- Potential impact: .NET tooling requirements, code patterns, EF Core patterns, and testing tiers become enforceable during generation and review.

## Stack Scope

- Primary language: C# (.NET 10).
- Supporting formats: Markdown, YAML, JSON, Bash, PowerShell.
- Toolchain baseline: `dotnet` CLI, .NET Aspire for cloud-native orchestration.
- Distribution: NuGet package or container image.

## Required Tooling

- Package/runtime: `dotnet` SDK (restore, build, test, format, publish).
- Lint/format: `dotnet format` (Roslyn analyzers + EditorConfig).
- Type checking: built-in (C# compiler with nullable reference types enabled).
- EF Core CLI: `dotnet-ef` tool for migrations (`dotnet tool install --global dotnet-ef`).
- Dependency vulnerability scan: `dotnet list package --vulnerable --include-transitive`.
- Security SAST: `semgrep` (OWASP-oriented), `gitleaks` (secret detection).
- Analyzer packages: `Microsoft.CodeAnalysis.NetAnalyzers`, `StyleCop.Analyzers`.

## Minimum Gate Set

- Pre-commit: `dotnet format --verify-no-changes`, `gitleaks`.
- Pre-push: `semgrep`, `dotnet list package --vulnerable --include-transitive`, `dotnet build --no-restore`, `dotnet test --no-build`.

## Quality Baseline

- Nullable reference types: `<Nullable>enable</Nullable>` in all projects.
- Coverage target: per `standards/framework/quality/core.md` (80% overall, 100% governance-critical).
- EditorConfig enforced: `indent_size=4`, `end_of_line=lf`, `charset=utf-8`.
- Roslyn analyzers enabled with `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` in Release configuration.
- XML documentation on all public APIs (`<GenerateDocumentationFile>true</GenerateDocumentationFile>`).

## SDK Version Pinning

- A `global.json` file MUST exist at the solution root.
- SDK version pinned as `major.minor.patch` with `rollForward: latestPatch`.
- Example: `{ "sdk": { "version": "10.0.100", "rollForward": "latestPatch" } }`.
- The pinned version must satisfy `<TargetFramework>net10.0</TargetFramework>` in all `.csproj` files.
- CI and local builds use the same SDK version via `global.json`.

## NuGet Package Management

- Central Package Management via `Directory.Packages.props` at solution root.
- Lock files: `packages.lock.json` generated per project with `<RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>`.
- CI restores with `--locked-mode` to fail on lock file drift.
- No floating versions (`*`, `>=`) in production dependencies.
- Trusted package sources only: `NuGet.config` with `<clear/>` followed by explicit `<add>` entries.

## Code Patterns

- **Async by default**: `async`/`await` for all I/O. Never `Task.Wait()`, never `.Result` (deadlock risk). `ValueTask<T>` for hot-path methods that often complete synchronously. Never `Task.Run` in ASP.NET Core request handlers (already on thread pool).
- **Dependency injection**: constructor injection only. `Transient` for stateless services, `Scoped` for per-request (DbContext), `Singleton` for shared state. Keyed services for named registrations (.NET 8+). Enable scope validation in Development (`ValidateScopes`). Never use service locator pattern (`IServiceProvider.GetService` in business logic).
- **IOptions pattern**: `IOptions<T>` for static config, `IOptionsSnapshot<T>` for scoped (reloads per request), `IOptionsMonitor<T>` for singleton with change notification. Validate with `ValidateDataAnnotations()` and `ValidateOnStart()`.
- **HttpClientFactory**: never `new HttpClient()` directly. Use `IHttpClientFactory` or typed clients. Configure resilience pipelines with `Microsoft.Extensions.Http.Resilience` (retry + circuit breaker + timeout). Named clients for multi-endpoint scenarios.
- **Minimal APIs**: prefer for new services. `MapGroup()` for route organization. `TypedResults` for compile-time response type safety. Endpoint filters for cross-cutting concerns. Route constraints for parameter validation (`{id:int}`).
- **Controllers**: `[ApiController]` attribute for automatic model validation and `400` responses. `[Route("api/v{version:apiVersion}/[controller]")]` for versioned routes. Use `ActionResult<T>` return types for Swagger documentation.
- **Middleware pipeline**: order matters — `UseExceptionHandler` > `UseHsts` > `UseHttpsRedirection` > `UseStaticFiles` > `UseRouting` > `UseCors` > `UseAuthentication` > `UseAuthorization` > Map endpoints.
- **Error handling**: ProblemDetails (RFC 9457) for ALL error responses. `IExceptionHandler` (.NET 8+) for global exception handling. Never expose stack traces in production. Use `Results.Problem()` in minimal APIs, `ControllerBase.Problem()` in controllers.
- **Structured logging**: `ILogger<T>` through DI. Message templates (not string interpolation): `_logger.LogInformation("Processing order {OrderId}", orderId)`. `[LoggerMessage]` source generator for high-performance logging paths. Correlation IDs via `Activity.Current?.Id`.
- **Configuration hierarchy**: `appsettings.json` > `appsettings.{env}.json` > environment variables > user secrets (dev only). NEVER store secrets in appsettings. Use Azure Key Vault references or `IConfiguration` with Key Vault provider.
- **Authentication/Authorization**: JWT bearer for APIs, cookie for web UI. `[Authorize]` on endpoints/controllers. Claims-based policies for fine-grained access. Role-based for coarse-grained. Never hard-code role names in code — use policy constants.
- **Health checks**: `/healthz` for liveness, `/ready` for readiness. `AddHealthChecks()` with checks for DB, cache, external services. Map with `MapHealthChecks()`. Return `Healthy`, `Degraded`, or `Unhealthy`.
- **Response caching**: Output caching (.NET 8+) with `[OutputCache]` or `MapGet().CacheOutput()`. `IDistributedCache` for cross-instance caching. `IMemoryCache` for single-instance hot data only.
- **Performance**: `ArrayPool<T>` / `MemoryPool<T>` for large allocations (avoid LOH >85KB). `Span<T>` / `Memory<T>` for zero-allocation parsing. `IAsyncEnumerable<T>` for streaming large datasets. Response compression with Brotli. Connection string pooling: `Pooling=true;Min Pool Size=5;Max Pool Size=100`.
- **Background work**: `IHostedService` / `BackgroundService` for in-process long-running tasks. Azure Functions for out-of-process jobs. Never `Task.Run` with fire-and-forget in request handlers. Use `IServiceScopeFactory` to create DI scopes in background services.
- **Cross-OS**: `Path.Combine` and `Path.DirectorySeparatorChar` throughout.
- **Small focused methods**: <50 lines, single responsibility.
- **Project layout**: `src/` for source projects, `tests/` for test projects. One `.sln` at repository root. Shared configuration in `Directory.Build.props`.

## EF Core Patterns

- **DbContext registration**: `AddDbContextPool<T>` for high-throughput scenarios (>100 req/s). `AddDbContext<T>` for standard workloads. Connection string from `IConfiguration`, never hardcoded.
- **Entity mapping**: Fluent API in `OnModelCreating` (not data annotations for complex mappings). Separate `IEntityTypeConfiguration<T>` per entity. Configure relationships, indexes, constraints, value conversions.
- **No-tracking queries**: `AsNoTracking()` for all read-only queries. Or set `QueryTrackingBehavior.NoTracking` as default and opt in with `AsTracking()` when needed.
- **Projections**: Always `Select()` to project only needed columns. Avoid loading full entities for read-only scenarios.
- **Split queries**: `AsSplitQuery()` to avoid cartesian explosion with multiple `Include()` chains.
- **Keyset pagination**: `.Where(x => x.Id > lastId).OrderBy(x => x.Id).Take(pageSize)`. Avoid `Skip()`/`Take()` for large datasets (poor SQL performance).
- **Compiled queries**: `EF.CompileAsyncQuery()` for hot-path queries executed frequently with the same shape.
- **Interceptors**: `SaveChangesInterceptor` for audit fields (`CreatedAt`, `UpdatedAt`). `IDbCommandInterceptor` for query logging or modification.
- **Migrations**: one migration per feature/change. Descriptive names: `AddUserEmailIndex`, `CreateOrdersTable`. Review generated SQL before applying. Expand-contract pattern for breaking schema changes. Never edit scaffolded `Down()` unless necessary.
- **Bulk operations**: `ExecuteUpdateAsync()` / `ExecuteDeleteAsync()` (.NET 7+) for set-based operations without loading entities into memory.
- **Index strategy**: `StartsWith()` translates to `LIKE 'x%'` (uses index). `Contains()` / `EndsWith()` generate `LIKE '%x%'` / `LIKE '%x'` (full scan). Create indexes on frequently filtered/sorted columns.
- **Concurrency**: `[ConcurrencyCheck]` or `[Timestamp]` (`rowversion`) for optimistic concurrency. Handle `DbUpdateConcurrencyException` with retry or user notification.
- **Connection resilience**: `EnableRetryOnFailure()` for transient error handling with SQL Server/Azure SQL.
- **Async always**: `ToListAsync()`, `FirstOrDefaultAsync()`, `SaveChangesAsync()` — never synchronous equivalents in web applications.
- **Avoid client evaluation**: ensure all LINQ operators translate to SQL. Enable `ConfigureWarnings(w => w.Throw(RelationalEventId.QueryClientEvaluationWarning))` in Development.

## Test Tiers

| Tier | Attribute | I/O | Gate | Description |
|------|-----------|-----|------|-------------|
| Unit | `[Category("Unit")]` | None | Pre-commit | Pure logic, no I/O, fast (<1s per test) |
| Integration | `[Category("Integration")]` | Local (DB, FS) | Pre-push | WebApplicationFactory, TestContainers |
| E2E | `[Category("E2E")]` | Full stack | PR gate | End-to-end API flows |
| Live | `[Category("Live")]` | External APIs | Opt-in | Requires `DOTNET_LIVE_TEST=1` env var |

- Tests without an explicit category are treated as **Unit** by default.
- Live tests are excluded from CI unless the environment variable is set.
- Coverage targets apply to Unit + Integration tiers combined.
- E2E tests validate behavior, not line coverage.

## Testing Patterns

- NUnit as test framework. One test class per production class.
- AAA pattern (Arrange-Act-Assert). Naming: `MethodName_Scenario_ExpectedOutcome`.
- **WebApplicationFactory\<Program\>**: custom factory inheriting `WebApplicationFactory<Program>`. Override `ConfigureWebHost` to replace `DbContext`, mock external HTTP clients, configure test authentication.
- **TestContainers**: `Testcontainers.MsSql` or `Testcontainers.PostgreSql` for realistic database integration tests. `IAsyncLifetime` for container lifecycle management.
- **Mocking**: NSubstitute (preferred) or Moq for DI dependencies. Never mock what you don't own — wrap external libraries behind interfaces.
- **Assertions**: FluentAssertions for readable assertions: `result.Should().BeEquivalentTo(expected)`.
- **Test data**: Bogus for fake data generation. AutoFixture for automatic test object creation. Builder pattern for complex entity setup.
- **Snapshot testing**: Verify library for response/object snapshot comparison.
- **Architecture tests**: NetArchTest.Rules to enforce layer boundaries (domain must not reference infrastructure).
- **Benchmarks**: BenchmarkDotNet for critical-path performance baselines.
- **Coverage**: `coverlet.collector` + ReportGenerator. Command: `dotnet test --collect:"XPlat Code Coverage"`.
- **Fixtures**: `[OneTimeSetUp]`/`[OneTimeTearDown]` for per-class shared context. `[SetUpFixture]` for cross-namespace shared context. `TestContext` for test output logging.

## Performance Patterns

- Benchmark with BenchmarkDotNet before optimizing. Measure, don't guess.
- Avoid LOH allocations (>85KB). Use `ArrayPool<byte>.Shared` for buffer reuse.
- Response compression with Brotli (default in ASP.NET Core, configure `CompressionLevel.Optimal`).
- Output caching (.NET 8+) for response-level caching with tag-based invalidation.
- Connection string pooling: `Pooling=true;Min Pool Size=5;Max Pool Size=100` (tune per workload).
- Minimal API has lower per-request overhead than controllers for high-throughput services.
- `IAsyncEnumerable<T>` for streaming large datasets (avoids buffering entire result sets).
- Cache layers: `IMemoryCache` for single-instance hot data, `IDistributedCache` (Redis/SQL) for multi-instance.
- Object pooling: `ObjectPool<T>` for expensive-to-create objects (StringBuilder, HttpClient handlers).
- String operations: `StringBuilder` for concatenation in loops. `string.Create` for known-length construction. Avoid LINQ on strings in hot paths.

## C# Coding Conventions

- **PascalCase**: public members, types, namespaces, properties, methods, events.
- **camelCase**: private fields with `_` prefix (`_camelCase`), parameters, local variables.
- **File-scoped namespaces**: `namespace MyApp.Services;` (one line, not block).
- **`var`**: use when type is obvious from the right side. Explicit type when not obvious.
- **Collection expressions**: `string[] items = ["a", "b"];` (.NET 8+).
- **Raw string literals**: `"""..."""` over escape sequences for multi-line or special characters.
- **String interpolation**: `$"{name} {value}"` over concatenation.
- **`using` declaration** (braceless): `using var stream = File.OpenRead(path);`.
- **Short-circuit operators**: `&&`/`||` over `&`/`|`.
- **Indentation**: 4-space, Allman brace style (opening brace on new line).
- **One statement per line**, one declaration per line.
- **Primary constructors**: use for DI injection in services (.NET 8+).
- **Pattern matching**: prefer `is`, `switch` expressions, and property patterns over type casting chains.
- **Records**: use `record` for immutable DTOs and value objects. `record struct` for small value types.

## Update Contract

This file is framework-managed and may be updated by framework releases.
