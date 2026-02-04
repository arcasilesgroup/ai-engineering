# Skill: Security Review

---
id: cross-cutting/security-review
name: Security Review
complexity: high
estimated_time: 30 minutes
---

## Description

Performs a comprehensive security review of code changes, identifying vulnerabilities, recommending mitigations, and ensuring compliance with security standards.

## Prerequisites

- Code changes to review
- Access to security guidelines
- Understanding of data sensitivity

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Files/Changes | Yes | Code to review |
| Context | Yes | Feature description |
| Data sensitivity | No | PII, financial, health data |
| Threat model | No | Known threats to consider |

## Outputs

- Security findings report
- Remediation recommendations
- Risk assessment

## Security Checklist by Category

### 1. Authentication & Authorization

- [ ] All endpoints require authentication
- [ ] Authorization checks at controller and service level
- [ ] No hardcoded credentials
- [ ] Secrets from Key Vault only
- [ ] Token validation is complete (issuer, audience, expiry)
- [ ] Role-based access control implemented
- [ ] Session management is secure

### 2. Input Validation

- [ ] All inputs validated (type, range, format)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] Path traversal prevention
- [ ] XML/JSON injection prevention
- [ ] File upload restrictions (type, size)
- [ ] Request size limits configured

### 3. Data Protection

- [ ] Sensitive data encrypted at rest
- [ ] Sensitive data encrypted in transit (TLS 1.2+)
- [ ] PII handling complies with GDPR
- [ ] Data masking in logs
- [ ] No sensitive data in URLs
- [ ] Proper data retention policies

### 4. Error Handling

- [ ] No stack traces in production responses
- [ ] Generic error messages to clients
- [ ] Detailed errors logged server-side only
- [ ] No sensitive data in error messages
- [ ] Consistent error format

### 5. Logging & Monitoring

- [ ] Security events logged
- [ ] No sensitive data in logs
- [ ] Log injection prevention
- [ ] Audit trail for critical operations
- [ ] Correlation IDs for tracing

### 6. API Security

- [ ] Rate limiting implemented
- [ ] CORS properly configured
- [ ] Security headers set (CSP, HSTS, etc.)
- [ ] API versioning strategy secure
- [ ] Deprecation handled gracefully

### 7. Infrastructure

- [ ] Network segmentation
- [ ] Firewall rules configured
- [ ] Key rotation policies
- [ ] Dependency vulnerabilities checked
- [ ] Container security best practices

## Common Vulnerabilities

### Injection Flaws

```csharp
// ❌ Vulnerable to SQL injection
string query = $"SELECT * FROM Users WHERE Id = {userId}";

// ✅ Parameterized query
var user = await context.Users
    .FirstOrDefaultAsync(u => u.Id == userId);
```

### Broken Authentication

```csharp
// ❌ Weak token validation
if (token == expectedToken) { /* ... */ }

// ✅ Proper token validation
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = configuration["Auth:Authority"];
        options.Audience = configuration["Auth:Audience"];
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ClockSkew = TimeSpan.Zero
        };
    });
```

### Sensitive Data Exposure

```csharp
// ❌ Logging sensitive data
_logger.LogInformation("User {Email} with password {Password}", email, password);

// ✅ Masked logging
_logger.LogInformation("User {Email} authenticated", email);
```

### Missing Function Level Access Control

```csharp
// ❌ No authorization check
[HttpDelete("{id}")]
public async Task<IActionResult> Delete(int id)

// ✅ With authorization
[HttpDelete("{id}")]
[Authorize(Policy = "AdminOnly")]
public async Task<IActionResult> Delete(int id)
```

### Security Misconfiguration

```csharp
// ❌ Permissive CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
        policy.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader());
});

// ✅ Restrictive CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("Production", policy =>
        policy.WithOrigins("https://app.company.com")
              .WithMethods("GET", "POST")
              .WithHeaders("Authorization", "Content-Type"));
});
```

## Risk Assessment Matrix

| Severity | Likelihood | Risk Level | Action Required |
|----------|------------|------------|-----------------|
| Critical | High | Critical | Immediate fix |
| Critical | Medium | High | Fix before release |
| High | High | High | Fix before release |
| High | Medium | Medium | Fix in sprint |
| Medium | High | Medium | Fix in sprint |
| Medium | Medium | Low | Backlog item |
| Low | Any | Low | Nice to have |

## Report Template

```markdown
# Security Review Report

**Date:** YYYY-MM-DD
**Reviewer:** [Name]
**Scope:** [Feature/Files reviewed]

## Executive Summary

[Brief overview of findings]

## Findings

### Finding 1: [Title]

**Severity:** Critical | High | Medium | Low
**Location:** [File:Line]
**Description:** [What was found]
**Impact:** [Potential consequences]
**Recommendation:** [How to fix]
**Status:** Open | Mitigated | Accepted Risk

### Finding 2: [Title]

[Same structure]

## Recommendations

1. [Priority 1 recommendation]
2. [Priority 2 recommendation]
3. [Priority 3 recommendation]

## Conclusion

[Overall security posture assessment]
```

## Security Standards Reference

### OWASP Top 10 (2021)

1. A01 - Broken Access Control
2. A02 - Cryptographic Failures
3. A03 - Injection
4. A04 - Insecure Design
5. A05 - Security Misconfiguration
6. A06 - Vulnerable Components
7. A07 - Authentication Failures
8. A08 - Data Integrity Failures
9. A09 - Logging Failures
10. A10 - SSRF

### CWE Common Weaknesses

- CWE-89: SQL Injection
- CWE-79: Cross-site Scripting
- CWE-287: Improper Authentication
- CWE-862: Missing Authorization
- CWE-200: Exposure of Sensitive Information

## Related Skills

- [Create ADR](./create-adr/skill.md)
- [Code Review](../../prompts/templates/code-review.md)

## Example Invocation

```
Perform security review:
- Files: UserController.cs, AuthService.cs
- Context: New user registration feature
- Data: PII (email, phone, address)
- Focus: Authentication, input validation, data protection
```
