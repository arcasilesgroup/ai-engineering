# OWASP Top 10 2025 Mapping

## Update Metadata

- Rationale: provide explicit mapping from OWASP Top 10 categories to framework controls for multi-stack security coverage.
- Expected gain: systematic security coverage with traceable control-to-risk mapping across all stacks.
- Potential impact: security reviews and audits must reference this mapping; gaps become explicit.

## Purpose

Maps each OWASP Top 10 2025 category to the specific framework controls, tools, and skills that address it. This mapping ensures comprehensive security coverage and makes gaps visible.

## Mapping

### A01: Broken Access Control

- **Controls**: authentication and authorization review in security skill step 3.
- **Tools**: `semgrep` with auth-check rules.
- **Skills**: `skills/review/security.md` (step 3 — authentication and authorization).
- **Stack-specific**: .NET `[Authorize]` attribute validation; Next.js middleware auth checks.

### A02: Cryptographic Failures

- **Controls**: configuration security audit, secret detection.
- **Tools**: `gitleaks` (exposed secrets), `semgrep` (weak crypto patterns).
- **Skills**: `skills/review/security.md` (step 1 — secret detection, step 5 — config security).
- **Stack-specific**: .NET Data Protection API usage; Next.js environment variable isolation.

### A03: Injection

- **Controls**: injection analysis covering SQL, command, path traversal, template injection.
- **Tools**: `semgrep` (injection rules).
- **Skills**: `skills/review/security.md` (step 2 — injection analysis).
- **Stack-specific**: .NET parameterized queries (Entity Framework); Next.js sanitized rendering (React XSS protection).

### A04: Insecure Design

- **Controls**: architecture review, threat modeling.
- **Skills**: `skills/review/architecture.md`, `agents/architect.md`.
- **Notes**: design-level control — requires human judgment and architecture review.

### A05: Security Misconfiguration

- **Controls**: configuration security audit.
- **Tools**: `semgrep` (config rules), stack-specific linters.
- **Skills**: `skills/review/security.md` (step 5 — configuration security).
- **Stack-specific**: .NET `appsettings.json` validation; Next.js `next.config.js` security headers.

### A06: Vulnerable and Outdated Components

- **Controls**: dependency vulnerability scanning per stack.
- **Tools**: `pip-audit` (Python), `dotnet list package --vulnerable` (.NET), `npm audit` (Next.js).
- **Skills**: `skills/review/security.md` (step 4 — dependency vulnerabilities), `skills/dev/deps-update.md`.
- **Notes**: gate-enforced at pre-push for all stacks.

### A07: Identification and Authentication Failures

- **Controls**: authentication flow review, credential management.
- **Tools**: `gitleaks` (exposed credentials), `semgrep` (weak auth patterns).
- **Skills**: `skills/review/security.md` (step 3 — authentication).
- **Stack-specific**: .NET Identity framework review; Next.js NextAuth/Auth.js configuration.

### A08: Software and Data Integrity Failures

- **Controls**: supply chain integrity, remote skill checksums, hook tamper resistance.
- **Tools**: `gitleaks` (data integrity), framework checksum validation.
- **Skills**: `agents/security-reviewer.md` (step 8 — tamper resistance).
- **Notes**: framework enforces `checksums_required` for remote skills, `non_bypassable` for hooks.

### A09: Security Logging and Monitoring Failures

- **Controls**: audit log enforcement, governance event logging.
- **Tools**: `state/audit-log.ndjson` (governance events).
- **Skills**: `skills/govern/accept-risk.md` (audit trail), `skills/govern/resolve-risk.md`.
- **Notes**: all risk decisions logged; governance events are append-only.

### A10: Server-Side Request Forgery (SSRF)

- **Controls**: input validation, network request review.
- **Tools**: `semgrep` (SSRF rules).
- **Skills**: `skills/review/security.md` (step 2 — injection analysis covers SSRF vectors).
- **Stack-specific**: .NET `HttpClient` usage validation; Next.js API route input validation.

## Coverage Summary

| OWASP Category | Gate-Enforced | Skill-Covered | Tool-Automated |
|----------------|:---:|:---:|:---:|
| A01 Broken Access Control | - | Yes | Partial |
| A02 Cryptographic Failures | Yes | Yes | Yes |
| A03 Injection | - | Yes | Yes |
| A04 Insecure Design | - | Yes | - |
| A05 Security Misconfiguration | - | Yes | Partial |
| A06 Vulnerable Components | Yes | Yes | Yes |
| A07 Auth Failures | - | Yes | Partial |
| A08 Integrity Failures | Yes | Yes | Yes |
| A09 Logging Failures | Yes | Yes | - |
| A10 SSRF | - | Yes | Partial |

## References

- `standards/framework/core.md` — mandatory local enforcement.
- `skills/review/security.md` — security review procedure.
- `agents/security-reviewer.md` — security reviewer agent.
- `skills/review/dast.md` — dynamic application security testing.
- `skills/review/container-security.md` — container image scanning.

## Update Contract

This file is framework-managed and may be updated by framework releases.
