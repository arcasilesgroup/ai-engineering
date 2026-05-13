# C# — Security Floor

Minimum bar for `ai-build` output in C# / .NET. Every control below
is mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input parsed via `System.Text.Json` with explicit DTO
  records. Reject unknown fields where the threat model warrants.
- Validate after deserialisation using DataAnnotations or
  FluentValidation; throw a typed exception before the value reaches
  business logic.
- Use `[FromBody]`, `[FromRoute]`, `[FromQuery]` explicitly in MVC /
  Minimal API endpoints — never bind from `dynamic`.

## Confidential configuration

- Read configuration via `IConfiguration` + bound options classes
  (`services.Configure<MarketsOptions>(...)`).
- Never log raw confidential values, even at debug. Use Serilog with
  destructuring policies that redact known-confidential field names.
- Local development: `dotnet user-secrets`. CI/Production: vaults
  (Azure Key Vault, AWS Secrets Manager) — never hard-code in
  `appsettings.json`.

## Dependencies

- `dotnet list package --vulnerable --include-transitive` in CI on
  every PR (failing the pipeline if any are flagged).
- Renovate / Dependabot configured to track CVEs.
- Pin direct dependencies in csproj; avoid wildcard versions.
- Ban legacy NuGet packages with known issues (`Newtonsoft.Json` if
  System.Text.Json suffices, etc.).

## OWASP top hits (web)

- **Injection**: parameterised queries via Entity Framework / Dapper.
  Never `string.Format` a SQL query.
- **Broken access control**: `[Authorize]` plus per-resource policy
  handlers. Default-deny.
- **XSS**: Razor auto-escapes by default; never call `Html.Raw` on
  user-supplied input.
- **CSRF**: ASP.NET Core anti-forgery middleware on for all
  cookie-authenticated state-changing routes.
- **SSRF**: outbound HTTP allowlist when fetching user-supplied URLs;
  use `IHttpClientFactory` so policy can be applied centrally.

## Cryptography

- Never roll your own. Use `System.Security.Cryptography` primitives.
- Hash login material with `Microsoft.AspNetCore.Identity` (PBKDF2
  with strong iteration count) or `Konscious.Security.Cryptography`
  for argon2id.
- Use AES-GCM (`AesGcm`) for symmetric, ECDsa or Ed25519
  (`System.Security.Cryptography`) for signing.
- Random IDs: `RandomNumberGenerator.Create()`; never `Random` for
  security-relevant values.

## TLS

- HTTPS-only outbound; do not configure
  `ServerCertificateCustomValidationCallback` to always return true
  outside a one-off debug script.
- `app.UseHsts()` in production startup.

## Static analysis

- Roslyn analyzers via `<EnableNETAnalyzers>true</EnableNETAnalyzers>`
  and `<AnalysisMode>AllEnabledByDefault</AnalysisMode>`.
- Security-focused: `Microsoft.CodeAnalysis.NetAnalyzers` with
  `CA2100` (SQL string concat), `CA3001` (XSS), `CA5350` series
  (cryptography misuse) at error level.
- `gitleaks` or `trufflehog` on every PR.
- `Snyk` or `JFrog Xray` for deeper supply-chain checks.
