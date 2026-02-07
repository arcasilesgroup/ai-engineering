# Universal Security Standards

These security standards apply to every technology stack and every environment. Security is not optional and is not a phase — it is a property of every line of code. When generating or modifying code, treat every rule in this document as a hard constraint unless a stack-specific override explicitly says otherwise.

---

## OWASP Top 10 Awareness

Every engineer and AI assistant must be familiar with the OWASP Top 10 and actively guard against these vulnerability classes:

1. **Broken Access Control** — Enforce authorization on every request. Never rely on client-side checks alone.
2. **Cryptographic Failures** — Use strong, current algorithms. Never roll your own crypto.
3. **Injection** — Parameterize all queries. Never concatenate user input into commands, queries, or templates.
4. **Insecure Design** — Threat model before building. Security cannot be bolted on after the fact.
5. **Security Misconfiguration** — Use secure defaults. Disable debug modes, default credentials, and unnecessary features in production.
6. **Vulnerable and Outdated Components** — Audit dependencies. Patch known vulnerabilities promptly.
7. **Identification and Authentication Failures** — Use proven libraries for auth. Enforce strong passwords, MFA, and session management.
8. **Software and Data Integrity Failures** — Verify the integrity of code, updates, and CI/CD pipelines. Sign artifacts.
9. **Security Logging and Monitoring Failures** — Log security-relevant events. Alert on anomalies. Retain logs for incident response.
10. **Server-Side Request Forgery (SSRF)** — Validate and restrict outbound requests. Never let user input control destination URLs without allowlisting.

When writing code that touches any of these areas, add a brief comment referencing the relevant OWASP category so reviewers can verify the mitigation.

---

## Input Validation and Sanitization

### Rules

- **Validate all input at the system boundary.** Every value that enters the system from an external source (HTTP request, file upload, message queue, CLI argument, environment variable) must be validated before use.
- **Use allowlists, not denylists.** Define what is permitted, not what is forbidden. Denylists are always incomplete.
- **Validate type, length, format, and range.** A "valid email" check is not sufficient — also enforce maximum length, reject null bytes, and check encoding.
- **Sanitize output, not just input.** Context-appropriate encoding must be applied at the point of output (HTML encoding for HTML, URL encoding for URLs, parameterization for SQL).
- **Reject invalid input immediately.** Do not attempt to "fix" malformed input by stripping characters or guessing intent. Return a clear error.

### Patterns

```
// DON'T — concatenating user input into a query
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// DO — parameterized query
const query = `SELECT * FROM users WHERE id = $1`;
const result = await db.query(query, [userId]);
```

```
// DON'T — rendering user input as raw HTML
element.innerHTML = userComment;

// DO — use text content or a sanitization library
element.textContent = userComment;
```

- Never trust `Content-Type` headers. Validate actual content regardless of declared type.
- File uploads must be validated by content (magic bytes), not just by extension. Restrict allowed MIME types. Store uploads outside the web root.
- Limit request body sizes. Enforce maximum lengths on all string fields. Set timeouts on all I/O operations.

### Injection Prevention by Type

| Injection Type | Mitigation |
|---|---|
| SQL injection | Parameterized queries or prepared statements. Never string concatenation. |
| NoSQL injection | Use typed query builders. Reject `$`-prefixed keys from user input in MongoDB. |
| Command injection | Avoid shell execution. Use language APIs that accept argument arrays, not shell strings. |
| LDAP injection | Escape special characters using framework-provided functions. |
| Template injection | Use sandboxed template engines. Never pass user input as template source. |
| Header injection | Reject newline characters (`\r`, `\n`) in header values. |
| Path traversal | Resolve paths and verify they remain within the expected base directory. Reject `..` sequences. |

```
// DON'T — command injection risk
const output = exec(`convert ${userFilename} output.png`);

// DO — argument array prevents injection
const output = execFile('convert', [userFilename, 'output.png']);
```

---

## Authentication and Authorization

### Authentication

