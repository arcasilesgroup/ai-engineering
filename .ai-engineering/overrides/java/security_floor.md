<!-- source: java security v1 (spec-133 D-133-12) -->

# Java — Security Floor

Minimum security posture for the `ai-security` reviewer when scanning java code.

## Common vulnerabilities

Log4Shell (CVE-2021-44228), deserialization (jackson polymorphic), XXE, SQLi via JDBC

## Required gates

- Dependency audit on every commit (stack-canonical command).
- SAST scan via the framework's `semgrep --config .semgrep.yml`.
- Secrets scan via `gitleaks protect --staged` (canonical hot-path).
