---
name: release-gate
description: Use when deciding whether to ship — production release gate that aggregates 8 dimensions into GO / CONDITIONAL / NO-GO, or rolls back a bad release. Trigger for "is this releasable", "ship it to prod", "rollback", "cut a release".
effort: max
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-release-gate

Production release decision aggregator. Eight dimensions reduce to one
verdict: **GO**, **CONDITIONAL** (proceed with named exceptions),
**NO-GO** (block release). Includes a `rollback` mode for fast revert.

## When to use

- Pre-release / pre-deploy gate (the final check before tagging)
- Release candidate validation
- Hotfix release after `/ai-hotfix`
- Production rollback when an incident is declared
- Scheduled release readiness review

## Eight dimensions

1. **Coverage** — domain ≥ 80%, application ≥ 70%, adapters with
   contract tests. Trend not regressing.
2. **Security** — `gitleaks`, `semgrep`, `pip-audit`/`bun audit`,
   `grype` clean at high+ severity. Sigstore + SLSA on artifacts.
3. **Tests** — full pytest + bun test green; no flakes in last 3 runs.
4. **Lint** — `ruff check` + `bun biome check` clean.
5. **Deps** — no critical CVEs; lockfile not drifted; transitive deps
   pinned where required.
6. **Types** — `ty` (Python), `tsc --noEmit` (TS) clean.
7. **Docs** — CHANGELOG entry, release notes draft, migration guide
   for breaking changes; OpenAPI/typedoc regenerated.
8. **Packaging** — version bumped per semver; SBOM generated; Sigstore
   signature verifiable; provenance attestation present.

## Modes

- **default (release)** — run all 8 lanes in parallel; aggregate to
  GO / CONDITIONAL / NO-GO; emit `release.evaluated` event.
- **`--candidate`** — non-blocking dry run for RC builds.
- **`--rollback <tag>`** — git revert to last known-good tag, restore
  prior artifact, emit `release.rolledback` with incident reference.

## Process

1. **Read manifest** — confirm release tier (default | regulated).
2. **Run 8 lanes in parallel** with per-lane budgets.
3. **Aggregate verdicts**:
   - GO: all green
   - CONDITIONAL: ≤ 2 yellow lanes with logged risk acceptance
   - NO-GO: any red lane OR > 2 yellow OR security critical
4. **Persist evidence** — full report to `.ai-engineering/releases/<tag>.json`.
5. **Emit telemetry** — `release.gate.passed` / `release.gate.blocked`.
6. **On rollback**: capture incident ID, revert tag, run smoke tests,
   notify on-call (cross-link `incident-respond` skill).

## Hard rules

- NEVER ship with security critical findings unaccepted.
- NEVER bypass coverage regression — it is a leading signal.
- NEVER skip SBOM/provenance — supply-chain attestation is mandatory.
- Rollback decisions are logged and immutable.
- Risk acceptance for CONDITIONAL must include owner + TTL + remediation plan.

## Common mistakes

- Releasing with yellow lanes and no risk acceptance trail
- Forgetting to bump version + tag artifact at the same commit
- Treating "tests pass on my machine" as evidence
- Rolling back without capturing the failure mode for postmortem
- Skipping the docs lane because it's "just a patch"
