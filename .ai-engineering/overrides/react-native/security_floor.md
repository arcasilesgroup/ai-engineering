<!-- source: react-native security v1 (spec-133 D-133-12) -->

# React-Native — Security Floor

Minimum security posture for the `ai-security` reviewer when scanning react-native code.

## Common vulnerabilities

OTA update signing (Expo updates), deep-link allowlists, secure storage (Keychain/EncryptedSharedPreferences), no embedded API secrets

## Required gates

- Dependency audit on every commit (stack-canonical command).
- SAST scan via the framework's `semgrep --config .semgrep.yml`.
- Secrets scan via `gitleaks protect --staged` (canonical hot-path).
