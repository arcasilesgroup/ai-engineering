# TypeScript — Security Floor

Minimum bar for `ai-build` output in TypeScript. Every control below
is mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input (HTTP, message bus, env) is parsed through a
  schema validator: `zod`, `valibot`, or `effect/schema`.
- Validation lives at the trust boundary; downstream code receives
  the validated type, never `unknown`.
- Reject with structured errors (HTTP 400 / typed Result), never
  silently coerce.

## Confidential configuration

- `process.env` reads go through one typed loader (e.g. `env.ts`)
  that validates required keys at boot.
- Never log raw confidential values, even at debug level. Redact
  before logging.
- Dotenv files are git-ignored; commit a placeholder example file
  with stub values only.
- Use platform vaults (CI provider, hosting provider, cloud KMS) —
  never hard-code.

## Dependencies

- `npm audit --audit-level=high` (or `pnpm audit`, `bun audit`) in CI.
- Renovate / Dependabot configured to track CVEs.
- Pin transitive critical packages via `resolutions` / `overrides`
  when a fix is unreleased upstream.
- Forbid known-malicious or sanction-listed packages in repo policy.

## OWASP top hits (web)

- **Injection**: parameterised queries (`pg`, `drizzle`, `prisma`),
  never string-built SQL. Server actions/RPC validate every input.
- **Broken access control**: authorisation check beside every query,
  not just at the route. Default-deny.
- **XSS**: never `dangerouslySetInnerHTML` user content. React escapes
  by default — keep it that way.
- **CSRF**: SameSite cookies + per-form tokens for state-changing
  routes that aren't already idempotent JSON APIs.
- **SSRF**: outbound HTTP allowlist when fetching user-supplied URLs.

## Cryptography

- Never roll your own. Use `crypto.subtle` (web) or `node:crypto`.
- Hash login material with argon2id or bcrypt at strong cost (≥12).
- Use AES-GCM for symmetric, Ed25519 / X25519 for signing / KX.
- Random IDs: `crypto.randomUUID()` only when collision-resistance is
  the requirement; for unguessable tokens use `crypto.randomBytes(32)`.

## TLS

- HTTPS-only outbound; do not disable TLS verification in any
  environment, even dev.
- HSTS in production responses.

## Static analysis

- `eslint-plugin-security` and the typescript-eslint security rules
  enabled.
- `gitleaks` or `trufflehog` on every PR.
- CodeQL / Semgrep optional but recommended for non-trivial repos.
