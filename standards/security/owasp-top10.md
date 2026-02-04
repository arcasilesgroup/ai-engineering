# OWASP Top 10 Security Standards

> Reference for OWASP Top 10:2025 security risks and mitigation strategies.

---

## OWASP Top 10:2025

| Rank | Category | Description |
|------|----------|-------------|
| A01 | Broken Access Control | Failure to properly enforce access restrictions |
| A02 | Security Misconfiguration | Insecure default configurations, incomplete setup |
| A03 | Software Supply Chain Failures | Vulnerable components, compromised dependencies |
| A04 | Cryptographic Failures | Weak encryption, exposed sensitive data |
| A05 | Injection | SQL, NoSQL, OS, LDAP injection attacks |
| A06 | Insecure Design | Missing security controls at design phase |
| A07 | Authentication Failures | Broken authentication mechanisms |
| A08 | Software/Data Integrity Failures | Unsigned updates, insecure deserialization |
| A09 | Security Logging/Alerting Failures | Insufficient monitoring and response |
| A10 | Mishandling of Exceptions | Improper error handling exposing information |

---

## A01: Broken Access Control

### Risk
Users can act outside their intended permissions.

### Prevention

```csharp
// ✅ Always validate authorization
[Authorize(Roles = "Admin")]
[HttpGet("admin/users")]
public async Task<IActionResult> GetUsers()
{
    // Additional resource-level check
    if (!await _authService.CanAccessResource(User, resourceId))
    {
        return Forbid();
    }
    // ...
}

// ✅ Use policy-based authorization
[Authorize(Policy = "RequireOwnership")]
public async Task<IActionResult> GetOrder(int orderId)
{
    // Policy handler validates user owns the order
}
```

### Checklist
- [ ] Deny by default, explicitly allow
- [ ] Validate user ownership of resources (IDOR prevention)
- [ ] Disable directory listing
- [ ] Log access control failures
- [ ] Rate limit API access

---

## A02: Security Misconfiguration

### Risk
Insecure defaults, incomplete configurations, verbose errors.

### Prevention

```csharp
// ✅ Disable detailed errors in production
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler("/error");
    app.UseHsts();
}

// ✅ Remove unnecessary headers
app.Use(async (context, next) =>
{
    context.Response.Headers.Remove("Server");
    context.Response.Headers.Remove("X-Powered-By");
    await next();
});

// ✅ Security headers
app.UseSecurityHeaders(policies =>
    policies
        .AddDefaultSecurityHeaders()
        .AddStrictTransportSecurityMaxAgeIncludeSubDomains(maxAgeInSeconds: 31536000)
        .AddContentSecurityPolicy(csp => csp.DefaultSources(s => s.Self()))
);
```

### Checklist
- [ ] Remove default accounts/passwords
- [ ] Disable unnecessary features
- [ ] Configure security headers (HSTS, CSP, X-Content-Type-Options)
- [ ] Review cloud storage permissions (no public buckets)
- [ ] Automate configuration validation

---

## A03: Software Supply Chain Failures

### Risk
Using components with known vulnerabilities, compromised CI/CD.

### Prevention

```yaml
# Dependabot for automated updates
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "nuget"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

# Lock file for reproducible builds
# Use packages.lock.json in .NET
```

```bash
# Regular vulnerability scanning
dotnet list package --vulnerable --include-transitive
npm audit
snyk test
```

### Checklist
- [ ] Maintain software inventory (SBOM)
- [ ] Monitor CVE databases
- [ ] Use dependency scanning (Snyk, Dependabot)
- [ ] Verify package signatures
- [ ] Pin dependency versions
- [ ] Secure CI/CD pipeline

---

## A04: Cryptographic Failures

### Risk
Exposure of sensitive data through weak cryptography.

### Prevention

```csharp
// ✅ Use strong algorithms
using var aes = Aes.Create();
aes.KeySize = 256;
aes.Mode = CipherMode.GCM;

// ✅ Hash passwords with modern algorithm
var hasher = new PasswordHasher<User>();
string hash = hasher.HashPassword(user, password);

// ✅ Use HTTPS everywhere
services.AddHttpsRedirection(options =>
{
    options.RedirectStatusCode = StatusCodes.Status308PermanentRedirect;
    options.HttpsPort = 443;
});

// ❌ Never use deprecated algorithms
// MD5, SHA1, DES, 3DES, RC4
```

### Checklist
- [ ] Encrypt data in transit (TLS 1.2+)
- [ ] Encrypt data at rest
- [ ] Use strong key derivation (PBKDF2, bcrypt, Argon2)
- [ ] Disable deprecated protocols
- [ ] Rotate keys regularly
- [ ] Never store secrets in code

