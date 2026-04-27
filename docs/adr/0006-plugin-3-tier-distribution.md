# ADR-0006 — Plugin Distribution: 3-Tier Federated-Curated

- **Status**: Accepted
- **Date**: 2026-04-27

## Context

Post Shai-Hulud (Sept 2025) and Shai-Hulud 2.0 (March 2026), npm and
PyPI have suffered worm-style supply chain attacks compromising hundreds
of packages. Agentic frameworks that distribute community plugins are
particularly exposed because plugins gain hook-level execution rights.

## Decision

Three-tier marketplace with progressive trust:

| Tier | Publisher | Discovery | Trust gate |
|------|-----------|-----------|------------|
| OFFICIAL | `@ai-engineering/*` org | `ai-eng plugin search official` | Sigstore + SLSA + signed by team |
| VERIFIED | Community-approved authors | curated registry | Sigstore + manual review (SECURITY.md, no `network: true` without justification, no disabled hooks) |
| COMMUNITY | Any GitHub repo with `ai-engineering-plugin` topic + valid manifesto | `ai-eng plugin install <owner>/<repo>` | Sigstore mandatory, OpenSSF Scorecard ≥ 7 |

**Mandatory cryptographic primitives** (all tiers):

- **Sigstore keyless OIDC** signing of release artifacts
- **SLSA v1.0** provenance via the `slsa-github-generator` reusable
  workflow pinned to `@v2.1.0` (NOT `@main`)
- **CycloneDX 1.6 SBOM**
- **OpenSSF Scorecard** — published

**Shai-Hulud 2.0 mitigations**:

- `validate-submission.yml` enforces `npm ci --ignore-scripts`
- All GitHub Actions pinned to **immutable commit SHAs**, not tags
- `ai-eng plugin verify --all` runs by `SessionStart` hook + nightly cron
- `yanked.json` is consulted on every install + every verify

## Consequences

- **Pro**: COMMUNITY tier is open and frictionless (Cargo-style auto
  publish) but cryptographically attested.
- **Pro**: OFFICIAL/VERIFIED tiers preserve a curated experience for
  enterprise.
- **Pro**: revocation works at three levels: yank a version, remove
  from registry, or notify installs via NDJSON event stream.
- **Con**: human review for VERIFIED is a bottleneck. Mitigated by AST
  parsers in CI that auto-fail on dangerous patterns; humans only review
  exceptions.

## Implementation references

- `ai-engineering.toml` — `[plugins]` section
- `docs/plugin-spec.md` — full manifesto schema (TODO Phase 7)
