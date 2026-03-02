---
name: sec-review
description: "Perform comprehensive security review covering OWASP risks, secrets, injection, and dependency vulnerabilities; use for pre-release audits or incident response."
version: 1.0.0
tags: [security, sast, secrets, owasp, vulnerabilities]
metadata:
  ai-engineering:
    requires:
      bins: [gitleaks, semgrep]
    scope: read-only
    token_estimate: 900
---

# Security Review

## Purpose

Comprehensive security review covering OWASP top risks, secret exposure, injection vulnerabilities, authentication flaws, dependency vulnerabilities, and security headers. Provides actionable findings with severity-tagged remediation.

## Trigger

- Command: agent invokes security-review skill or user requests security audit.
- Context: pre-release review, new feature with external input, dependency update, security incident response.

## When NOT to Use

- **Code quality metrics** (coverage, duplication, complexity) — use `audit` instead.
- **Architecture review** (coupling, dependencies, drift) — use `arch-review` instead.
- **General code review** (style, patterns, correctness) — use `code-review` instead.
- **Governance content validation** — use `integrity` instead.

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

4. **Dependency vulnerabilities** — check supply chain (multi-stack).
   - Detect active stacks from `install-manifest.json`.
   - Python: run `pip-audit` for known CVEs.
   - .NET: run `dotnet list package --vulnerable`.
   - Next.js: run `npm audit`.
   - Run `semgrep` with OWASP ruleset (all stacks).
   - Verify dependencies are from trusted sources.
   - Check for typosquatting risks on package names.
   - For comprehensive supply chain view, reference `skills/sbom/SKILL.md`.

5. **Cloud security** (when applicable) — review cloud resource configuration.
   - IAM: least privilege, no wildcard permissions, service principal rotation.
   - Network: private endpoints, NSG rules, no public-facing databases.
   - Storage: no public blob access, SAS token scope and expiry, encryption at rest.
   - Key Vault / secrets management: managed identities preferred over secrets.
   - Reference `standards/framework/stacks/azure.md` for Azure-specific patterns.

6. **IaC scanning** (when applicable) — scan infrastructure code.
   - Terraform: `tfsec` or `checkov` for misconfigurations.
   - Bicep: `az bicep lint` + manual review of resource configurations.
   - Docker: `trivy config` for Dockerfile best practices.
   - Flag: insecure defaults, missing encryption, overly permissive network rules, hardcoded secrets.

7. **Configuration security** — check runtime settings.
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
- `standards/framework/security/owasp-top10-2025.md` — OWASP Top 10 mapping.
- `agents/review.md` — agent that performs security reviews.
- `skills/sec-deep/SKILL.md` — DAST, container scanning, and data security posture (mode: `dast`, `container`, `data`).
- `skills/sbom/SKILL.md` — software bill of materials generation.
- `standards/framework/stacks/azure.md` — Azure security patterns.
- `standards/framework/stacks/infrastructure.md` — IaC security patterns.
