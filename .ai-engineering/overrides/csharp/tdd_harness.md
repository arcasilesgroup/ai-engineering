# C# — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through xUnit (or NUnit on
existing repos). Tests are deterministic and never reach the
network.

## Runner

- **Default**: `xunit` (modern, parallel-by-default).
- **Acceptable**: `NUnit` if the repo already uses it; not for new
  repos.
- **Forbid**: `MSTest` for new code — slower, fewer features.

## Layout

```
src/Markets.Domain/Market.cs
tests/Markets.Domain.Tests/MarketTests.cs
tests/Markets.Domain.Tests/Markets.Domain.Tests.csproj
```

- One test project per source project, named `<Source>.Tests`.
- Mirror folder layout inside the test project so the file path
  reveals what's under test.

## Naming

- File: `<Unit>Tests.cs`.
- Class: `public class <Unit>Tests`.
- Method: `public void <Method>_<Condition>_<Outcome>()` —
  `Init_EmptySymbol_Throws`.

## RED → GREEN → REFACTOR

1. **RED** — write the failing test. Run
   `dotnet test --filter FullyQualifiedName~MarketTests.Init_EmptySymbol_Throws`.
   Confirm the failure message matches the assertion.
2. **GREEN** — minimum implementation. Do not modify the test.
3. **REFACTOR** — clean up; suite stays green.

## xUnit patterns

```csharp
public class MarketTests
{
    [Fact]
    public void Init_EmptySymbol_Throws()
    {
        var ex = Assert.Throws<MarketException>(() => new Market("", 1m));
        Assert.Equal(MarketError.EmptySymbol, ex.Error);
    }

    [Theory]
    [InlineData("btc", "BTC")]
    [InlineData(" eth ", "ETH")]
    public void Init_NormalisesSymbol(string input, string expected)
    {
        var market = new Market(input, 1m);
        Assert.Equal(expected, market.Symbol);
    }
}
```

## `[Theory]` + `[InlineData]`

The xUnit parametric pattern. Use `[MemberData]` for runtime-built
cases, `[ClassData]` for complex data sources.

## Async tests

```csharp
[Fact]
public async Task Load_ReturnsMarket()
{
    var market = await _repo.LoadAsync("id-1");
    Assert.Equal("BTC", market.Symbol);
}
```

## Mocks / fakes

- **Default**: hand-rolled fakes for small interfaces.
- **When generators justified**: `NSubstitute` (preferred) or `Moq`.
  Pin the version and avoid feature creep.
- Avoid mocking concrete classes — extract an interface first.

## Coverage

- `dotnet test --collect:"XPlat Code Coverage"`.
- `coverlet` for richer reports.
- Floor: 80 % statement coverage on touched files.

## Helpers

- Use `IClassFixture<T>` for shared expensive setup.
- `IDisposable.Dispose` on test classes for per-test teardown
  (xUnit calls it automatically).
- `ITestOutputHelper` for diagnostic output, not `Console.WriteLine`.
