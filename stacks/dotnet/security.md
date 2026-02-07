# .NET Security Standards

Follow these security standards for all .NET code generation. Security is non-negotiable: never skip these rules, never leave security as a TODO, and never generate code with known vulnerabilities.

---

## Authentication

### JWT Bearer Authentication

Use JWT bearer tokens for API authentication. Always validate issuer, audience, and lifetime.

```csharp
// DO
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Key"]!)),
            ClockSkew = TimeSpan.FromMinutes(1) // reduce default 5-minute skew
        };
    });

// DON'T
options.TokenValidationParameters = new TokenValidationParameters
{
    ValidateIssuer = false,       // NEVER disable validation
    ValidateAudience = false,     // NEVER disable validation
    ValidateLifetime = false,     // NEVER disable validation
};
```

### Cookie Authentication

Use cookie authentication for server-rendered applications. Always set secure cookie properties.

```csharp
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.Cookie.HttpOnly = true;
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.ExpireTimeSpan = TimeSpan.FromHours(1);
        options.SlidingExpiration = true;
        options.LoginPath = "/auth/login";
        options.AccessDeniedPath = "/auth/access-denied";
    });
```

### ASP.NET Core Identity

When using Identity, configure password and lockout policies strictly.

```csharp
builder.Services.AddIdentity<ApplicationUser, IdentityRole>(options =>
{
    // Password policy
    options.Password.RequiredLength = 12;
    options.Password.RequireDigit = true;
    options.Password.RequireLowercase = true;
    options.Password.RequireUppercase = true;
    options.Password.RequireNonAlphanumeric = true;
    options.Password.RequiredUniqueChars = 4;

    // Lockout policy
    options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
    options.Lockout.MaxFailedAccessAttempts = 5;
    options.Lockout.AllowedForNewUsers = true;

    // User settings
    options.User.RequireUniqueEmail = true;
    options.SignIn.RequireConfirmedEmail = true;
})
.AddEntityFrameworkStores<AppDbContext>()
.AddDefaultTokenProviders();
```

---

## Authorization

### Policy-Based Authorization

Define authorization policies for fine-grained access control. Prefer policies over raw role checks.

```csharp
// DO - Policy-based
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("AdminOnly", policy =>
        policy.RequireRole("Admin"))
    .AddPolicy("CanManageOrders", policy =>
        policy.RequireClaim("permission", "orders:manage"))
    .AddPolicy("MinimumAge", policy =>
        policy.Requirements.Add(new MinimumAgeRequirement(18)));

// Usage in controllers
[Authorize(Policy = "CanManageOrders")]
[HttpPost]
public async Task<IActionResult> CreateOrder(CreateOrderRequest request) { }
```

### Resource-Based Authorization

Use resource-based authorization when access depends on the resource being accessed.

```csharp
// Authorization handler
public class OrderAuthorizationHandler : AuthorizationHandler<OperationAuthorizationRequirement, Order>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        OperationAuthorizationRequirement requirement,
        Order resource)
    {
        var userId = context.User.FindFirstValue(ClaimTypes.NameIdentifier);

        if (requirement.Name == Operations.Read.Name)
        {
            if (resource.CustomerId.ToString() == userId ||
                context.User.IsInRole("Admin"))
            {
                context.Succeed(requirement);
            }
        }

        return Task.CompletedTask;
    }
}

// Usage in controller
[HttpGet("{id:guid}")]
public async Task<IActionResult> GetOrder(Guid id, CancellationToken cancellationToken)
{
    var order = await _orderService.GetByIdAsync(id, cancellationToken);
    if (order is null) return NotFound();

    var authResult = await _authorizationService.AuthorizeAsync(
        User, order, Operations.Read);

    if (!authResult.Succeeded) return Forbid();

    return Ok(order.ToResponse());
}
```

---

## CORS Configuration

Never use wildcard origins in production. Always specify exact origins.

