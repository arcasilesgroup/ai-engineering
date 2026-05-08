<!-- source: _shared overrides v1 -->

# Shared Security Floor — Cross-Stack Minimums

Non-negotiable security controls applied regardless of stack.

## Mandatory

- **Secrets**: never log, never commit, never paste in PR description. Read
  via runtime secret manager only.
- **Supply chain**: all direct deps pinned, transitive scanned via SBOM
  + vulnerability gate before merge.
- **Auth**: default-deny on all endpoints; auth checks at handler edge,
  not deep inside business logic.
- **Crypto**: stdlib / vetted library only — never roll-your-own.
- **TLS**: HTTPS-only outbound; pinned cert validation in production.
- **Static analysis**: stack-specific linter at error level for security
  rules (SonarQube, CodeQL, Snyk, gitleaks/trufflehog on every PR).

## Per-stack overrides

Stack-specific tooling and version pins live in
`.ai-engineering/overrides/<stack>/security_floor.md`.
