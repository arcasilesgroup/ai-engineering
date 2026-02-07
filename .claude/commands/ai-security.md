# /ai-security — Security Audit Workflow

This skill defines the step-by-step workflow for performing a comprehensive security audit of a codebase. It covers the OWASP Top 10, dependency vulnerabilities, secrets exposure, configuration review, authentication and authorization patterns, and input validation. The output is a structured security report with severity ratings and actionable remediation steps.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established security conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — **Security Memory**: known security issues from previous audits to avoid repeating false alarms or missing known risks
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
5. Identify the current branch and working tree state

Do not report this step to the user. Internalize it as context for the audit.

---

## Depth Levels

This audit supports three depth levels. If the user does not specify, default to **Standard**.

### Level 1: Quick (automated scans only)

- Dependency audit (`npm audit`, `pip-audit`, etc.)
- Secrets scan (`gitleaks`)
- Estimated time: 2-5 minutes

### Level 2: Standard (default)

- Everything in Level 1
- OWASP Top 10 code review
- Configuration review
- Input validation review
- Estimated time: 10-20 minutes

### Level 3: Deep (comprehensive)

- Everything in Level 2
- Authentication and authorization flow analysis
- Data flow tracing (where does user input go?)
- Threat modeling (identify attack surfaces and vectors)
- Historical secrets scan (full git history)
- Estimated time: 30+ minutes

The user can specify the level: `/ai-security quick`, `/ai-security standard`, `/ai-security deep`.

---

## Trigger

- User invokes `/ai-security`
- User invokes `/ai-security quick` — Level 1 only
- User invokes `/ai-security deep` — Level 3 (comprehensive)
- User says "security audit", "security scan", "check for vulnerabilities", or similar intent

---

## Prerequisites

Before starting, verify:

- The current directory is a project with recognizable structure.
- Identify the technology stack to determine which tools and checks apply.
- Note which security tools are available on the system:

```bash
# Check for available tools
which gitleaks 2>/dev/null && echo "gitleaks: available" || echo "gitleaks: NOT installed"
which trivy 2>/dev/null && echo "trivy: available" || echo "trivy: NOT installed"
npm audit --help 2>/dev/null && echo "npm audit: available" || echo "npm: NOT installed"
pip-audit --help 2>/dev/null && echo "pip-audit: available" || echo "pip-audit: NOT installed"
dotnet list package --help 2>/dev/null && echo "dotnet: available" || echo "dotnet: NOT installed"
```

If critical tools are missing, report which tools are unavailable and which checks will be skipped. Recommend installation where possible.

---

## Step 1: OWASP Top 10 Review

Systematically review the codebase against each OWASP Top 10 category.

### A01: Broken Access Control

- Search for authorization checks on route handlers, controllers, and API endpoints.
- Identify endpoints that perform data access without verifying the requesting user's permissions.
- Look for direct object references (IDs in URLs or request bodies) without ownership validation.
- Check for missing authorization on administrative or privileged operations.

```bash
# Find route definitions
grep -rn "app\.\(get\|post\|put\|patch\|delete\)\|@Get\|@Post\|@Put\|@Controller\|\[HttpGet\]\|\[HttpPost\]\|@app\.route" src/
# Look for authorization middleware/decorators
grep -rn "authorize\|@auth\|requireAuth\|isAuthenticated\|checkPermission\|\[Authorize\]" src/
```

### A02: Cryptographic Failures

- Search for weak or outdated cryptographic algorithms (MD5, SHA-1, DES, RC4).
- Check for hardcoded encryption keys or initialization vectors.
- Verify that sensitive data is encrypted at rest and in transit.
- Check TLS configuration if applicable.

```bash
grep -rn "md5\|sha1\|sha-1\|DES\|RC4\|createHash.*md5\|createHash.*sha1" src/
grep -rn "encryptionKey\|secretKey\|iv.*=.*['\"]" src/
```

