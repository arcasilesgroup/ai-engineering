# Go — Security Floor

Minimum bar for `ai-build` output in Go. Every control below is
mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input parsed through `encoding/json` with explicit
  struct tags (`json:"field,omitempty"`).
- Unknown fields rejected: `decoder.DisallowUnknownFields()`.
- Validate after decode using `go-playground/validator` or hand-rolled
  predicates; never trust raw JSON bytes downstream.

## Confidential configuration

- Read environment via a single typed config struct:
  ```go
  type Config struct {
      Port int    `env:"PORT,required"`
      DSN  string `env:"DSN,required"`
  }
  ```
- `caarlos0/env` or `kelseyhightower/envconfig` for parsing; both
  validate at boot.
- Never log raw confidential values, even at debug. Use a structured
  logger with redaction (`zap`, `slog`) and field allowlists.
- Use platform vaults (CI provider, hosting provider, cloud KMS) —
  never hard-code.

## Dependencies

- `govulncheck ./...` in CI on every PR.
- `go mod tidy` on every change; commit `go.mod` + `go.sum` together.
- `go-licenses` to gate license compliance.

## OWASP top hits

- **Injection**: parameterised queries via `database/sql` `?` /
  `$1` placeholders or an ORM (`sqlc`, `bun`, `gorm`). Never
  `fmt.Sprintf` a query.
- **Broken access control**: authorisation check beside every query,
  not just at the route. Default-deny.
- **XSS**: `html/template` over `text/template` for any HTML output;
  it auto-escapes by default.
- **CSRF**: `gorilla/csrf` middleware (or framework equivalent).
- **SSRF**: outbound HTTP allowlist when fetching user-supplied URLs.

## Cryptography

- Never roll your own. Stdlib `crypto/*` covers the basics.
- Hash login material with `golang.org/x/crypto/argon2` or
  `golang.org/x/crypto/bcrypt` at strong cost.
- Use AES-GCM (`crypto/cipher` + `crypto/aes`) for symmetric, Ed25519
  for signing.
- Random IDs: `crypto/rand`, never `math/rand` for security-relevant
  values.

## TLS

- HTTPS-only outbound; never `InsecureSkipVerify: true` outside a
  one-off debug script.
- mTLS via `tls.Config{Certificates: ..., RootCAs: ...}` for internal
  services.

## Static analysis

- `gosec` (security linter) wired into `golangci-lint`.
- `gitleaks` or `trufflehog` on every PR.
- `staticcheck` for general bug-prone patterns; `errcheck` for missed
  error returns.