- Never implement custom authentication from scratch. Use established libraries and protocols (OAuth 2.0, OpenID Connect, SAML).
- Passwords must be hashed with a modern adaptive algorithm: **bcrypt**, **scrypt**, or **Argon2id**. Never use MD5, SHA-1, or SHA-256 alone for password hashing.
- Enforce minimum password length of 12 characters. Do not impose arbitrary complexity rules (e.g., "must contain special character") — they reduce security by encouraging patterns.
- Implement account lockout or progressive delays after repeated failed login attempts.
- Session tokens must be cryptographically random, at least 128 bits of entropy, transmitted only over HTTPS, and stored in `HttpOnly`, `Secure`, `SameSite=Strict` cookies.
- Implement session expiration and idle timeout. Invalidate sessions server-side on logout.
- Support and encourage multi-factor authentication (MFA) for all user-facing applications.

### Authorization

- Enforce authorization on **every** server-side request handler. Never rely on the UI hiding elements as a security control.
- Use role-based access control (RBAC) or attribute-based access control (ABAC) with clearly defined roles and permissions.
- Apply the principle of least privilege: grant the minimum permissions required for each role.
- Check authorization against the resource being accessed, not just the action. A user authorized to edit *their* profile is not authorized to edit *all* profiles.
- Log authorization failures. Multiple failures from the same source may indicate an attack.
- Implement rate limiting on all public endpoints. Use stricter limits on authentication endpoints (login, password reset, MFA verification).
- Use time-constant comparison for tokens and secrets to prevent timing attacks.

### API Security

- Authenticate every API request. Use bearer tokens (JWT or opaque tokens), API keys (for server-to-server), or session cookies (for browser clients).
- Validate JWT tokens on every request: check signature, issuer, audience, expiration, and required claims. Do not skip validation for "internal" endpoints.
- API keys must be treated as secrets — never embed in client-side code, URLs, or logs.
- Implement request throttling and abuse detection. Return `429 Too Many Requests` with `Retry-After` headers.
- For webhooks, verify the request signature using a shared secret and HMAC. Reject unsigned or expired webhook payloads.

```
// DON'T — only checking if the user is logged in
if (currentUser) {
  deleteProject(projectId);
}

// DO — verifying the user has permission on this specific resource
if (currentUser && currentUser.canDelete(project)) {
  deleteProject(projectId);
}
```

---

## Secrets Management

### Hard Rules

- **Never hardcode secrets.** No API keys, passwords, tokens, certificates, or connection strings in source code. Not in constants, not in comments, not in "temporary" test files. Never.
- **Never commit secrets to version control.** If a secret is accidentally committed, rotate it immediately. Removing it from history is not sufficient — assume it is compromised.
- **Never log secrets.** Not at any log level. Not in error messages. Not in debug output.
- **Never transmit secrets in URL query parameters.** URLs are logged by proxies, browsers, and servers.

### Storage and Access

- Store secrets in a dedicated secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, Azure Key Vault, 1Password, Doppler).
- For local development, use `.env` files that are listed in `.gitignore`. Never commit `.env` files.
- Rotate secrets on a regular schedule and immediately after any suspected compromise.
- Limit secret access to the minimum set of services and personnel that require them.
- Use short-lived credentials (temporary tokens, rotating keys) wherever possible.

### Environment Variables

- Use environment variables to inject configuration and secrets at runtime.
- Validate that required environment variables are present at application startup. Fail fast with a clear error if any are missing.
- Do not use environment variables for complex structured configuration. Use configuration files (with secrets injected separately) for that purpose.

```
# DON'T
DATABASE_URL = "postgres://admin:supersecretpassword@prod-db.internal:5432/app"

# DO
DATABASE_URL = "${DB_PROTOCOL}://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
# With each component injected from the secrets manager at deploy time
```

---

## Dependency Security