### A03: Injection

- Search for SQL string concatenation or template literal interpolation in queries.
- Check for command injection vectors (`exec`, `spawn`, `system`, `eval`).
- Look for LDAP, XPath, or NoSQL injection patterns.
- Verify that all database queries use parameterized statements.

```bash
grep -rn "exec(\|spawn(\|system(\|eval(\|Function(\|child_process" src/
grep -rn "SELECT.*\+\|INSERT.*\+\|UPDATE.*\+\|DELETE.*\+" src/
grep -rn "\`.*\${.*}\`.*query\|\.query.*\`" src/
```

### A04: Insecure Design

- Review authentication and authorization architecture.
- Check for missing rate limiting on sensitive endpoints (login, password reset, API).
- Identify business logic that lacks abuse prevention.
- Review error handling for information leakage.

### A05: Security Misconfiguration

- Check for debug mode enabled in production configurations.
- Search for default credentials or example secrets left in configuration.
- Verify that unnecessary features, ports, or services are disabled.
- Check that directory listing is disabled.

```bash
grep -rn "DEBUG.*=.*[Tt]rue\|debug.*:.*true\|NODE_ENV.*development" src/ config/
grep -rn "password.*=.*['\"]\(admin\|password\|123\|test\|default\)" src/ config/
```

### A06: Vulnerable and Outdated Components

Covered in depth in Step 2 (Dependency Audit).

### A07: Identification and Authentication Failures

- Review session management (token generation, expiry, invalidation).
- Check password hashing algorithms (must be bcrypt, scrypt, or Argon2id).
- Look for missing MFA support on sensitive operations.
- Check for session fixation vulnerabilities.

```bash
grep -rn "bcrypt\|argon2\|scrypt\|pbkdf2" src/
grep -rn "jwt\.sign\|jwt\.verify\|jsonwebtoken\|jose" src/
grep -rn "session\|cookie\|token.*expir" src/
```

### A08: Software and Data Integrity Failures

- Check CI/CD pipeline configurations for unsigned actions or unpinned versions.
- Review deserialization of untrusted data.
- Check for `eval()` or dynamic code execution with user input.

```bash
grep -rn "JSON\.parse\|pickle\.loads\|yaml\.load\|deserialize\|eval(" src/
```

### A09: Security Logging and Monitoring Failures

- Verify that authentication events are logged.
- Check that authorization failures are logged.
- Verify that logs do not contain secrets, tokens, or excessive PII.

```bash
grep -rn "logger\.\|console\.log\|logging\.\|log\." src/ | grep -i "password\|token\|secret\|key\|credential"
```

### A10: Server-Side Request Forgery (SSRF)

- Search for HTTP requests where the URL is derived from user input.
- Check for URL allowlisting on outbound requests.
- Verify that internal network addresses are blocked in outbound requests.

```bash
grep -rn "fetch(\|axios\.\|http\.get\|http\.request\|urllib\|requests\.\(get\|post\)" src/
```

---

## Step 2: Dependency Audit

Run automated dependency vulnerability scanning using the stack-appropriate tool.

### Node.js / npm

```bash
npm audit --json
# Or if using yarn
yarn audit --json
# Or if using pnpm
pnpm audit --json
```

### Python / pip

```bash
pip-audit --format json
# Or
safety check --json
```

### .NET / NuGet

```bash
dotnet list package --vulnerable --include-transitive --format json
```

### Go

```bash
govulncheck ./...
```

### Rust

```bash
cargo audit --json
```

### General (Trivy)

```bash
trivy fs --format json --severity HIGH,CRITICAL .
```

### Output Processing

For each vulnerability found, report:

- Package name and version
- Vulnerability ID (CVE number)
- Severity (critical/high/medium/low)
- Whether a patched version is available
- Whether the vulnerable code path is actually reachable in this project

