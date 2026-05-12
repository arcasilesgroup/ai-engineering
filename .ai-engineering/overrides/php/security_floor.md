<!-- source: php security v1 (spec-133 D-133-12) -->

# Php — Security Floor

Minimum security posture for the `ai-security` reviewer when scanning php code.

## Common vulnerabilities

SQLi via PDO bypass, XSS via unescaped output, file upload validation, eval/include hazards

## Required gates

- Dependency audit on every commit (stack-canonical command).
- SAST scan via the framework's `semgrep --config .semgrep.yml`.
- Secrets scan via `gitleaks protect --staged` (canonical hot-path).
