# Security Standards

> Consolidated security standards: OWASP Top 10, secret scanning, dependency scanning, SAST, authentication, authorization, data protection, and compliance.

---

## 1. OWASP Top 10 (2021)

### A01: Broken Access Control

**Description:** Users act outside their intended permissions, accessing unauthorized functions or data.

**Mitigations:**
- Deny by default; require explicit grants
- Implement RBAC with resource-level checks
- Validate ownership on every data access
- Disable directory listing, restrict CORS

```typescript
// GOOD: Resource-level authorization check
async function getOrder(userId: string, orderId: string): Promise<Order> {
  const order = await orderRepository.findById(orderId);
  if (order.userId !== userId) {
    throw new ForbiddenError("Access denied to this order");
  }
  return order;
}
```

### A02: Cryptographic Failures

**Description:** Failures related to cryptography that expose sensitive data.

**Mitigations:**
- Encrypt data at rest (AES-256) and in transit (TLS 1.2+)
- Never implement custom cryptography
- Use strong password hashing (bcrypt, Argon2)
- Classify data and apply controls per classification level

### A03: Injection

**Description:** Untrusted data sent to an interpreter as part of a command or query.

**Mitigations:**
- Use parameterized queries / prepared statements (never string concatenation)
- Validate and sanitize all inputs at system boundaries
- Use ORMs with parameterized queries

```python
# GOOD: Parameterized query
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

# BAD: String concatenation (SQL injection)
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### A04: Insecure Design

**Description:** Missing or ineffective security controls due to design flaws.

**Mitigations:**
- Threat model during design phase
- Use secure design patterns (defense in depth, least privilege)
- Establish and use a secure development lifecycle
- Perform security architecture reviews

### A05: Security Misconfiguration

**Description:** Missing security hardening, default credentials, unnecessary features enabled.

**Mitigations:**
- Automated hardening process (IaC)
- Remove unused features, frameworks, and components
- Review cloud permissions and configurations
- Send security headers on all responses

### A06: Vulnerable and Outdated Components

**Description:** Using components with known vulnerabilities.

**Mitigations:**
- Automated dependency scanning in CI (Snyk, `npm audit`)
- Enable Dependabot or Renovate for automated updates
- Maintain an inventory of all components and versions
- Monitor CVE databases

### A07: Identification and Authentication Failures

**Description:** Weaknesses in authentication mechanisms.

**Mitigations:**
- Implement multi-factor authentication
- Use strong password policies (min 12 chars, check breached databases)
- Rate limit login attempts
- Use secure session management (short-lived tokens)

### A08: Software and Data Integrity Failures

**Description:** Code and infrastructure that does not protect against integrity violations.

**Mitigations:**
- Verify dependencies with checksums and lock files
- Use signed commits and CI pipeline integrity checks
- Validate data integrity with checksums
- Use trusted CI/CD pipelines

### A09: Security Logging and Monitoring Failures

**Description:** Insufficient logging, monitoring, and alerting.

**Mitigations:**
- Log all authentication events (success and failure)
- Log authorization failures
- Centralize logs with tamper-proof storage
- Set up alerts for suspicious patterns

### A10: Server-Side Request Forgery (SSRF)

**Description:** Application fetches a remote resource without validating the user-supplied URL.

**Mitigations:**
- Validate and sanitize all URLs before fetching
- Use allow-lists for external service URLs
- Block requests to internal/private IP ranges
- Disable HTTP redirects or validate redirect targets

---

## 2. Secret Scanning

### Gitleaks Configuration

```toml
# .gitleaks.toml
title = "Gitleaks Configuration"

[allowlist]
paths = [
  '''\.gitleaks\.toml$''',
  '''tests/fixtures/''',
]

[[rules]]
id = "generic-api-key"
description = "Generic API Key"
regex = '''(?i)(api[_-]?key|apikey)\s*[:=]\s*['"]?([A-Za-z0-9_\-]{20,})['"]?'''
tags = ["key", "api"]

[[rules]]
id = "azure-connection-string"
description = "Azure Connection String"
regex = '''(?i)(DefaultEndpointsProtocol|AccountKey)\s*=\s*[^\s;]+'''
tags = ["azure", "connection-string"]
```

### .gitignore Security Rules

```gitignore
# Secrets and credentials
.env
.env.*
*.pem
*.key
*credentials*
*secret*
appsettings.*.json
!appsettings.json
!appsettings.Development.json.template
```

### Secret Scanning Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Secrets in source code | Exposed in Git history | Use environment variables or vault |
| `.env` committed to repo | Plaintext secrets in Git | Add `.env` to `.gitignore` |
| Secrets in CI logs | Visible to anyone with log access | Mask secrets in pipeline config |
| Shared API keys | No individual accountability | Per-user or per-service keys |
| Long-lived tokens | Extended exposure window | Short-lived tokens with rotation |

---

## 3. Dependency Scanning

### Tools and Integration

| Tool | Scope | Integration |
|------|-------|-------------|
| Snyk | All languages | CI pipeline, IDE, PR checks |
| OWASP Dependency-Check | Java, .NET, Node, Python | CI pipeline, CLI |
| `npm audit` | Node.js | Pre-commit, CI |
| `pip-audit` | Python | CI pipeline |
| GitHub Dependabot | All supported languages | GitHub native |
| Trivy | Containers, IaC, filesystems | CI pipeline, CLI |

### CI Integration

```yaml
# GitHub Actions example
- name: Run Snyk Security Scan
  uses: snyk/actions/node@master
  with:
    args: --severity-threshold=high
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

