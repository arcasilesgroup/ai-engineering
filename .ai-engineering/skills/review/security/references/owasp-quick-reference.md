# OWASP Quick Reference

On-demand reference for the security review skill. Load selectively by risk category.

## OWASP Top 10 — 2025 Aligned

### A01: Broken Access Control
**What**: Users act outside intended permissions.
**Check for**:
- Missing authorization on endpoints/functions.
- IDOR (Insecure Direct Object References) — user A accesses user B's data by changing an ID.
- Missing RBAC enforcement.
- CORS misconfiguration allowing unauthorized origins.

**Code patterns to flag**:
```python
# BAD: No authorization check
@app.route("/api/users/<user_id>")
def get_user(user_id):
    return db.get_user(user_id)  # Any user can access any user

# GOOD: Authorization enforced
@app.route("/api/users/<user_id>")
@require_auth
def get_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        abort(403)
    return db.get_user(user_id)
```

### A02: Cryptographic Failures
**What**: Weak or missing encryption for sensitive data.
**Check for**:
- Plaintext passwords or secrets in code/config/logs.
- Weak hashing (MD5, SHA1 for passwords).
- Missing TLS for data in transit.
- Hardcoded encryption keys.

### A03: Injection
**What**: Untrusted data sent to interpreter.
**Check for**:
- SQL injection (string concatenation in queries).
- Command injection (user input in `subprocess`, `os.system`).
- Path traversal (`../` in file paths from user input).
- Template injection (user input in Jinja2/Mako templates).

**Code patterns to flag**:
```python
# BAD: SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD: Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# BAD: Command injection
os.system(f"ping {hostname}")

# GOOD: Use subprocess with list args
subprocess.run(["ping", hostname], check=True)
```

### A04: Insecure Design
**What**: Missing or ineffective security controls in design.
**Check for**:
- No rate limiting on authentication endpoints.
- No account lockout after failed attempts.
- Missing input validation at trust boundaries.
- Business logic flaws (negative quantities, price manipulation).

### A05: Security Misconfiguration
**What**: Insecure default configs, open cloud storage, verbose errors.
**Check for**:
- Debug mode enabled in production.
- Default credentials.
- Unnecessary features enabled.
- Missing security headers (CSP, HSTS, X-Frame-Options).
- Verbose error messages exposing internals.

### A06: Vulnerable Components
**What**: Known vulnerabilities in dependencies.
**Check with**:
```bash
pip-audit                    # Python
dotnet list package --vulnerable  # .NET
npm audit                    # Node.js
trivy fs .                   # Universal
```

### A07: Authentication Failures
**What**: Broken authentication mechanisms.
**Check for**:
- Weak password policies.
- Missing MFA on sensitive operations.
- Session fixation or insufficient session invalidation.
- JWT without expiration or with weak signing.

### A08: Data Integrity Failures
**What**: Code and infrastructure without integrity verification.
**Check for**:
- Dependencies from untrusted sources.
- Missing signature verification on updates.
- Insecure deserialization (pickle, yaml.load).

**Code patterns to flag**:
```python
# BAD: Insecure deserialization
import pickle
data = pickle.loads(user_input)  # Remote code execution

# BAD: Unsafe YAML
import yaml
data = yaml.load(user_input)  # Code execution via !!python/object

# GOOD: Safe YAML
data = yaml.safe_load(user_input)
```

### A09: Logging and Monitoring Failures
**What**: Insufficient logging for security events.
**Check for**:
- No logging of authentication successes/failures.
- No logging of authorization failures.
- Sensitive data in logs (passwords, tokens, PII).
- No alerting on suspicious patterns.

### A10: Server-Side Request Forgery (SSRF)
**What**: Server fetches URLs from user input without validation.
**Check for**:
- User-controlled URLs in HTTP requests.
- Missing allowlist for external service calls.
- Internal network access via crafted URLs.

## Severity Classification

| Severity | Criteria | Example |
|----------|----------|---------|
| Critical | Exploitable, no auth required, data exposure | SQL injection on public endpoint |
| High | Exploitable with auth, significant impact | IDOR allowing cross-user data access |
| Medium | Requires specific conditions | XSS in admin-only panel |
| Low | Informational, minimal impact | Missing security header |
