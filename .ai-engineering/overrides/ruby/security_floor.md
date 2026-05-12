<!-- source: ruby security v1 (spec-133 D-133-12) -->

# Ruby — Security Floor

Minimum security posture for the `ai-security` reviewer when scanning ruby code.

## Common vulnerabilities

Rails CSRF protection ON, mass-assignment via strong_params, ERB output escaping, eval/send/instance_variable_set

## Required gates

- Dependency audit on every commit (stack-canonical command).
- SAST scan via the framework's `semgrep --config .semgrep.yml`.
- Secrets scan via `gitleaks protect --staged` (canonical hot-path).
