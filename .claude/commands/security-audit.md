---
description: Run a comprehensive security audit against OWASP Top 10
---

## Context

Performs a thorough security review of specified files or the entire project, checking against OWASP Top 10, secret exposure, dependency vulnerabilities, and project security standards.

## Inputs

$ARGUMENTS - File paths, directory, or "full" for entire project

## Steps

### 1. Gather Context

- Read `standards/security.md` for security requirements.
- Identify the scope: specific files or full project.
- Determine the technology stack(s) in scope.

### 2. Secret Scanning

- Run `gitleaks detect --source . --no-git --verbose` if available.
- Manually scan for patterns: `AKIA`, `sk-`, `ghp_`, `xox`, connection strings, private keys.
- Check for `.env` files, `credentials.*`, `*.pem`, `*.key` in tracked files.
- Verify `.gitignore` excludes sensitive files.

### 3. Dependency Scanning

- .NET: `dotnet list package --vulnerable`
- TypeScript: `npm audit`
- Python: `pip audit`
- Report vulnerabilities with severity and remediation advice.

### 4. OWASP Top 10 Review

For each file in scope, check:

| # | Category | What to Look For |
|---|----------|-----------------|
| A01 | Broken Access Control | Missing authorization checks, IDOR, path traversal |
| A02 | Cryptographic Failures | Weak algorithms, hardcoded keys, missing encryption |
| A03 | Injection | SQL concatenation, command injection, XSS, LDAP injection |
| A04 | Insecure Design | Missing rate limiting, business logic flaws |
| A05 | Security Misconfiguration | Debug mode in prod, default credentials, verbose errors |
| A06 | Vulnerable Components | Outdated dependencies (see Step 3) |
| A07 | Auth Failures | Weak passwords, missing MFA, session fixation |
| A08 | Data Integrity | Missing input validation, unsafe deserialization |
| A09 | Logging Failures | Missing audit logs, PII in logs, log injection |
| A10 | SSRF | Unvalidated URLs, internal network access |

### 5. Report

```markdown
## Security Audit Report

**Scope:** [files/directories audited]
**Verdict:** PASS | FAIL

### Critical (must fix before deploy)
- [ ] **[file:line]** [OWASP category] - [Description] → [Fix]

### High Priority
- [ ] **[file:line]** [Description]

### Medium Priority
- [ ] **[file:line]** [Description]

### Informational
- [Observations and recommendations]

### Dependencies
- [Vulnerable packages with versions and fixes]
```

## Verification

- All OWASP Top 10 categories checked
- No secrets in source code
- Dependency vulnerabilities documented
- Each finding has a remediation recommendation
