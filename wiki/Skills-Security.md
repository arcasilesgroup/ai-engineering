# Security Skills

> Skills for security auditing, blast radius analysis, and vulnerability management.

## /assess

**Unified risk assessment: security audit and/or blast radius analysis.**

The `/assess` skill consolidates security auditing and impact analysis into a single workflow with two modes.

```
/assess                    # Run both security audit and blast radius
/assess security           # OWASP Top 10 security review only
/assess impact             # Blast radius / impact analysis only
/assess security src/controllers/
```

---

### /assess security

**OWASP Top 10 security review.**

#### What It Checks

The security audit reviews code against OWASP Top 10:

| # | Vulnerability | What's Checked |
|---|--------------|----------------|
| 1 | Injection | SQL, command, LDAP injection |
| 2 | Broken Auth | Weak passwords, session issues |
| 3 | Sensitive Data | Encryption, data exposure |
| 4 | XXE | XML external entity processing |
| 5 | Broken Access | Missing authorization checks |
| 6 | Misconfig | Default credentials, debug mode |
| 7 | XSS | Cross-site scripting |
| 8 | Deserialization | Unsafe deserialization |
| 9 | Components | Known vulnerable dependencies |
| 10 | Logging | Insufficient logging/monitoring |

#### Audit Process

1. **Scan codebase** — Identify security-relevant code
2. **Check patterns** — Look for known vulnerability patterns
3. **Analyze dependencies** — Check for vulnerable packages
4. **Check secrets** — Scan for hardcoded credentials
5. **Report** — Findings by severity

#### Example Output

```markdown
## Security Audit Report

**Overall Risk:** MEDIUM

### Critical (must fix immediately)
- [ ] `src/controllers/AuthController.cs:45`
  SQL injection: User input concatenated into query
  ```csharp
  // VULNERABLE
  var query = $"SELECT * FROM Users WHERE Email = '{email}'";
  ```

### High (fix before release)
- [ ] `src/services/TokenService.cs:78`
  Weak token: Using predictable GUID for password reset

### Medium (fix in next sprint)
- [ ] `src/config/appsettings.json`
  Debug mode enabled in production config

### Low (consider fixing)
- [ ] `src/controllers/UserController.cs:123`
  Missing rate limiting on login endpoint

### Dependency Vulnerabilities
| Package | Version | CVE | Severity |
|---------|---------|-----|----------|
| Newtonsoft.Json | 12.0.1 | CVE-2024-1234 | High |
```

---

### /assess impact

**Analyze the blast radius of proposed changes.**

```
/assess impact
/assess impact src/services/UserService.cs
```

#### What It Analyzes

1. **Direct dependencies** — What uses this code?
2. **Indirect dependencies** — What uses the things that use this code?
3. **Test coverage** — What tests cover this code?
4. **API surface** — Does this change the public API?
5. **Database** — Does this affect data models?

#### Example Output

```markdown
## Blast Radius: UserService.cs

### Direct Dependencies (5 files)
- `UserController.cs` — calls GetUser, CreateUser
- `AuthService.cs` — calls ValidateUser
- `OrderService.cs` — calls GetUser
- `NotificationService.cs` — calls GetUserEmail
- `ReportService.cs` — calls GetUserStats

### Indirect Dependencies (12 files)
- All controllers that use OrderService
- Background jobs that use NotificationService

### Test Coverage
- `UserServiceTests.cs` — 94% coverage
- `UserControllerTests.cs` — 87% coverage
- `AuthServiceTests.cs` — 91% coverage

### Risk Assessment
- **API Change:** No (internal only)
- **Database Change:** No
- **Breaking Change:** No

**Recommendation:** Safe to proceed. Run full test suite after changes.
```

---

## Quality Gates

Quality gate checks (build, tests, lint, security, secrets, dependencies, duplication) are handled by the **[verify-app agent](Agents-verify-app)** rather than a standalone skill. For quality gate thresholds, see [Standards - Quality Gates](Standards-Quality-Gates).

---

## Secret Scanning

**Prevent secrets from being committed.**

### How It Works

1. **gitleaks** scans staged files before commit
2. Looks for patterns: API keys, tokens, passwords, connection strings
3. Blocks commit if secrets found

### Patterns Detected

| Pattern | Example |
|---------|---------|
| AWS Keys | `AKIA...` |
| GitHub Tokens | `ghp_...`, `github_pat_...` |
| OpenAI Keys | `sk-...` |
| Slack Tokens | `xox...` |
| Private Keys | `-----BEGIN RSA PRIVATE KEY-----` |
| Connection Strings | `Server=...;Password=...` |
| Generic Secrets | `password=`, `secret=`, `api_key=` |

### Configuration

gitleaks uses `.gitleaks.toml` for configuration:

```toml
[allowlist]
paths = [
  '''tests/fixtures/''',
  '''docs/examples/'''
]

[[rules]]
description = "Generic API Key"
regex = '''(?i)(api[_]?key|apikey)(.{0,20})?['\"]([0-9a-zA-Z]{32,64})['\"]'''
```

### Bypassing (Emergency Only)

If you need to commit something that looks like a secret but isn't:

```bash
# Add to allowlist in .gitleaks.toml
# OR use inline comment
# gitleaks:allow

# NOT RECOMMENDED: skip entirely
git commit --no-verify
```

---

## Dependency Scanning

**Check for vulnerable dependencies.**

### Commands by Stack

| Stack | Command | Checks |
|-------|---------|--------|
| .NET | `dotnet list package --vulnerable` | NuGet packages |
| Node | `npm audit` | npm packages |
| Python | `pip audit` | PyPI packages |

### Pre-Push Hook

The framework includes a pre-push hook that:

1. Runs on `git push`
2. Checks dependencies for vulnerabilities
3. **CRITICAL** → Blocks push
4. **HIGH** → Warns but allows

### Example Output

```
Checking npm dependencies...

found 2 vulnerabilities (1 high, 1 critical)

CRITICAL: lodash < 4.17.21
  Prototype Pollution
  Fix: npm update lodash

HIGH: axios < 1.6.0
  SSRF vulnerability
  Fix: npm update axios

Push blocked. Fix critical vulnerabilities first.
```

---
**See also:** [Quality Gates](Standards-Quality-Gates) | [Code Quality Skills](Skills-Code-Quality) | [verify-app Agent](Agents-verify-app)
