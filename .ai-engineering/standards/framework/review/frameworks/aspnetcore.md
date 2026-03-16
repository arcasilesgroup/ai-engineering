# ASP.NET Core Review Guidelines

## Update Metadata
- Rationale: ASP.NET Core-specific patterns for middleware, DI, EF Core, and security.

## Middleware & Pipeline
- Order matters: authentication before authorization before routing.
- Use `IMiddleware` interface for scoped middleware.
- Prefer minimal APIs for simple endpoints.

## Entity Framework Core
- Use `AsNoTracking()` for read-only queries.
- Include navigation properties explicitly — no lazy loading by default.
- Use migrations for schema changes — never manual DDL.

## Dependency Injection
- Register services with correct lifetime: Singleton, Scoped, Transient.
- Never resolve scoped services from singleton — causes captive dependency.
- Use `IOptions<T>` for configuration binding.

## Security
- Use `[Authorize]` with policies, not role strings.
- Enable HTTPS redirection and HSTS.
- Use `[ValidateAntiForgeryToken]` on form endpoints.

## References
- Enforcement: `standards/framework/stacks/dotnet.md`
