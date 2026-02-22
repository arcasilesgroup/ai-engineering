# Container Security

## Purpose

Container image scanning using Trivy for vulnerability detection, misconfiguration analysis, and secret scanning in Docker images. Ensures container deployments meet security baselines before promotion.

## Trigger

- Command: agent invokes container-security skill or user requests container scan.
- Context: container image build, pre-deploy verification, periodic container audit, base image update.

## Procedure

1. **Identify target image** — determine image to scan.
   - Accept image reference (name:tag, digest, or local image).
   - Verify image exists locally or is pullable.

2. **Run vulnerability scan** — detect known CVEs in image layers.
   - Execute: `trivy image --severity CRITICAL,HIGH,MEDIUM <image>`.
   - Collect: CVE IDs, severity, package name, fixed version.
   - Flag unfixed critical/high vulnerabilities.

3. **Run misconfiguration scan** — check Dockerfile best practices.
   - Execute: `trivy config --severity CRITICAL,HIGH,MEDIUM .` (on Dockerfile).
   - Check: running as root, unnecessary privileges, exposed ports, missing health checks.

4. **Run secret scan** — detect embedded secrets in image.
   - Execute: `trivy image --scanners secret <image>`.
   - Flag any detected secrets or credentials in image layers.

5. **Check base image** — verify base image currency.
   - Identify base image and version.
   - Flag end-of-life or significantly outdated base images.
   - Recommend pinned digests over mutable tags.

6. **Report findings** — structured container security assessment.
   - Severity: critical / high / medium / low / info.
   - Each finding: scanner, CVE/rule, package, fixed version, remediation.
   - Total vulnerability count by severity.

## Output Contract

- Container security findings report with severity-tagged issues.
- Verdict: PASS (no critical/high) / FAIL (critical/high found).
- Base image assessment with currency status.
- Remediation plan (upgrade paths, Dockerfile fixes).
- Tool evidence (Trivy outputs).

## Governance Notes

- Container security is not a gate hook — it runs on-demand or in CI/CD pipelines.
- Critical and high findings are hard blockers for container promotion.
- Findings cannot be dismissed without explicit risk acceptance in `state/decision-store.json`.
- Trivy is optional — listed in `manifest.yml` under `tooling.optional.container`.
- Base images should be reviewed for EOL status at minimum quarterly.

## References

- `standards/framework/security/owasp-top10-2025.md` — OWASP mapping (A06 vulnerable components).
- `standards/framework/core.md` — mandatory local enforcement and risk acceptance.
- `agents/security-reviewer.md` — agent that orchestrates security reviews.