- Run automated vulnerability scanning on every CI build. Use tools like `npm audit`, `pip-audit`, `cargo audit`, `trivy`, or Snyk.
- Do not ignore or suppress vulnerability warnings without documenting the justification and setting a remediation deadline.
- Keep dependencies up to date. Automate update PRs with Dependabot or Renovate and review them promptly.
- Use lock files (`package-lock.json`, `Pipfile.lock`, `Cargo.lock`, `go.sum`) in every project. Commit them to version control.
- Verify package integrity. Use checksums, signatures, or `--integrity` flags where available.
- Audit transitive dependencies, not just direct ones. A vulnerability three levels deep is still a vulnerability.
- Prefer dependencies from well-known maintainers and organizations. Scrutinize packages with very few downloads, recent namespace transfers, or suspiciously similar names to popular packages (typosquatting).
- Remove unused dependencies. Every dependency is attack surface.

---

## Data Protection

### Personally Identifiable Information (PII)

- Identify and classify all PII your system handles: names, emails, phone numbers, addresses, government IDs, financial data, health data, biometric data, IP addresses, device identifiers.
- Minimize PII collection. Do not collect data you do not need. If you no longer need it, delete it.
- Encrypt PII at rest using AES-256 or equivalent. Use full-disk encryption for databases and storage volumes.
- Encrypt PII in transit using TLS 1.2 or higher. Never transmit PII over unencrypted channels.
- Mask or redact PII in logs, error reports, and monitoring dashboards.
- Implement data retention policies and automated deletion. Comply with applicable regulations (GDPR, CCPA, HIPAA).

### Encryption

- Use TLS 1.2+ for all network communication. Disable TLS 1.0 and 1.1.
- Use AES-256-GCM for symmetric encryption. Use RSA-2048+ or ECDSA P-256+ for asymmetric encryption.
- Never implement your own cryptographic algorithms or protocols. Use vetted libraries (libsodium, OpenSSL, the standard library of your language).
- Store encryption keys separately from the data they encrypt. Use a key management service (KMS).
- Rotate encryption keys periodically and on suspected compromise.

---

## Logging Security

### What to Log

- Authentication events: successful logins, failed logins, logouts, password changes, MFA events.
- Authorization failures: access denied events with the user, resource, and attempted action.
- Input validation failures: rejected requests with sanitized context (no raw user input in logs).
- Administrative actions: configuration changes, user management, permission changes.
- System events: startup, shutdown, errors, dependency failures.

### What NEVER to Log

- Passwords, API keys, tokens, secrets, or credentials — in any form, at any log level.
- Full credit card numbers, Social Security numbers, or government-issued IDs.
- Session tokens or authentication cookies.
- PII beyond what is necessary for the log's purpose. Log user IDs, not full names or emails, unless required for the specific audit event.
- Raw request/response bodies that may contain sensitive data. Sanitize before logging.

### Log Hygiene

- Use structured logging (JSON) with consistent field names across services.
- Include correlation IDs to trace requests across service boundaries.
- Set appropriate log levels: ERROR for failures requiring attention, WARN for degraded conditions, INFO for significant business events, DEBUG for development only.
- Never enable DEBUG logging in production without explicit, time-limited authorization.
- Protect log storage with access controls. Logs often contain enough information to reconstruct sensitive operations.

```
// DON'T
logger.info(`User login: ${email}, password: ${password}, token: ${sessionToken}`);

// DO
logger.info({ event: "user_login", userId: user.id, ip: request.ip, timestamp: Date.now() });
```

---

## Error Messages and Stack Traces

- **Never expose stack traces, internal paths, database schema, or framework versions to end users.** These details help attackers map your system.
- Return generic, user-friendly error messages to clients: "An error occurred. Please try again or contact support."
- Log the full error details (including stack trace) server-side for debugging.
- Use error codes that map to internal documentation. Return `{ "error": "AUTH_003" }` rather than `{ "error": "JWT signature validation failed using RS256 algorithm" }`.
- In API responses, never include the names of internal services, database tables, file paths, or server hostnames.

