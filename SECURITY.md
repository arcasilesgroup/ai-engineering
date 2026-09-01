# Security Policy (§07 — the product is security)

## Reporting a vulnerability

Email: security@arcasiles.group (PGP key on the group site). Do not open a public
issue for exploitable findings.

- Acknowledgement within 72h; triage verdict within 7 days.
- The reporter validates the fix (the one who validates is never the one who found).

## Supported versions

| Version | Supported |
|---|---|
| 0.13.x | yes |
| v1 (Python ≤1.0.0) | no — archived at tag v1-final |

## Scope

- Guard bypass (any of the five) — critical.
- Lockfile/canon tampering without a doctor FAIL — high.
- Receipt forgery that survives `Receipt-Id` correlation — high.
- Install payload fetched from the network by any verb — critical by design: it
  cannot exist; if you find a path that makes one, that is the report.

## Hardening notes

- Overrides require `reason` + `until`; expired exceptions re-arm the guard.
- gitleaks missing under a governed repo is HARD FAIL, never silent degradation.
- The `update` verb never touches the network; it re-plants from the binary.
