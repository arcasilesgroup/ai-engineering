---
name: security
description: Use when scanning for vulnerabilities, secrets, or supply-chain risks — pre-commit secret scans, dependency audits, SAST, SBOM generation, threat modeling. Trigger for "scan for security", "is this safe to merge", "audit dependencies", "generate SBOM". Maps findings to OWASP/CWE.
effort: max
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-security

Orchestrates the security toolchain across secrets, SAST, dependency
audits, and supply-chain attestation. Findings map to OWASP Top 10 and
CWE identifiers and feed `decision-store.json` for risk acceptance.

> **Dual-Plane** (ADR-0002) — every action proposed by the LLM passes
> through the OPA gatekeeper before execution. Audit log is append-only.

## When to use

- Pre-commit / pre-push security gate
- "Is this PR safe to merge?", "audit my dependencies"
- New plugin acceptance (Sigstore + SLSA + Scorecard verification)
- Periodic supply-chain re-verification
- Threat modeling new architecture

## Lanes (parallel)

1. **Secrets** — `gitleaks protect --staged --no-banner` (commit hot path)
   and `gitleaks detect --no-git` (cold path / deep scan).
2. **SAST** — `semgrep --config=p/owasp-top-ten --config=p/cwe-top-25`
   for language-specific rules + custom org rule packs.
3. **Dependencies** — `pip-audit` (Python), `bun audit` / `npm audit`
   (TypeScript), `cargo audit` (Rust), `grype` for container images.
4. **SBOM** — `syft` produces CycloneDX 1.6 SBOM; `grype` consumes it
   to surface known CVEs without re-scanning binaries.
5. **Supply chain** — verify Sigstore keyless signature, SLSA v1.0
   provenance, OpenSSF Scorecard ≥ 7 for every plugin install.
6. **Injection guard** — prompt-injection regex + heuristics on user
   input flowing to LLMs (Dual-Plane Input Guard).

## Process

1. **Detect scope** — staged-only (commit), diff (PR), full repo
   (release-gate / nightly).
2. **Run lanes in parallel** with timeouts and fail-fast on critical
   findings.
3. **Normalize findings** — every finding has stable ID, severity
   (info/low/medium/high/critical), CWE/OWASP mapping, and remediation.
4. **Map to risk acceptance** — if a finding blocks merge but is
   accepted: persist to `decision-store.json` with TTL by severity
   (critical=7d, high=30d, medium=90d, low=180d).
5. **Emit telemetry** — every finding written to
   `framework-events.ndjson` for observability and audit.
6. **Delegate to `security-scanner` agent** — agent owns aggregation,
   de-duplication, and adversarial validation of findings.

## Hard rules

- NEVER add findings to allowlists without `governance` skill approval.
- NEVER suppress with `# nosec`, `// @ts-ignore`, etc. — fix or accept
  with TTL. Risk acceptance is logged-acceptance, not weakening.
- NEVER install plugins missing Sigstore signature, SLSA provenance,
  or Scorecard < 7. CI enforces `--ignore-scripts` on npm/bun.
- All GitHub Actions pinned to immutable commit SHAs, not mutable tags.

## Common mistakes

- Skipping deep scan because hot-path passed (different scope)
- Treating all severities equally — gate on critical/high only
- Accepting risk without owner, spec ref, and TTL
- Forgetting SBOM regeneration on dependency bumps
- Trusting plugin tags instead of pinning commit SHAs