```
// DON'T — production error response
{
  "error": "QueryFailedError: relation \"users\" does not exist",
  "stack": "at PostgresDriver.query (/app/node_modules/typeorm/...)"
}

// DO — production error response
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred. Please contact support with reference ID: abc-123."
  }
}
```

---

## CORS, CSP, and Security Headers

### CORS (Cross-Origin Resource Sharing)

- Never use `Access-Control-Allow-Origin: *` on endpoints that serve private data or require authentication.
- Allowlist specific origins. Validate the `Origin` header against the allowlist on every request.
- Restrict allowed methods and headers to only those required.
- Set `Access-Control-Max-Age` to cache preflight responses and reduce request overhead.

### CSP (Content Security Policy)

- Define a strict Content Security Policy. Start with `default-src 'self'` and add specific directives only as needed.
- Avoid `unsafe-inline` and `unsafe-eval`. Use nonces or hashes for inline scripts when absolutely necessary.
- Report CSP violations using the `report-uri` or `report-to` directive to catch misconfigurations and attacks.

### Security Headers

Apply the following headers on all HTTP responses:

| Header | Value | Purpose |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | Force HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` or `SAMEORIGIN` | Prevent clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer leakage |
| `Permissions-Policy` | Restrict as needed | Limit browser feature access |
| `Content-Security-Policy` | Strict policy per above | Prevent XSS and injection |
| `X-XSS-Protection` | `0` | Disable legacy XSS filter (CSP replaces it) |

---

## Supply Chain Security

- Verify the integrity of all build tools, CI/CD runners, and deployment pipelines.
- Use signed commits where possible. Require signed commits on protected branches in high-security environments.
- Pin CI/CD action versions to specific commit SHAs, not mutable tags. `uses: actions/checkout@v4` can be hijacked; `uses: actions/checkout@<full-sha>` cannot.
- Review and restrict permissions granted to GitHub Actions, CI runners, and deployment service accounts.
- Use multi-party approval for changes to build pipelines, deployment configurations, and infrastructure-as-code.
- Produce and verify Software Bill of Materials (SBOM) for production artifacts.
- Audit third-party integrations (webhooks, OAuth apps, marketplace plugins) regularly. Revoke unused access.
- Treat CI/CD configuration files (`.github/workflows/*.yml`, `Jenkinsfile`, `.gitlab-ci.yml`) with the same security scrutiny as application code.
- Implement reproducible builds. Given the same source code and dependencies, the build output should be byte-for-byte identical. This makes tampering detectable.
- Use private registries or mirrors for critical dependencies in enterprise environments. Do not rely solely on public registries for production builds.
- Implement dependency lockdown: if a dependency is removed from the public registry (left-pad scenario), your build should still succeed from the lock file and cache.

---

## Security Review Triggers

Certain changes require explicit security review before merging:

- Changes to authentication or authorization logic.
- Changes to cryptographic code, key management, or token handling.
- New external integrations (APIs, webhooks, OAuth providers).
- Changes to input validation or output encoding.
- Infrastructure changes (firewall rules, IAM policies, network configuration).
- Addition of new dependencies that handle security-sensitive operations.
- Changes to CI/CD pipelines or deployment processes.
- Any code that processes PII, financial data, or health data.

Flag these PRs with a `security-review` label and assign a reviewer with security expertise.

---

## Summary Checklist

| Area | Check |
|---|---|
| Input | Is all external input validated with allowlists and parameterized queries? |
| Auth | Is authorization checked on every server-side request? |
| Secrets | Are all secrets in a vault/env, with zero hardcoded values? |
| Dependencies | Are deps scanned, pinned, and up to date? |
| Data | Is PII encrypted at rest and in transit, and minimized? |
| Logging | Are logs free of secrets, tokens, and unnecessary PII? |
| Errors | Do production error responses hide internal details? |
| Headers | Are CORS, CSP, and security headers configured? |
| Supply chain | Are CI/CD pipelines reviewed and action versions pinned? |
