# Example — record + xUnit theory

Demonstrates: positional record, value-based equality, parametric
test via `[Theory]` + `[InlineData]`, no `async void`, no force
unwrap.

```csharp
// src/Markets.Domain/Market.cs
namespace Markets.Domain;

public enum MarketError
{
    EmptySymbol,
    SymbolTooLong,
    SymbolNonLetter,
}

public class MarketException : Exception
{
    public MarketException(MarketError error)
        : base(error.ToString()) => Error = error;
    public MarketError Error { get; }
}

public sealed record Market(string Symbol, decimal LastPrice)
{
    public static Market Create(string rawSymbol, decimal lastPrice)
    {
        var trimmed = rawSymbol?.Trim() ?? string.Empty;
        if (trimmed.Length == 0)
            throw new MarketException(MarketError.EmptySymbol);
        if (trimmed.Length > 10)
            throw new MarketException(MarketError.SymbolTooLong);
        foreach (var c in trimmed)
        {
            if (!char.IsLetter(c) || c > 0x7F)
                throw new MarketException(MarketError.SymbolNonLetter);
        }
        return new Market(trimmed.ToUpperInvariant(), lastPrice);
    }
}
```

```csharp
// tests/Markets.Domain.Tests/MarketTests.cs
using Markets.Domain;

public class MarketTests
{
    [Fact]
    public void Create_EmptySymbol_Throws()
    {
        var ex = Assert.Throws<MarketException>(() => Market.Create("", 1m));
        Assert.Equal(MarketError.EmptySymbol, ex.Error);
    }

    [Theory]
    [InlineData("btc", "BTC")]
    [InlineData(" eth ", "ETH")]
    public void Create_NormalisesSymbol(string input, string expected)
    {
        var m = Market.Create(input, 1m);
        Assert.Equal(expected, m.Symbol);
    }

    [Fact]
    public void Equality_IsValueBased()
    {
        var a = Market.Create("BTC", 1m);
        var b = Market.Create("BTC", 1m);
        Assert.Equal(a, b);
    }
}
```
