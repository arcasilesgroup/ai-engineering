# DAST (Dynamic Application Security Testing)

## Purpose

Post-deployment dynamic security scanning of running applications using OWASP ZAP and/or Nuclei. Identifies runtime vulnerabilities not detectable by static analysis, including authentication bypass, security header gaps, and active injection vectors.

## Trigger

- Command: agent invokes DAST skill or user requests dynamic security scan.
- Context: post-deploy to staging, pre-release verification, periodic security assessment, incident response.

## Procedure

1. **Verify target** — confirm target URL is a staging/test environment (never production without explicit approval).
   - Check environment label (staging, dev, test).
   - Confirm target is not production unless explicitly authorized.
   - Record target URL and environment in findings.

2. **Run OWASP ZAP baseline scan** — passive + active scanning.
   - Execute: `zap-cli quick-scan --self-contained --start-options '-config api.disablekey=true' <target-url>`.
   - Alternative: `zap-baseline.py -t <target-url> -r zap-report.html`.
   - Collect: alerts by risk level (High/Medium/Low/Informational).

3. **Run Nuclei scan** — template-based vulnerability detection.
   - Execute: `nuclei -u <target-url> -t cves/ -t vulnerabilities/ -t misconfiguration/ -severity critical,high,medium`.
   - Collect: matched templates with severity and evidence.

4. **Check security headers** — validate HTTP response headers.
   - Required headers: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`.
   - Recommended: `Referrer-Policy`, `Permissions-Policy`.
   - Flag missing or misconfigured headers.

5. **Check TLS configuration** — verify encryption setup.
   - Minimum TLS 1.2.
   - No weak cipher suites.
   - Valid certificate chain.

6. **Report findings** — structured DAST assessment.
   - Severity: critical / high / medium / low / info.
   - Each finding: tool, description, evidence, remediation.
   - Cross-reference with OWASP Top 10 2025 mapping.

## Output Contract

- DAST findings report with severity-tagged issues.
- Verdict: PASS (no critical/high) / FAIL (critical/high found).
- Security headers compliance matrix.
- Remediation plan for each finding.
- Tool evidence (ZAP/Nuclei outputs).

## Governance Notes

- DAST is not a gate hook — it runs on-demand or in CI/CD pipelines.
- Target must be staging/test environment unless explicitly authorized for production.
- Critical and high findings are hard blockers for release.
- Findings cannot be dismissed without explicit risk acceptance in `state/decision-store.json`.
- DAST tools (`zap-cli`, `nuclei`) are optional — listed in `manifest.yml` under `tooling.optional.dast`.

## References

- `standards/framework/security/owasp-top10-2025.md` — OWASP mapping.
- `standards/framework/core.md` — mandatory local enforcement and risk acceptance.
- `agents/security-reviewer.md` — agent that orchestrates security reviews.