---

## A05: Injection

### Risk
Untrusted data sent to interpreter as command/query.

### Prevention

```csharp
// ✅ Parameterized queries
var users = await context.Users
    .Where(u => u.Email == email)  // EF Core parameterizes automatically
    .ToListAsync();

// ✅ Explicit parameters for raw SQL
await context.Database.ExecuteSqlRawAsync(
    "SELECT * FROM Users WHERE Email = {0}",
    email);

// ❌ Never concatenate user input
var sql = $"SELECT * FROM Users WHERE Email = '{email}'";  // VULNERABLE
```

```typescript
// ✅ Use parameterized queries in Node.js
const result = await pool.query(
    'SELECT * FROM users WHERE email = $1',
    [email]
);
```

### Checklist
- [ ] Use parameterized queries/prepared statements
- [ ] Validate and sanitize all input
- [ ] Use ORMs with parameterization
- [ ] Escape special characters for context
- [ ] Implement input length limits

---

## A06: Insecure Design

### Risk
Missing security controls at architecture/design level.

### Prevention

- Threat modeling during design
- Security user stories in backlog
- Secure design patterns (Defense in Depth)
- Reference architectures

### Checklist
- [ ] Conduct threat modeling (STRIDE)
- [ ] Define security requirements
- [ ] Use secure design patterns
- [ ] Implement defense in depth
- [ ] Review architecture for security

---

## A07: Authentication Failures

### Risk
Broken authentication allowing account compromise.

### Prevention

```csharp
// ✅ Strong password policy
services.Configure<IdentityOptions>(options =>
{
    options.Password.RequireDigit = true;
    options.Password.RequireLowercase = true;
    options.Password.RequireUppercase = true;
    options.Password.RequireNonAlphanumeric = true;
    options.Password.RequiredLength = 12;

    options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
    options.Lockout.MaxFailedAccessAttempts = 5;
});

// ✅ Multi-factor authentication
services.AddIdentity<User, Role>()
    .AddDefaultTokenProviders()
    .AddTokenProvider<AuthenticatorTokenProvider<User>>("Authenticator");
```

### Checklist
- [ ] Implement MFA where possible
- [ ] Use strong password policies
- [ ] Implement account lockout
- [ ] Don't expose session IDs in URLs
- [ ] Regenerate session IDs after login
- [ ] Implement secure password recovery

---

## A08: Software/Data Integrity Failures

### Risk
Assuming integrity without verification.

### Prevention

```csharp
// ✅ Validate JWT signatures
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(key),
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ClockSkew = TimeSpan.Zero
        };
    });

// ✅ Sign NuGet packages
// Use code signing certificates
```

### Checklist
- [ ] Verify digital signatures
- [ ] Use signed packages
- [ ] Validate data integrity (checksums)
- [ ] Secure CI/CD pipeline
- [ ] Review deserialization safety

---

## A09: Security Logging/Alerting Failures

### Risk
Inability to detect, escalate, or respond to attacks.

### Prevention

```csharp
// ✅ Log security events
_logger.LogWarning(
    "Failed login attempt for user {UserId} from IP {IpAddress}",
    userId,
    ipAddress);

_logger.LogCritical(
    "Privilege escalation attempt detected for user {UserId}",
    userId);

// ✅ Structured logging for SIEM integration
services.AddApplicationInsightsTelemetry();
```

### Checklist
- [ ] Log authentication failures
- [ ] Log access control failures
- [ ] Log input validation failures
- [ ] Use centralized log management
- [ ] Set up real-time alerting
- [ ] Establish incident response plan

---

## A10: Mishandling of Exceptions

### Risk
Information leakage through detailed error messages.

### Prevention

```csharp
// ✅ Generic error responses to clients
app.UseExceptionHandler(errorApp =>
{
    errorApp.Run(async context =>
    {
        context.Response.StatusCode = 500;
        context.Response.ContentType = "application/json";

        await context.Response.WriteAsJsonAsync(new
        {
            Error = "An unexpected error occurred.",
            TraceId = Activity.Current?.Id ?? context.TraceIdentifier
        });
    });
});

// ✅ Log full details internally
catch (Exception ex)
{
    _logger.LogError(ex, "Error processing request {RequestId}", requestId);
    throw;  // Re-throw for global handler
}
```

### Checklist
- [ ] Never expose stack traces in production
- [ ] Use generic error messages for clients
- [ ] Log detailed errors internally
- [ ] Handle all exception types
- [ ] Test error handling paths
