# Security Review

## Purpose

Comprehensive security review covering OWASP top risks, secret exposure, injection vulnerabilities, authentication flaws, dependency vulnerabilities, and security headers. Provides actionable findings with severity-tagged remediation.

## Trigger

- Command: agent invokes security-review skill or user requests security audit.
- Context: pre-release review, new feature with external input, dependency update, security incident response.

## Procedure

1. **Secret detection** — scan for exposed credentials.
   - Run `gitleaks detect --no-banner` on repository.
   - Check environment variables, config files, and test fixtures.
   - Verify `.gitignore` excludes sensitive files (`.env`, keys, certs).
   - Check commit history for previously committed secrets.

2. **Injection analysis** — check for injection vectors.
   - SQL injection: parameterized queries, no string concatenation for queries.
   - Command injection: no `os.system()` or `subprocess.run(shell=True)` with user input.
   - Path traversal: validate and sanitize file paths, use `pathlib.Path.resolve()`.
   - Template injection: no user input in template strings without escaping.

3. **Authentication and authorization** — check access controls.
   - API keys and tokens properly scoped and rotated.
   - `gh` CLI authentication verified before operations.
   - No privilege escalation paths in CLI commands.

4. **Dependency vulnerabilities** — check supply chain.
   - Run `pip-audit` for known CVEs.
   - Run `semgrep` with OWASP ruleset.
   - Verify dependencies are from trusted sources.
   - Check for typosquatting risks on package names.

5. **Configuration security** — check runtime settings.
   - No debug mode in production configs.
   - Sensitive defaults are secure (deny by default).
   - Error messages don't expose internals.
   - Logging doesn't capture secrets or PII.

6. **Report findings** — structured security assessment.
   - Severity: critical / high / medium / low / info.
   - Each finding: description, impact, remediation, evidence.
   - CVSS score reference where applicable.

## Output Contract

- Security findings report with severity-tagged issues.
- Verdict: PASS (no critical/high) / FAIL (critical/high found).
- Remediation plan for each finding.
- Evidence of checks executed (tool outputs).

## Governance Notes

- Critical and high findings are hard blockers — merge is prohibited.
- Secret exposure is always critical severity.
- `gitleaks` and `semgrep` are mandatory tools — if missing, auto-remediate before continuing.
- Security findings cannot be dismissed without explicit risk acceptance in `state/decision-store.json`.
- Never provide bypass guidance for security gates.

## References

- `standards/framework/core.md` — mandatory local enforcement and risk acceptance.
- `standards/framework/quality/core.md` — severity policy.
- `agents/security-reviewer.md` — agent that performs security reviews.
