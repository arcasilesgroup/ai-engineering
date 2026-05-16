<!-- source: flutter security v1 (spec-133 D-133-12) -->

# Flutter — Security Floor

Minimum security posture for the `ai-security` reviewer when scanning flutter code.

## Common vulnerabilities

Deep-link hijacking, secure storage via flutter_secure_storage, certificate pinning for sensitive APIs

## Required gates

- Dependency audit on every commit (stack-canonical command).
- SAST scan via the framework's `semgrep --config .semgrep.yml`.
- Secrets scan via `gitleaks protect --staged` (canonical hot-path).