```csharp
// DO
builder.Services.AddCors(options =>
{
    options.AddPolicy("Production", policy =>
    {
        policy.WithOrigins(
                "https://myapp.com",
                "https://www.myapp.com")
            .WithMethods("GET", "POST", "PUT", "DELETE")
            .WithHeaders("Content-Type", "Authorization")
            .SetPreflightMaxAge(TimeSpan.FromMinutes(10));
    });
});

// DON'T
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()     // NEVER in production
              .AllowAnyMethod()     // too permissive
              .AllowAnyHeader();    // too permissive
    });
});
```

---

## Data Protection API

Use the Data Protection API for encrypting sensitive data at rest (tokens, cookies, temporary secrets).

```csharp
// Registration
builder.Services.AddDataProtection()
    .PersistKeysToDbContext<AppDbContext>()
    .SetApplicationName("MyApp")
    .SetDefaultKeyLifetime(TimeSpan.FromDays(90));

// Usage
public class TokenService
{
    private readonly IDataProtector _protector;

    public TokenService(IDataProtectionProvider provider)
    {
        _protector = provider.CreateProtector("MyApp.Tokens.v1");
    }

    public string Protect(string plainText) => _protector.Protect(plainText);
    public string Unprotect(string protectedText) => _protector.Unprotect(protectedText);
}
```

---

## Anti-Forgery Tokens

Always use anti-forgery tokens for form-based mutations. ASP.NET Core's `[ValidateAntiForgeryToken]` handles this automatically for Razor Pages and MVC.

```csharp
// DO - Global anti-forgery for MVC
builder.Services.AddControllersWithViews(options =>
{
    options.Filters.Add(new AutoValidateAntiforgeryTokenAttribute());
});

// For APIs, use the SameSite cookie attribute and custom header validation
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-XSRF-TOKEN";
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
});
```

---

## SQL Injection Prevention

### Always Use Parameterized Queries

Never concatenate user input into SQL strings.

```csharp
// DON'T - SQL injection vulnerability
var query = $"SELECT * FROM Orders WHERE CustomerName = '{customerName}'";
var orders = await _dbContext.Orders.FromSqlRaw(query).ToListAsync();

// DO - Parameterized query
var orders = await _dbContext.Orders
    .FromSqlInterpolated($"SELECT * FROM Orders WHERE CustomerName = {customerName}")
    .ToListAsync(cancellationToken);

// DO - LINQ (automatically parameterized)
var orders = await _dbContext.Orders
    .Where(o => o.CustomerName == customerName)
    .ToListAsync(cancellationToken);

// DO - Dapper with parameters
var orders = await connection.QueryAsync<Order>(
    "SELECT * FROM Orders WHERE CustomerName = @Name",
    new { Name = customerName });
```

---

## XSS Prevention

### Output Encoding

ASP.NET Core Razor automatically HTML-encodes output. Never use `Html.Raw()` with user input.

```csharp
// DO - Automatic encoding in Razor
<p>@Model.UserComment</p>  <!-- automatically HTML-encoded -->

// DON'T
<p>@Html.Raw(Model.UserComment)</p>  <!-- XSS vulnerability -->
```

### Content Security Policy

Set CSP headers to prevent inline script execution.

```csharp
app.Use(async (context, next) =>
{
    context.Response.Headers.Append(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';");
    await next();
});
```

### Input Sanitization

Sanitize any user input that will be stored or displayed. Use a library like HtmlSanitizer for rich text.

```csharp
// DO - Sanitize rich text input
public class CommentService
{
    private readonly HtmlSanitizer _sanitizer;

    public CommentService()
    {
        _sanitizer = new HtmlSanitizer();
        _sanitizer.AllowedTags.Clear();
        _sanitizer.AllowedTags.Add("b");
        _sanitizer.AllowedTags.Add("i");
        _sanitizer.AllowedTags.Add("p");
        _sanitizer.AllowedTags.Add("br");
    }

    public string Sanitize(string userInput) => _sanitizer.Sanitize(userInput);
}
```

---

## Secret Management

### Never Hard-Code Secrets

Never put secrets in source code, `appsettings.json`, or environment variables committed to source control.

