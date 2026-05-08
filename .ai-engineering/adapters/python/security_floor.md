# Python — Security Floor

Minimum bar for `ai-build` output in Python. Every control below is
mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input (HTTP, message bus, env, CLI) is parsed through
  a schema validator: `pydantic` v2 (preferred) or `attrs` + `cattrs`.
- Validation lives at the trust boundary; downstream code receives
  the validated model, never `dict[str, Any]`.
- Reject with a structured error (HTTP 422 / typed exception), never
  silently coerce.

## Confidential configuration

- `os.environ` reads go through a single typed loader (e.g. a
  `Settings(BaseModel)`) that validates required keys at boot.
- Never log raw confidential values, even at debug level. Use a
  redacting logger filter.
- Dotenv files are git-ignored; commit a stub example file with
  placeholder values only.
- Use platform vaults (CI provider, hosting provider, cloud KMS) —
  never hard-code.

## Dependencies

- `pip-audit` (or `uv pip audit`) in CI on every PR.
- `bandit` for static analysis of common Python anti-patterns.
- Pin direct dependencies; let the lockfile pin transitives.
- Renovate / Dependabot configured to track CVEs.

## OWASP top hits (web)

- **Injection**: parameterised queries via the ORM (`Django ORM`,
  `SQLAlchemy`, `asyncpg` placeholders). Never f-string a SQL query.
- **Broken access control**: authorisation check beside every query,
  not just at the URL router. Default-deny.
- **XSS**: Django / Jinja auto-escape by default — never disable
  unless rendering trusted markdown through a sanitised pipeline.
- **CSRF**: Django middleware on; for APIs use SameSite cookies +
  per-form tokens for state-changing routes.
- **SSRF**: outbound HTTP allowlist when fetching user-supplied URLs.

## Cryptography

- Never roll your own. Use `cryptography` (PyCA) or stdlib `secrets`.
- Hash login material with argon2id (`argon2-cffi`) or bcrypt
  (`bcrypt`) at strong cost (≥12).
- Use AES-GCM for symmetric, Ed25519 for signing.
- `secrets.token_urlsafe(32)` for unguessable tokens; never
  `random.random()` for security-relevant values.

## TLS

- HTTPS-only outbound; do not disable certificate verification in any
  environment, even dev.
- For internal services, mTLS via `requests` / `httpx` `verify=` and
  client cert tuples.

## Static analysis

- `ruff` rules `S` (bandit), `B` (bugbear), `BLE` (blind except),
  `T20` (print statements) enabled.
- `gitleaks` or `trufflehog` on every PR.
- `semgrep` for deeper queries when the threat model justifies it.