```
Dependency vulnerabilities found:
  CRITICAL: lodash@4.17.20 — CVE-2021-23337 (Prototype Pollution)
    Patched in: 4.17.21
    Remediation: npm update lodash

  HIGH: jsonwebtoken@8.5.1 — CVE-2022-23529 (Insecure token verification)
    Patched in: 9.0.0
    Remediation: npm update jsonwebtoken (breaking changes — review migration guide)

  MEDIUM: semver@5.7.1 — CVE-2022-25883 (ReDoS)
    Patched in: 5.7.2
    Remediation: npm update semver
```

---

## Step 3: Secrets Scan

Run `gitleaks` on the full repository history to detect any secrets that have been committed.

```bash
# Scan full git history
gitleaks detect --source . --verbose --report-format json --report-path /tmp/gitleaks-report.json

# Scan current working directory (uncommitted files)
gitleaks detect --source . --no-git --verbose --report-format json
```

### What to Look For

- API keys (AWS, GCP, Azure, Stripe, SendGrid, Twilio, etc.)
- Database connection strings with embedded credentials
- Private keys (RSA, ECDSA, PGP)
- OAuth client secrets
- JWT signing secrets
- Basic auth credentials
- Webhook secrets
- Encryption keys

### If Secrets Are Found

For each secret detected:

1. Report the file, line number, and type of secret (without revealing the actual value).
2. Check if the file is in `.gitignore` (it should be if it contains secrets).
3. Determine if the secret is in the current working tree or only in git history.
4. Provide remediation:
   - **Current files:** Remove the secret, move it to environment variables or a secrets manager.
   - **Git history:** The secret must be rotated immediately. Removing from history is not sufficient — assume the secret is compromised.

```
Secrets detected:
  CRITICAL: AWS Access Key found in src/config/aws.ts:12 (in current tree)
    Type: AWS Access Key ID
    Remediation: Remove from source. Store in environment variable. Rotate the key immediately.

  HIGH: Generic API key found in git history (commit abc1234, file: config/old-settings.js, since deleted)
    Type: Generic API Token
    Remediation: Rotate this key. It exists in git history and should be considered compromised.
```

---

## Step 4: Configuration Review

Review security-related configuration for the application.

### Security Headers