```csharp
// DON'T
var connectionString = "Server=prod;Database=MyDb;User=sa;Password=P@ssw0rd123!;";
var apiKey = "sk-1234567890abcdef";

// DO - Development: User Secrets
// dotnet user-secrets set "ConnectionStrings:DefaultConnection" "Server=localhost;..."
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");

// DO - Production: Azure Key Vault
builder.Configuration.AddAzureKeyVault(
    new Uri($"https://{builder.Configuration["KeyVault:Name"]}.vault.azure.net/"),
    new DefaultAzureCredential());

// DO - Production: Environment variables (set on the host, not in code)
var apiKey = builder.Configuration["ExternalService:ApiKey"];
```

### .gitignore

Always ensure these files are in `.gitignore`:

```
appsettings.Development.json
appsettings.Local.json
*.pfx
*.p12
secrets.json
.env
```

---

## HTTPS Enforcement

Always enforce HTTPS in production. Redirect HTTP to HTTPS.

```csharp
// DO
if (!app.Environment.IsDevelopment())
{
    app.UseHsts();
}
app.UseHttpsRedirection();

// In production configuration
builder.Services.AddHttpsRedirection(options =>
{
    options.RedirectStatusCode = StatusCodes.Status307TemporaryRedirect;
    options.HttpsPort = 443;
});

builder.Services.AddHsts(options =>
{
    options.Preload = true;
    options.IncludeSubDomains = true;
    options.MaxAge = TimeSpan.FromDays(365);
});
```

---

## Security Headers

Add security headers to every response. Use middleware or a library like NWebsec.

```csharp
// DO - Security headers middleware
app.Use(async (context, next) =>
{
    var headers = context.Response.Headers;

    headers.Append("X-Content-Type-Options", "nosniff");
    headers.Append("X-Frame-Options", "DENY");
    headers.Append("X-XSS-Protection", "0"); // Disabled; CSP is the modern replacement
    headers.Append("Referrer-Policy", "strict-origin-when-cross-origin");
    headers.Append("Permissions-Policy",
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()");
    headers.Remove("X-Powered-By");
    headers.Remove("Server");

    await next();
});
```

---

## Input Validation and Model Binding

### Validate All Input

Never trust client input. Validate at the API boundary and again at the domain level.

```csharp
// DO - API-level validation with FluentValidation
public class CreateOrderRequestValidator : AbstractValidator<CreateOrderRequest>
{
    public CreateOrderRequestValidator()
    {
        RuleFor(x => x.CustomerName)
            .NotEmpty()
            .MaximumLength(200)
            .Matches(@"^[\w\s\-'.]+$").WithMessage("Customer name contains invalid characters.");

        RuleFor(x => x.Email)
            .NotEmpty()
            .EmailAddress();

        RuleFor(x => x.Lines)
            .NotEmpty()
            .Must(lines => lines.Count <= 100)
            .WithMessage("Order cannot exceed 100 lines.");

        RuleForEach(x => x.Lines).ChildRules(line =>
        {
            line.RuleFor(l => l.Quantity).InclusiveBetween(1, 9999);
            line.RuleFor(l => l.UnitPrice).InclusiveBetween(0.01m, 999_999.99m);
        });
    }
}
```

### Restrict Model Binding

Only bind expected properties to prevent over-posting attacks.

```csharp
// DON'T - Binding directly to entity (mass assignment vulnerability)
[HttpPost]
public async Task<IActionResult> Create(Order order)  // attacker can set order.Id, order.Status, etc.

// DO - Bind to a dedicated DTO
[HttpPost]
public async Task<IActionResult> Create(CreateOrderRequest request)
// CreateOrderRequest only has the properties the client is allowed to set

// DO - Use [Bind] attribute if you must bind to an entity
[HttpPost]
public async Task<IActionResult> Create([Bind("CustomerName", "Email")] Order order)
```

---

## Rate Limiting

Use built-in rate limiting (.NET 7+) to protect against abuse.

