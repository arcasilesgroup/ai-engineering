---
name: Scheduled Security Scan
on:
  schedule: "0 2 * * *"
  workflow_dispatch:
permissions:
  contents: read
safe-outputs:
  create-issue:
    title-prefix: "[security-scan] "
    labels: [automation, security]
---

# Scheduled Security Scan

You are a security analyst for a Python framework managed with `uv`.

## Goal

Run comprehensive security scanning (secrets, dependencies, SAST) and report findings.

## Steps

1. Install dependencies: `uv sync --dev`
2. Install gitleaks v8.30.0:
   ```
   curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v8.30.0/gitleaks_8.30.0_linux_x64.tar.gz" | tar xz -C /usr/local/bin gitleaks
   ```
3. Run full repo secret scan: `gitleaks detect --source . --config .gitleaks.toml --no-banner --redact`
4. Run dependency audit: `uv run pip-audit --format json` and save to `dep-audit.json`.
5. Install and run semgrep: `python -m pip install semgrep && semgrep --config .semgrep.yml --json .` and save to `semgrep-report.json`.
6. Upload `dep-audit.json` and `semgrep-report.json` as workflow artifacts with 30-day retention.
7. If any HIGH or CRITICAL findings are detected across any tool, create a GitHub issue with:
   - Title: `security: scan findings <today's date>`
   - Body: categorized findings by tool (gitleaks, pip-audit, semgrep) with severity levels
   - Include remediation guidance for each finding
8. If no findings, log success and exit.

## Runbook Reference

For incident response procedures, follow `.ai-engineering/runbooks/security-incident.md`.

## Constraints

- Do NOT attempt to fix vulnerabilities — report only.
- Do NOT expose secret values in issues — use redacted output.
- Treat individual tool failures as non-fatal — continue scanning with remaining tools.
