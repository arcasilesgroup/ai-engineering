# Framework .NET Stack Standards

## Update Metadata

- Rationale: extend multi-stack support to .NET projects; mirror python.md structure for consistency.
- Expected gain: predictable .NET baseline with explicit patterns for AI-assisted code generation and review.
- Potential impact: .NET tooling requirements and code patterns become enforceable during generation and review.

## Stack Scope

- Primary language: C# (.NET 8+).
- Supporting formats: Markdown, YAML, JSON, Bash, PowerShell.
- Toolchain baseline: `dotnet` CLI (format, build, test, list package).
- Distribution: NuGet package or container image.

## Required Tooling

- Package/runtime: `dotnet` SDK (includes restore, build, test, format).
- Lint/format: `dotnet format` (Roslyn analyzers + EditorConfig).
- Type checking: built-in (C# compiler with nullable reference types enabled).
- Dependency vulnerability scan: `dotnet list package --vulnerable`.
- Security SAST: `semgrep` (OWASP-oriented), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `dotnet format --verify-no-changes`, `gitleaks`.
- Pre-push: `semgrep`, `dotnet list package --vulnerable`, `dotnet build --no-restore`, `dotnet test --no-build`.

## Quality Baseline

- Nullable reference types enabled (`<Nullable>enable</Nullable>`).
- Test coverage target: >=80% overall, >=90% for governance-critical paths.
- EditorConfig enforced for formatting consistency.
- XML documentation on all public APIs.

## Code Patterns

- **Minimal APIs or Controller-based**: follow project convention, prefer minimal APIs for new services.
- **Dependency injection**: built-in `Microsoft.Extensions.DependencyInjection`.
- **Configuration**: `IOptions<T>` pattern with appsettings.json hierarchy.
- **Cross-OS**: `Path.Combine` and `Path.DirectorySeparatorChar` throughout.
- **Small focused methods**: <50 lines, single responsibility.
- **Async by default**: async/await for I/O-bound operations.
- **Project layout**: `src/` for source, `tests/` for test projects.

## Testing Patterns

- xUnit as test framework.
- One test class per production class, AAA pattern (Arrange-Act-Assert).
- `IClassFixture<T>` for shared test context.
- Integration tests use `WebApplicationFactory<T>` for API testing.
- Naming: `MethodName_Scenario_ExpectedOutcome`.
- Test data builders or AutoFixture for complex setup.

## Update Contract

This file is framework-managed and may be updated by framework releases.
