# C# Review Guidelines

## Update Metadata
- Rationale: C#-specific patterns for null safety, async/await, LINQ, and .NET conventions.

## Idiomatic Patterns
- Enable nullable reference types (`<Nullable>enable</Nullable>`).
- Use `record` types for immutable data transfer objects.
- Prefer pattern matching (`is`, `switch expressions`) over type casting.
- Use `IAsyncEnumerable<T>` for streaming data.
- Dependency injection via constructor — no service locator anti-pattern.

## Performance Anti-Patterns
- **LINQ in hot paths**: Materialize queries early, avoid repeated enumeration.
- **String interpolation in logging**: Use structured logging with message templates.
- **Missing `ConfigureAwait(false)`** in library code.
- **Boxing value types**: Watch for `object` parameters accepting structs.

## Security Patterns
- Use parameterized queries — never string concatenation for SQL.
- Validate model binding with `[Required]`, `[Range]`, data annotations.
- Use `[Authorize]` attributes consistently on controllers.

## Testing Patterns
- xUnit with `[Theory]` + `[InlineData]` for parameterized tests.
- Use `Moq` or `NSubstitute` for mocking — prefer interfaces.
- Integration tests with `WebApplicationFactory<T>`.

## Self-Challenge Questions
- Is this a .NET version-specific issue? Check target framework.
- Does the suggested pattern work with the project's DI container?

## References
- Enforcement: `standards/framework/stacks/dotnet.md`
