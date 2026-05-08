# Rust — Security Floor

Minimum bar for `ai-build` output in Rust. Every control below is
mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input parsed through `serde` derives, never manual
  `Value::as_*()` chains.
- Validate after deserialisation: domain-newtype constructors fail on
  invalid values (`UserId::new(s) -> Result<Self, ParseError>`).
- Reject unknown fields with `#[serde(deny_unknown_fields)]` on every
  request DTO.

## Confidential configuration

- Read environment via `figment`, `config`, or hand-rolled typed
  loader; validate at boot.
- Never log raw confidential values, even at debug. `tracing` with
  `Redacted<T>` newtype for fields that must not leak.
- Dotenv files git-ignored; commit only a stub example file with
  placeholder values.
- Use platform vaults (CI provider, hosting provider, cloud KMS) —
  never hard-code.

## Dependencies

- `cargo audit` in CI on every PR. RustSec advisory database.
- `cargo deny check` for licenses + banned crates + duplicate
  versions.
- `cargo shear` (or `cargo machete`) to flag unused deps — unused
  deps signal design drift.
- Renovate / Dependabot configured to track CVEs.

## OWASP top hits (web)

- **Injection**: parameterised queries via `sqlx` (compile-time
  checked) or `diesel` builder. Never `format!` a SQL query.
- **Broken access control**: authorisation check beside every query,
  not just at the route. Default-deny.
- **XSS**: `askama` / `tera` / `maud` templates auto-escape; never
  emit raw user-supplied strings into HTML.
- **CSRF**: framework middleware (`axum-csrf`, `actix-csrf`) for
  cookie-authenticated routes.
- **SSRF**: outbound HTTP allowlist when fetching user-supplied URLs.

## Cryptography

- Never roll your own. Use `ring`, `rustcrypto`, or framework
  primitives.
- Hash login material with `argon2` (RustCrypto) at strong cost.
- AES-GCM for symmetric, Ed25519 for signing.
- Random IDs: `rand::rngs::OsRng` — never `thread_rng()` for
  security-relevant values.

## Unsafe

- `unsafe` blocks require a `// SAFETY:` comment explaining the
  invariants the caller must uphold.
- Avoid `unsafe` in new code unless the alternative is materially
  worse (FFI is the canonical exception).
- `cargo clippy` with `clippy::undocumented_unsafe_blocks = warn`.

## TLS

- HTTPS-only outbound; never disable certificate verification in
  `reqwest::Client::builder().danger_accept_invalid_certs(true)`
  outside a one-off debug script.
- mTLS via `rustls` `ClientConfig::with_client_auth_cert`.

## Static analysis

- `cargo clippy` with the `pedantic` group enabled in CI.
- `gitleaks` or `trufflehog` on every PR.
- `cargo geiger` to gauge `unsafe` density of dependencies.