```csharp
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;

    // Fixed window: 100 requests per minute
    options.AddFixedWindowLimiter("fixed", config =>
    {
        config.PermitLimit = 100;
        config.Window = TimeSpan.FromMinutes(1);
        config.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
        config.QueueLimit = 10;
    });

    // Sliding window for API endpoints
    options.AddSlidingWindowLimiter("api", config =>
    {
        config.PermitLimit = 60;
        config.Window = TimeSpan.FromMinutes(1);
        config.SegmentsPerWindow = 6;
    });

    // Token bucket for burst-tolerant endpoints
    options.AddTokenBucketLimiter("burst", config =>
    {
        config.TokenLimit = 20;
        config.ReplenishmentPeriod = TimeSpan.FromSeconds(10);
        config.TokensPerPeriod = 5;
    });

    // Per-user rate limiting
    options.AddPolicy("per-user", context =>
    {
        var userId = context.User?.FindFirstValue(ClaimTypes.NameIdentifier) ?? "anonymous";
        return RateLimitPartition.GetFixedWindowLimiter(userId, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 30,
            Window = TimeSpan.FromMinutes(1)
        });
    });
});

app.UseRateLimiter();

// Apply to specific endpoints
app.MapPost("/api/orders", CreateOrder).RequireRateLimiting("api");
app.MapPost("/api/auth/login", Login).RequireRateLimiting("burst");
```

---

## OWASP Compliance Checklist

Before generating or reviewing .NET code, verify against the OWASP Top 10:

| OWASP Risk | .NET Mitigation |
|------------|-----------------|
| **A01 - Broken Access Control** | Policy-based authorization, resource-based authorization, `[Authorize]` on all endpoints by default |
| **A02 - Cryptographic Failures** | Data Protection API, HTTPS enforcement, no hard-coded secrets |
| **A03 - Injection** | Parameterized queries, EF Core LINQ, never concatenate SQL |
| **A04 - Insecure Design** | Input validation, FluentValidation, DTOs (never bind to entities) |
| **A05 - Security Misconfiguration** | Security headers, CORS with specific origins, remove server headers |
| **A06 - Vulnerable Components** | `dotnet list package --vulnerable`, regular dependency updates |
| **A07 - Auth Failures** | Strong password policy, account lockout, JWT validation |
| **A08 - Data Integrity Failures** | Anti-forgery tokens, signed JWTs, CSP headers |
| **A09 - Logging Failures** | Structured logging, audit trails, never log secrets |
| **A10 - SSRF** | Validate and allowlist external URLs, restrict outbound connections |

### Never Log Sensitive Data

```csharp
// DON'T
_logger.LogInformation("User login: {Email} with password {Password}", email, password);
_logger.LogDebug("API key: {ApiKey}", apiKey);
_logger.LogInformation("Credit card: {CardNumber}", cardNumber);

// DO
_logger.LogInformation("User login attempt for {Email}", email);
_logger.LogDebug("External API call initiated for service {ServiceName}", serviceName);
```

### Check for Vulnerable Packages

Regularly audit dependencies for known vulnerabilities.

```bash
dotnet list package --vulnerable
dotnet list package --outdated
```

---

## Summary Checklist

Before generating or reviewing security-related .NET code, verify:

- [ ] JWT tokens validate issuer, audience, lifetime, and signing key
- [ ] Cookies are HttpOnly, Secure, and SameSite=Strict
- [ ] Authorization uses policies, not raw role strings in controllers
- [ ] CORS specifies exact origins (no wildcards in production)
- [ ] All SQL uses parameterized queries or EF Core LINQ
- [ ] User input is validated at the API boundary
- [ ] DTOs are used for model binding (no direct entity binding)
- [ ] Secrets are stored in User Secrets (dev) or Key Vault (prod)
- [ ] HTTPS is enforced with HSTS
- [ ] Security headers are set on all responses
- [ ] Rate limiting is configured on all public endpoints
- [ ] Sensitive data is never logged
- [ ] Anti-forgery tokens are used for form submissions
- [ ] Vulnerable packages are checked regularly
