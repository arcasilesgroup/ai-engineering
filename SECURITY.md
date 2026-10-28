# Security Policy

The product is security: `ai-engineering` installs guardrails under AI coding
agents, so attacks on those guardrails are vulnerabilities of the product.

## Reporting a vulnerability

Email: **security@arcasiles.group** (PGP key on the group site).

Do **not** open a public issue for exploitable findings.

- Acknowledgement within 72 hours; triage verdict within 7 days.
- The reporter validates the fix — the one who validates is never the one who found.
- Please include the affected command, hook or surface, reproduction steps, and
  `ai-eng doctor` output where relevant.

## Supported versions

| Version | Supported |
|---|---|
| 2.x | yes |

Only the current major line receives security fixes; older lines are archived
and unsupported.

## Scope

- **Bypass of a protection guard** — critical. The five protection guards are
  `self-protect`, `no-verify`, `policy`, `injection` and `loop`. The separate
  `wrap` rewrite filters test output to reduce context use; it is not a
  protection guard. The `spoken-secret` prompt guard denies likely credential
  disclosures on surfaces that support prompt hooks.
- **Checkpoint-gate bypass** that permits a workflow action before its required
  approval or gate — high.
- Lockfile/canon tampering that survives without a `doctor` FAIL — high.
- Receipt forgery that survives `Receipt-Id` correlation — high.
- An `ai-eng` command that fetches install assets from the network — critical.
  `init` and `update` materialize assets shipped in the installed package. The
  optional version notice reads registry metadata only; it does not fetch assets.

Out of scope: social engineering of human approvals, and vulnerabilities in
the surfaces ai-engineering governs (Claude Code, OpenCode, …) — report those
upstream.

## Hardening notes

- Overrides require `reason` + `until`; expired exceptions re-arm the guard.
- gitleaks missing under a governed repo is a HARD FAIL, never silent degradation.
- `update` reinstalls packaged assets locally. The optional registry notice is
  separate from installation.
- The checkpoint guard rejects workflow writes that violate the checkpoint
  phase, approval or gate contract.
- The chain dispatcher is fail-closed: any guard crash denies the tool call.

## Disclosure policy

Coordinated disclosure: we confirm the report, ship a patch release, and credit
the reporter (unless anonymity is requested) once the fix is published.
