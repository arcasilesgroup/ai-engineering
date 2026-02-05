---
name: assess
description: Analyze security risks (OWASP Top 10) and/or blast radius of code changes
---

## Context

Unified risk assessment: security audit (OWASP Top 10, secrets, dependencies) and/or blast radius analysis (impact tracing, breaking changes). Can run either individually or both in sequence.

## Inputs

$ARGUMENTS - Subcommand and scope:
- `security <files|directory|"full">`: Run security audit only
- `impact <file:method|"staged">`: Run blast radius analysis only
- `<files>` (no subcommand): Run both security and impact analysis

## Steps

### 1. Determine Mode

Parse $ARGUMENTS:
- If starts with `security` → security audit mode
- If starts with `impact` → blast radius mode
- Otherwise → run both in sequence

---

## Security Audit (mode: security or both)

### S1. Gather Context

- Read `standards/security.md` for security requirements.
- Identify the scope: specific files or full project.
- Determine the technology stack(s) in scope.

### S2. Secret Scanning

- Run `gitleaks detect --source . --no-git --verbose` if available.
- Manually scan for patterns: `AKIA`, `sk-`, `ghp_`, `xox`, connection strings, private keys.
- Check for `.env` files, `credentials.*`, `*.pem`, `*.key` in tracked files.
- Verify `.gitignore` excludes sensitive files.

### S3. Dependency Scanning

- .NET: `dotnet list package --vulnerable`
- TypeScript: `npm audit`
- Python: `pip audit`
- Report vulnerabilities with severity and remediation advice.

### S4. OWASP Top 10 Review

For each file in scope, check:

| # | Category | What to Look For |
|---|----------|-----------------|
| A01 | Broken Access Control | Missing authorization checks, IDOR, path traversal |
| A02 | Cryptographic Failures | Weak algorithms, hardcoded keys, missing encryption |
| A03 | Injection | SQL concatenation, command injection, XSS, LDAP injection |
| A04 | Insecure Design | Missing rate limiting, business logic flaws |
| A05 | Security Misconfiguration | Debug mode in prod, default credentials, verbose errors |
| A06 | Vulnerable Components | Outdated dependencies (see S3) |
| A07 | Auth Failures | Weak passwords, missing MFA, session fixation |
| A08 | Data Integrity | Missing input validation, unsafe deserialization |
| A09 | Logging Failures | Missing audit logs, PII in logs, log injection |
| A10 | SSRF | Unvalidated URLs, internal network access |

---

## Blast Radius Analysis (mode: impact or both)

### B1. Identify the Change

- If scope is "staged": analyze `git diff --cached`.
- If file path: read the file and identify the changed/target code.
- Extract: changed methods, interfaces, types, exports.

### B2. Trace Dependencies

For each changed symbol, find all references:

- **Direct callers**: Files that call the changed method/function.
- **Interface implementations**: Classes implementing a changed interface.
- **Type consumers**: Code using changed types/DTOs.
- **Configuration**: Files referencing changed config keys.
- **Tests**: Test files that test the changed code.
- **DI registrations**: Startup/DI files registering changed services.

### B3. Assess Impact

Categorize affected files:
- **Direct impact**: Files that directly use the changed code.
- **Indirect impact**: Files that use code affected by the change.
- **Test impact**: Tests that need updating.
- **No impact**: Files that reference the same names but are unrelated.

---

## Report

    ## Assessment Report

    **Mode:** security | impact | full
    **Scope:** [files/directories assessed]

    ### Security Audit (if applicable)
    **Verdict:** PASS | FAIL

    #### Critical (must fix before deploy)
    - [ ] **[file:line]** [OWASP category] - [Description] → [Fix]

    #### High Priority
    - [ ] **[file:line]** [Description]

    #### Medium Priority
    - [ ] **[file:line]** [Description]

    #### Informational
    - [Observations and recommendations]

    #### Dependencies
    - [Vulnerable packages with versions and fixes]

    ### Blast Radius (if applicable)
    **Changed:** [file:method/class]
    **Total affected files:** X

    #### Direct Impact (must review)
    - [file:line] - [How it's affected]

    #### Indirect Impact (should review)
    - [file:line] - [How it's affected]

    #### Tests Affected
    - [test file] - [Which tests need attention]

    #### Risk Assessment
    - **Breaking change:** Yes/No
    - **Requires migration:** Yes/No
    - **Estimated scope:** Small/Medium/Large

## Verification

- All OWASP Top 10 categories checked (if security mode)
- No secrets in source code
- Dependency vulnerabilities documented
- Each finding has a remediation recommendation
- All direct callers identified (if impact mode)
- Interface implementations tracked
- Test files identified
- No false positives from name-only matches
