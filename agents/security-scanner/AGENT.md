---
name: security-scanner
role: noisy-output-isolator
write_access: false
tools: [Read, Glob, Grep, Bash]
---

# security-scanner

NEW agent (v3). Aggregates SAST + SCA + secret scans with isolated
context to keep the noisy output from contaminating other agents.

## Tools invoked

- `gitleaks protect --staged --no-banner`
- `semgrep --config auto --json`
- `pip-audit` / `npm audit` / Trivy
- `syft` for SBOM, `grype` for vulnerability matching
- OWASP/CWE mapping

## Output

Structured report with stable finding IDs (so risk acceptance can
reference them). Severity normalized to critical/high/medium/low to
match the framework's TTL ladder.

## Why isolated

Security scanners produce 10-100x more output than other tools. Running
them in a separate agent keeps the orchestrator's context clean.
