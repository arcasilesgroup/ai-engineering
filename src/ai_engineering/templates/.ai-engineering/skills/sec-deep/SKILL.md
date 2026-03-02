---
name: sec-deep
description: "Run specialized security assessments: DAST (ZAP/Nuclei), container scanning (Trivy), or data security posture review."
version: 1.0.0
tags: [security, dast, container, data, owasp-zap, nuclei, trivy]
metadata:
  ai-engineering:
    scope: read-only
    token_estimate: 1100
---

# Specialized Security

## Purpose

Targeted security assessments beyond static analysis: dynamic application testing, container image scanning, and data security posture review. Each mode addresses a distinct security domain with specialized tooling.

## Trigger

- Command: `/review:specialized-security dast|container|data` or agent selects appropriate mode.
- Context: post-deploy verification, container promotion, data handling changes, periodic audits.

## When NOT to Use

- **Static code security** — use `sec-review` instead.
- **General quality gate** — use `audit` instead.
- **Dependency vulnerabilities only** — use `pip-audit`/`npm-audit` directly.

## Mode: DAST

Dynamic Application Security Testing against live staging environments using OWASP ZAP and Nuclei.

**Requires**: `zap-cli`, `nuclei` (optional tooling in manifest).

### Procedure

1. **Verify target** — confirm staging/test environment (never production without explicit approval). Record URL and environment.
2. **ZAP baseline scan** — `zap-cli quick-scan` or `zap-baseline.py`. Collect alerts by risk level.
3. **Nuclei scan** — `nuclei -u <url> -t cves/ -t vulnerabilities/ -t misconfiguration/ -severity critical,high,medium`.
4. **Security headers** — validate `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`. Flag missing.
5. **TLS check** — minimum TLS 1.2, no weak ciphers, valid certificate chain.
6. **Report** — severity-tagged findings with OWASP Top 10 mapping, remediation per finding.

### Output

DAST findings report. Verdict: PASS (no critical/high) / FAIL. Security headers matrix. Tool evidence.

## Mode: Container

Container image scanning using Trivy for CVEs, misconfigurations, and secrets.

**Requires**: `trivy` (optional tooling in manifest).

### Procedure

1. **Identify image** — accept name:tag, digest, or local image.
2. **Vulnerability scan** — `trivy image --severity CRITICAL,HIGH,MEDIUM <image>`. Collect CVEs with fixed versions.
3. **Misconfiguration scan** — `trivy config --severity CRITICAL,HIGH,MEDIUM .` on Dockerfile. Check: root user, privileges, exposed ports, health checks.
4. **Secret scan** — `trivy image --scanners secret <image>`. Flag embedded credentials.
5. **Base image review** — identify base image version. Flag EOL or outdated. Recommend pinned digests.
6. **Report** — severity-tagged findings with upgrade paths and Dockerfile fixes.

### Output

Container security report. Verdict: PASS/FAIL. Base image assessment. Remediation plan.

## Mode: Data

Data security posture review for confidentiality and integrity controls.

### Procedure

1. **Classify** — identify data types and sensitivity levels in scope.
2. **Encryption** — verify at-rest and in-transit encryption controls.
3. **Access control** — evaluate authentication/authorization boundaries.
4. **Retention** — check retention, deletion, and auditability requirements.
5. **Report** — exposure risks with severity and remediation priorities.

### Output

Data security findings with severity and remediation plan.

## Governance Notes

- Specialized security runs on-demand or in CI/CD — not a gate hook.
- Critical/high findings are hard blockers for release/promotion.
- Findings cannot be dismissed without `state/decision-store.json` risk acceptance.
- DAST tools and Trivy are optional — listed in manifest under `tooling.optional`.
- DAST target must be staging/test unless explicitly authorized for production.
- Base images should be reviewed for EOL status quarterly.

## References

- `skills/sec-review/SKILL.md` — general security assessment.
- `agents/review.md` — agent that orchestrates security reviews.
- `standards/framework/core.md` — enforcement and risk acceptance rules.
