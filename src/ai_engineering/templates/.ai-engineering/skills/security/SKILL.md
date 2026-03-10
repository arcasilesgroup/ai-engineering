---
name: security
description: "Unified security scanning: SAST, DAST, dependency audit, SBOM generation. Modes: static | dynamic | deps | sbom."
metadata:
  version: 2.0.0
  tags: [security, sast, dast, dependencies, sbom, owasp]
  ai-engineering:
    requires:
      bins: [gitleaks, semgrep]
    scope: read-write
    token_estimate: 1200
---

# Security

## Purpose

Unified security assessment covering static analysis (SAST), dynamic analysis (DAST), dependency auditing, and SBOM generation. Consolidates sec-review, sec-deep, sbom, and deps into modes.

## Trigger

- Command: `/ai:scan security` or `/ai:security [static|dynamic|deps|sbom]`
- Context: security review, pre-release security gate, dependency audit.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"security"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Modes

### static — SAST review
OWASP Top 10 2025 analysis, secret detection, injection patterns, auth issues.
Tools: `semgrep`, `gitleaks`, manual code analysis.
Optional: `snyk code test` (requires `SNYK_TOKEN`, CI-only).

### dynamic — DAST review
Runtime security testing, container scanning, cloud configuration.
Tools: `zap-cli`, `nuclei`, `trivy`.

### deps — Dependency audit
Vulnerability scanning of all dependencies across stacks.
Tools: `pip-audit`, `npm audit`, `dotnet list package --vulnerable`, `cargo audit`.
Optional: `snyk test` (requires `SNYK_TOKEN`, CI-only).

### sbom — Software Bill of Materials
Generate CycloneDX SBOM for all project dependencies.
Tools: `cyclonedx-py`, `cdxgen`.

## Procedure

1. **Detect stacks** -- read install-manifest for active stacks.
2. **Run tools** -- execute stack-appropriate security tools.
3. **Analyze findings** -- classify by OWASP category and severity.
4. **Prioritize** -- order by exploitability and business impact.
5. **Report** -- uniform scan output contract with score 0-100.

## Output

Follows uniform scan output contract (see scan agent).