Check if the application sets required security headers (per the framework's universal security standards):

| Header                      | Expected                                               |
| --------------------------- | ------------------------------------------------------ |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload`         |
| `X-Content-Type-Options`    | `nosniff`                                              |
| `X-Frame-Options`           | `DENY` or `SAMEORIGIN`                                 |
| `Content-Security-Policy`   | Defined and strict (no `unsafe-inline`, `unsafe-eval`) |
| `Referrer-Policy`           | `strict-origin-when-cross-origin` or stricter          |
| `Permissions-Policy`        | Defined and restrictive                                |

```bash
grep -rn "helmet\|security.headers\|X-Content-Type\|Content-Security-Policy\|Strict-Transport\|X-Frame-Options" src/ config/
```

### CORS Configuration

- Check that `Access-Control-Allow-Origin` is not set to `*` on authenticated endpoints.
- Verify that allowed origins are explicitly listed, not dynamically reflected from the request.
- Check that allowed methods and headers are restricted.

```bash
grep -rn "cors\|Access-Control\|allowedOrigins\|origin.*\*" src/ config/
```

### Environment Configuration

- Verify that production configurations disable debug mode.
- Check that error responses do not expose stack traces in production.
- Verify that default ports and endpoints are documented and intentional.

---

## Step 5: Authentication and Authorization Review

Review the authentication and authorization implementation in depth.

### Authentication

- **Password storage:** Verify bcrypt/scrypt/Argon2id is used. Check work factor / cost parameter.
- **Token management:** Verify JWT configuration (algorithm, expiry, signing key source). Check that tokens are validated on every request.
- **Session management:** Verify session tokens are cryptographically random, have appropriate expiry, and are invalidated on logout.
- **Account security:** Check for brute-force protection (rate limiting, account lockout, progressive delays).

### Authorization

- **Route protection:** Verify that every non-public endpoint has an authorization check.
- **Resource-level access:** Verify that users can only access their own resources (not just "is logged in" but "owns this resource").
- **Role hierarchy:** If roles exist, verify that privilege escalation is not possible through API manipulation.
- **Admin functions:** Verify that administrative operations have additional authorization requirements.

```bash
# Find all route handlers
grep -rn "router\.\|app\.\(get\|post\|put\|delete\)\|@Controller\|@Get\|@Post" src/
# Cross-reference with auth middleware
grep -rn "authenticate\|authorize\|requireRole\|checkPermission\|\[Authorize\]" src/
```

Report any endpoints that lack authorization:

```
Unprotected endpoints detected:
  HIGH: GET /api/users/:id — no authorization middleware (src/routes/users.ts:23)
    Risk: Any authenticated user can access any user's data (IDOR)
    Remediation: Add ownership check or role-based authorization

  MEDIUM: PUT /api/settings — requires authentication but no role check (src/routes/settings.ts:45)
    Risk: Any authenticated user can modify application settings
    Remediation: Restrict to admin role
```

---

## Step 6: Input Validation Review

Review how the application handles external input.

### Checks

- **API request bodies:** Are they validated against a schema (Joi, Zod, FluentValidation, Pydantic)?
- **Query parameters:** Are they validated for type, length, and allowed values?
- **Path parameters:** Are they validated (e.g., UUID format, numeric ID)?
- **File uploads:** Are they validated by content type (magic bytes), size limits, and filename?
- **Headers:** Are custom headers validated before use?

### Common Vulnerabilities

- Request bodies accepted without any validation.
- String fields without maximum length (potential denial of service).
- Numeric fields without range validation.
- Array fields without maximum size.
- Nested objects without depth limits.
- File uploads without size or type restrictions.

```bash
# Find validation patterns
grep -rn "validate\|schema\|Joi\|zod\|yup\|class-validator\|FluentValidation\|Pydantic" src/
# Find request handling without visible validation
grep -rn "req\.body\|req\.query\|req\.params\|request\.json\|Request\.Form" src/
```

Report unvalidated inputs:

```
Input validation gaps:
  HIGH: POST /api/users — request body not validated (src/routes/users.ts:34)
    Risk: Arbitrary data can be passed to the database layer
    Remediation: Add Zod schema validation matching the User type

  MEDIUM: GET /api/search?q= — query parameter 'q' has no max length (src/routes/search.ts:12)
    Risk: Extremely long query strings may cause performance issues
    Remediation: Limit 'q' to 500 characters
```

---

## Step 7: Produce Security Report

Compile all findings into a structured security report.

### Report Format

```
## Security Report — <project-name> — <date>

### Executive Summary

Risk Level: [LOW / MEDIUM / HIGH / CRITICAL]
Audit Depth: [Quick / Standard / Deep]
Findings: X critical, Y high, Z medium, W low

### Scan Results (automated)

| Tool | Status | Findings |
|------|--------|----------|
| gitleaks | PASS/FAIL | N secrets |
| npm audit | PASS/FAIL | N vulnerabilities |
| semgrep | PASS/FAIL | N issues |

### Findings (by severity)

CRITICAL FINDINGS
─────────────────

| # | Category | Location | Finding | Remediation |
|---|----------|----------|---------|-------------|
| 1 | Secrets | src/config/aws.ts:12 | AWS Access Key hardcoded in source file | Remove from source. Use environment variable. Rotate key immediately. |

HIGH FINDINGS
─────────────

| # | Category | Location | Finding | Remediation |
|---|----------|----------|---------|-------------|
| 2 | Injection | src/db/queries.ts:45 | SQL query built with string concatenation | Use parameterized query with $1, $2 placeholders |
| 3 | Access Control | src/routes/users.ts:23 | GET /api/users/:id has no authorization check | Add ownership validation middleware |
| 4 | Dependencies | package.json | jsonwebtoken@8.5.1 has CVE-2022-23529 | Update to jsonwebtoken@9.0.0 |

MEDIUM FINDINGS
───────────────

| # | Category | Location | Finding | Remediation |
|---|----------|----------|---------|-------------|
| 5 | Configuration | src/app.ts | No Content-Security-Policy header set | Add helmet with strict CSP configuration |
| ... | ... | ... | ... | ... |

LOW FINDINGS
────────────

| # | Category | Location | Finding | Remediation |
|---|----------|----------|---------|-------------|
| 10 | Logging | src/auth/login.ts:56 | Failed login attempts not logged | Add structured logging for auth failures |
| ... | ... | ... | ... | ... |

POSITIVE OBSERVATIONS
─────────────────────
  - Password hashing uses bcrypt with appropriate cost factor (12)
  - All API endpoints use HTTPS
  - .env files are in .gitignore
  - Input validation present on 80% of endpoints (Zod schemas)

RECOMMENDATIONS (Priority Order)
─────────────────────────────────
  1. IMMEDIATE: Rotate the exposed AWS access key and remove from source
  2. BEFORE NEXT RELEASE: Fix SQL injection in queries.ts
  3. BEFORE NEXT RELEASE: Add authorization to unprotected endpoints
  4. BEFORE NEXT RELEASE: Update vulnerable dependencies
  5. SHORT-TERM: Implement security headers via helmet
  6. SHORT-TERM: Add validation to remaining 20% of endpoints
  7. ONGOING: Implement security event logging
```

### Severity Definitions

| Severity     | Definition                                                                                | Response Time          |
| ------------ | ----------------------------------------------------------------------------------------- | ---------------------- |
| **CRITICAL** | Actively exploitable vulnerability, exposed credentials, or data breach risk              | Immediate (same day)   |
| **HIGH**     | Exploitable vulnerability requiring specific conditions, or significant security weakness | Within current sprint  |
| **MEDIUM**   | Security weakness that reduces defense-in-depth, or misconfiguration                      | Within next 2 sprints  |
| **LOW**      | Best practice violation, minor weakness, or defense-in-depth improvement                  | Backlog / next quarter |

---

## Error Recovery

| Failure                              | Action                                                                                        |
| ------------------------------------ | --------------------------------------------------------------------------------------------- |
| Security tool not installed          | Report which tools are missing. Run manual checks. Note reduced coverage.                     |
| Cannot access git history            | Skip history-based secrets scan. Note limitation. Scan current files only.                    |
| Dependency audit tool unavailable    | Attempt manual review of lock file. Note reduced coverage.                                    |
| Codebase too large for manual review | Focus on high-risk areas: auth, database, API handlers, configuration. Note scope limitation. |
| Cannot determine stack               | Run language-agnostic checks only (secrets, general patterns). Note limitation.               |

---

## Learning Capture (on completion)

If during the audit you discovered recurring security issues:

1. **Recurring finding** (e.g., same type of vulnerability across multiple files) → Propose adding to `knowledge/anti-patterns.md`
2. **Security pattern** (e.g., project's established way of handling auth) → Propose adding to `knowledge/patterns.md`
3. **Lesson learned** (e.g., dependency that introduces unexpected risk) → Propose adding to `knowledge/learnings.md`

This creates **Security Memory** — future audits can skip known false positives and focus on new risks.

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not fix vulnerabilities. It reports findings and provides remediation guidance.
- It does not perform penetration testing. It is a static analysis and configuration review.
- It does not scan infrastructure (servers, networks, cloud configurations). It focuses on application code.
- It does not replace professional security audits. It is a first-pass automated review to catch common issues.
- It does not guarantee security. Passing this audit means common vulnerabilities were not found — it does not mean the application is secure.
