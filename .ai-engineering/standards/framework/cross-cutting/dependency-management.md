# Cross-Cutting Standard: Dependency Management

## Scope

Applies to all stacks. Governs how projects declare, resolve, audit, and update dependencies.

## Principles

1. **Lock files committed**: lock files (`uv.lock`, `package-lock.json`, `Cargo.lock`, `Gemfile.lock`) are always committed.
2. **Pinned versions**: direct dependencies pinned to exact or compatible versions. No floating ranges in production.
3. **Minimal dependencies**: every dependency must justify its inclusion. Prefer standard library when adequate.
4. **Vulnerability scanning**: automated scanning in CI for known CVEs.
5. **Update cadence**: dependencies reviewed monthly. Security patches applied within 48 hours.

## Patterns

- **Audit in CI**: `pip-audit` (Python), `npm audit` (Node), `cargo audit` (Rust), `bundler-audit` (Ruby), `composer audit` (PHP).
- **License compliance**: verify licenses are compatible with project license. Block copyleft in proprietary code.
- **Dependency grouping**: separate production, development, and test dependencies.
- **Update strategy**: automated PRs for minor/patch updates (Dependabot, Renovate). Manual review for major updates.
- **SBOM generation**: generate Software Bill of Materials for production releases.

## Anti-patterns

- Not committing lock files ("it works on my machine").
- Using `*` or `latest` for dependency versions.
- Adding a library for a single utility function that could be written in 10 lines.
- Ignoring vulnerability scan results without risk acceptance in decision-store.
- Transitive dependency conflicts resolved by force-overriding versions.

## Update Contract

This file is framework-managed and may be updated by framework releases.
