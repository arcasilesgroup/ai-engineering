<!-- source: contexts/languages/csharp.md @ affdef6d3235a65039813845a467340fa4f70803 -->

# C# — Build Conventions

Authoritative reference for the `ai-build` agent when generating C#
code. Distilled from `contexts/languages/csharp.md` plus
`contexts/frameworks/aspnetcore.md`.

## Toolchain

- **.NET version**: latest LTS (.NET 8 minimum, .NET 10 once stable).
  Pin via `<TargetFramework>net8.0</TargetFramework>`.
- **Language**: C# 12+ (`<LangVersion>latest</LangVersion>`).
- **Formatter**: `dotnet format` — verified in CI with
  `dotnet format --verify-no-changes`.
- **Editor config**: `.editorconfig` at repo root pinning style and
  enabling analyzer severity overrides.

## Project layout

```
src/
  Markets.Api/          # ASP.NET Core host
  Markets.Domain/       # pure domain logic
  Markets.Infrastructure/
tests/
  Markets.Domain.Tests/
  Markets.Api.Tests/
Markets.sln
Directory.Build.props   # shared MSBuild properties
.editorconfig
```

- One project per ring. Domain has no framework references.
- `Directory.Build.props` enforces nullable reference types and
  treat-warnings-as-errors across the solution.

## Naming (Microsoft conventions)

| Element | Convention | Example |
|---|---|---|
| Public types / methods / properties | PascalCase | `MarketRepository`, `LookupAsync` |
| Private fields | `_camelCase` | `_repository` |
| Local variables / parameters | camelCase | `marketId` |
| Constants | PascalCase | `MaxRetries` (not `MAX_RETRIES`) |
| Interfaces | `I` prefix | `IMarketRepository` (this is the .NET convention; it's the only language with this rule that we follow) |

## Nullable reference types

- `<Nullable>enable</Nullable>` is mandatory in every project.
- Public APIs annotate intent with `?` for nullable, no annotation for
  non-null.
- The null-forgiving operator `!` is forbidden in new code; allowed
  with a justifying comment.

## Async

- Suffix async methods with `Async`.
- Never use `.Result` or `.Wait()` — they deadlock under
  synchronization contexts.
- `async Task` for fallible work; `async Task<T>` for results;
  `async ValueTask<T>` only when justified by hot-path measurements.
- `async void` only for event handlers.
- `ConfigureAwait(false)` in libraries; not needed in ASP.NET Core
  host code.

## LINQ

- `Any()` over `Count() > 0` for existence checks.
- Materialise once with `.ToList()` when the query is enumerated
  multiple times.
- `Where().OrderBy()` not `OrderBy().Where()` to reduce sorting work.

## Records & DTOs

- `record` for immutable data; `record class` for reference types,
  `record struct` for tiny value types.
- Positional records for DTOs (`public record Market(string Symbol,
  decimal LastPrice);`).

## Disposal

- `using var x = ...;` (C# 8+) for scope-bound disposal.
- Implement `IAsyncDisposable` when cleanup is async.
- Never call `.Dispose()` manually except in finalisers / unusual
  ownership scenarios.

## Quality gate (pre-commit)

1. `dotnet build --warnaserror`
2. `dotnet format --verify-no-changes`
3. `dotnet test` — see `tdd_harness.md`
4. `dotnet list package --vulnerable --include-transitive` in CI
