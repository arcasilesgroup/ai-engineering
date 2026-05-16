# Kotlin — Security Floor

Minimum bar for `ai-build` output in Kotlin. Every control below is
mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input parsed via `kotlinx.serialization` or `Moshi`
  with explicit data classes. Reject unknown fields where the threat
  model warrants.
- Validate after deserialisation; throw a typed exception or return
  a `Result<T>` failure before the value reaches business logic.

## Confidential storage (Android)

- Never store confidential values in `SharedPreferences` plain.
- Use Android `Keystore` for cryptographic material; `EncryptedSharedPreferences`
  (`androidx.security:security-crypto`) for small confidential blobs.
- Mark confidential fields with custom redacting `toString()` or use
  inline value classes that override `toString` to avoid leaking via
  logs.
- Never log raw confidential values, even at debug level.

## Network

- HTTPS-only outbound; default `OkHttpClient` rejects cleartext.
- Add a `NetworkSecurityConfig` declaring the per-domain trust
  policy; deny cleartext to production hosts.
- Pin certificates for high-value APIs via `OkHttp` `CertificatePinner`
  if the threat model justifies it.

## Dependencies

- `dependencyCheckAnalyze` (OWASP Gradle plugin) in CI on every PR.
- Renovate / Dependabot configured to track CVEs.
- Pin direct dependencies in `libs.versions.toml`; no dynamic
  versions.

## OWASP MASVS (mobile)

- **MSTG-AUTH-1**: never bake login material into the APK; auth
  through a server.
- **MSTG-CRYPTO-1**: use Android `Keystore`; never roll your own
  primitives.
- **MSTG-NETWORK-1**: HTTPS-only; pin where the threat model warrants.
- **MSTG-PLATFORM-2**: validate WebView input; never `loadUrl` with
  user-controlled URLs.
- **MSTG-CODE-3**: ProGuard / R8 configured to strip debug logging
  in release builds.

## OWASP top hits (server-side Kotlin)

- **Injection**: parameterised queries via `Exposed`, `Ktorm`, or
  JDBI. Never string-interpolate a SQL query.
- **Broken access control**: authorisation check beside every query,
  not just at the route. Default-deny.
- **CSRF**: framework middleware (Ktor `csrf`, Spring Security) for
  cookie-authenticated routes.
- **SSRF**: outbound HTTP allowlist when fetching user-supplied URLs.

## Cryptography

- Never roll your own. Use Android `Keystore` / `javax.crypto`.
- Hash login material with `argon2id` (kotlin-argon2 binding) or
  `bcrypt` at strong cost (≥12).
- Use AES-GCM for symmetric, Ed25519 for signing.
- Random IDs: `SecureRandom`; never `Random` for security-relevant
  values.

## Static analysis

- `detekt` rules for security: `IteratorNotThrowingNoSuchElementException`,
  `MissingExceptionHandling`, custom rules for `!!` usage.
- `ktlint` enforced; `detekt` in CI fails the build on errors.
- `gitleaks` or `trufflehog` on every PR.
