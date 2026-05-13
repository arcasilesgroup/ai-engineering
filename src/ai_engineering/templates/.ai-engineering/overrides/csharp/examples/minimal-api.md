# Example — ASP.NET Core Minimal API

A typed POST endpoint with FluentValidation, dependency injection,
problem-detail responses. Demonstrates: nullable annotations, no
`async void`, anti-forgery on cookie-authenticated routes.

```csharp
// src/Markets.Api/Program.cs
using FluentValidation;
using Markets.Api;
using Markets.Domain;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<IMarketRepository, InMemoryMarketRepository>();
builder.Services.AddSingleton<IValidator<CreateMarketRequest>, CreateMarketRequestValidator>();
builder.Services.AddProblemDetails();
builder.Services.AddAntiforgery();

var app = builder.Build();
app.UseHttpsRedirection();
app.UseAntiforgery();

app.MapPost("/markets", async (
    CreateMarketRequest request,
    IValidator<CreateMarketRequest> validator,
    IMarketRepository repo,
    CancellationToken ct) =>
{
    var validation = await validator.ValidateAsync(request, ct);
    if (!validation.IsValid)
    {
        return Results.ValidationProblem(validation.ToDictionary());
    }
    if (await repo.ExistsAsync(request.Symbol, ct))
    {
        return Results.Problem(
            detail: "symbol_taken", statusCode: StatusCodes.Status409Conflict);
    }
    var market = new Market(request.Symbol, request.LastPrice);
    await repo.CreateAsync(market, ct);
    return Results.Created($"/markets/{market.Symbol}", market);
});

app.Run();

public record CreateMarketRequest(string Symbol, decimal LastPrice);

public sealed class CreateMarketRequestValidator : AbstractValidator<CreateMarketRequest>
{
    public CreateMarketRequestValidator()
    {
        RuleFor(x => x.Symbol).NotEmpty().Length(1, 10).Matches("^[A-Z]+$");
        RuleFor(x => x.LastPrice).GreaterThan(0);
    }
}
```

## TDD pairing

```csharp
// tests/Markets.Api.Tests/CreateMarketTests.cs
public class CreateMarketTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    public CreateMarketTests(WebApplicationFactory<Program> factory)
        => _client = factory.CreateClient();

    [Fact]
    public async Task Post_RejectsInvalidSymbol()
    {
        var res = await _client.PostAsJsonAsync(
            "/markets", new { symbol = "", lastPrice = 1.0m });
        Assert.Equal(System.Net.HttpStatusCode.BadRequest, res.StatusCode);
    }
}
```
