# Security Policy

The product is security: `ai-engineering` installs guardrails under AI coding
agents, so attacks on those guardrails are vulnerabilities of the product.

## Reporting a vulnerability

Email: **security@arcasiles.group** (PGP key on the group site).

Do **not** open a public issue for exploitable findings.

- Acknowledgement within 72 hours; triage verdict within 7 days.
- The reporter validates the fix — the one who validates is never the one who found.
- Please include: affected verb (`init`/`chain`/`git`/`spec`/…), reproduction
  steps, and `ai-eng doctor` output where relevant.

## Supported versions

| Version | Supported |
|---|---|
| 2.x | yes |

Only the current major line receives security fixes; older lines are archived
and unsupported.

## Scope

- **Guard bypass (any of the five: no-verify, self-protect, injection, loop,
  wrap)** — critical.
- Lockfile/canon tampering that survives without a `doctor` FAIL — high.
- Receipt forgery that survives `Receipt-Id` correlation — high.
- Install payload fetched from the network by any verb — critical **by design**
  it cannot exist; if you find a path that makes one, that is the report.

Out of scope: social engineering of human approvals, and vulnerabilities in
the surfaces ai-engineering governs (Claude Code, OpenCode, …) — report those
upstream.

## Hardening notes

- Overrides require `reason` + `until`; expired exceptions re-arm the guard.
- gitleaks missing under a governed repo is a HARD FAIL, never silent degradation.
- The `update` verb never touches the network; it reinstalls from the binary.
- A contract nobody approved refuses to run: `spec run` checks the sha256
  pinned in `ai-eng.lock` (§9.3).
- The chain dispatcher is fail-closed: any guard crash denies the tool call.

## Disclosure policy

Coordinated disclosure: we confirm the report, ship a patch release, and credit
the reporter (unless anonymity is requested) once the fix is published.