---

## 4. Static Application Security Testing (SAST)

### CodeQL

```yaml
# .github/workflows/codeql.yml
name: CodeQL Analysis
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # Weekly Monday 6 AM

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    strategy:
      matrix:
        language: [javascript, python, csharp]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
```

### SonarQube Security Rules

Configure SonarQube to enforce security hotspot review:
- All Security Hotspots must be reviewed before merge
- Security rating must be **A** (no open vulnerabilities)
- Use SonarQube quality profiles with OWASP rules enabled

---

## 5. Authentication Patterns

### JWT Best Practices

| Practice | Requirement |
|----------|-------------|
| Algorithm | RS256 or ES256 (never HS256 in production with shared secrets) |
| Expiration | Access tokens: 15-30 minutes; Refresh tokens: 7-30 days |
| Storage | HttpOnly, Secure, SameSite cookies (never localStorage) |
| Claims | Minimal: `sub`, `iss`, `aud`, `exp`, `iat` |
| Validation | Always validate `iss`, `aud`, `exp`, and signature |

### OAuth2 / OpenID Connect

- Use Authorization Code flow with PKCE for SPAs and mobile
- Never use Implicit flow (deprecated)
- Validate `state` parameter to prevent CSRF
- Store tokens server-side when possible

### API Key Management

- Prefix keys for identification: `myapp_live_abc123...`
- Hash keys before storage (SHA-256 minimum)
- Support key rotation without downtime
- Set per-key rate limits and scopes

---

## 6. Authorization

### Role-Based Access Control (RBAC)

```typescript
// Define roles and permissions
const PERMISSIONS = {
  admin: ["read", "write", "delete", "manage-users"],
  editor: ["read", "write"],
  viewer: ["read"],
} as const;

// Middleware
function requirePermission(permission: string) {
  return (req: Request, res: Response, next: NextFunction): void => {
    const userPermissions = PERMISSIONS[req.user.role] ?? [];
    if (!userPermissions.includes(permission)) {
      throw new ForbiddenError("Insufficient permissions");
    }
    next();
  };
}
```

### Resource-Level Authorization

Always verify the requesting user has access to the specific resource, not just the action:

```python
# GOOD: Check both role AND resource ownership
async def update_document(user: User, document_id: str, data: dict) -> Document:
    document = await document_repo.get(document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} not found")
    if document.owner_id != user.id and "admin" not in user.roles:
        raise ForbiddenError("Not authorized to update this document")
    return await document_repo.update(document_id, data)
```

---

## 7. Data Protection

### Encryption Requirements

| Data State | Minimum Standard |
|------------|-----------------|
| At rest | AES-256 |
| In transit | TLS 1.2+ |
| Database fields (PII) | Column-level encryption or tokenization |
| Backups | Encrypted with separate key |
| Logs | No PII in logs; mask if unavoidable |

### PII Handling

- Classify data: Public, Internal, Confidential, Restricted
- Minimize data collection (only what is needed)
- Implement data retention policies with automated deletion
- Provide data export and deletion for GDPR compliance
- Mask PII in non-production environments

---

## 8. Security Headers

```typescript
// Required security headers
const securityHeaders = {
  "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "X-XSS-Protection": "0",  // Disabled; use CSP instead
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};
```

### CORS Configuration

```typescript
// GOOD: Restrictive CORS
const corsOptions = {
  origin: ["https://app.example.com", "https://admin.example.com"],
  methods: ["GET", "POST", "PUT", "DELETE"],
  allowedHeaders: ["Content-Type", "Authorization"],
  credentials: true,
  maxAge: 86400,
};

// BAD: Overly permissive
const corsOptions = { origin: "*" };  // Never in production
```

---

## 9. Compliance Checklist

| Category | Check | Frequency |
|----------|-------|-----------|
| Secrets | No secrets in source code (gitleaks) | Every commit |
| Dependencies | No high/critical vulnerabilities | Every build |
| SAST | No critical findings (CodeQL/SonarQube) | Every PR |
| Authentication | MFA enabled for all admin accounts | Quarterly audit |
| Authorization | RBAC permissions reviewed | Quarterly audit |
| Encryption | TLS 1.2+ enforced on all endpoints | Monthly scan |
| Headers | Security headers present on all responses | Monthly scan |
| Logging | Security events logged and monitored | Continuous |
| Data | PII handling compliant with policy | Quarterly audit |
| Infrastructure | IaC scanned for misconfigurations | Every deployment |
| Containers | Base images scanned for vulnerabilities | Every build |
| Access | Service account permissions follow least privilege | Quarterly audit |
