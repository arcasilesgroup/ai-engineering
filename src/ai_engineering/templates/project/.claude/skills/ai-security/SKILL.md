---
name: ai-security
description: "Runs security gates: SAST with OWASP/CWE mapping, dependency vulnerability scans, secret detection, SBOM generation for compliance, pre-release security verdict. Trigger for 'is this secure', 'audit dependencies', 'check for secrets', 'security report', 'is this package safe', 'compliance review'. Not for governance process; use /ai-governance instead. Not for runtime payload inspection; use prompt-injection-guard hook instead. Not for code quality metrics; use /ai-verify quality instead."
effort: mid
argument-hint: "all|static|deps|secrets|sbom|--fix"
tags: [security, sast, dependencies, sbom, owasp, enterprise]
requires:
  bins:
  - gitleaks
  - semgrep
  anyBins:
  - cdxgen
  - pip-audit
---

# Security Scanning

Runs the repo's security gates — SAST with OWASP/CWE mapping, dependency vulnerability scans, secret detection, and SBOM generation — to produce a pre-release security verdict. Use it to answer "is this secure", audit dependencies, check for secrets, or run a compliance review.

## Quick start

```
/ai-security all       # full sweep: static + deps + secrets (aggregated report)
/ai-security static    # SAST only (semgrep)
/ai-security deps      # dependency audit only
/ai-security secrets   # gitleaks scan
/ai-security sbom      # CycloneDX SBOM for compliance
/ai-security deps --fix  # audit + auto-fix where safe
```

Unified security assessment for regulated industries. Zero tolerance for medium+ findings. Each finding carries severity, location, fix suggestion, and CWE reference.

## Workflow

Principles applied: §10.2 YAGNI (every dependency and exposed endpoint is attack surface — the smallest surface is the safest).

Step 0 — load contexts: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack + `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md`.

`all` (default) runs static -> deps -> secrets in sequence and emits one aggregated report. Per-mode procedure:

1. **static (SAST)** — run `gitleaks detect --source . --no-git` (any finding critical; full-repo scan, distinct from the pre-commit `gitleaks protect --staged`); run `semgrep scan --config auto --json` (parse rule IDs, severity, CWE); manual review of what tools miss — auth on every endpoint (A01), parameterized queries only (A03), secrets from env/vault never hardcoded (A02), HTTP security headers (A05), no user-controlled URLs in HTTP clients (A10); classify severity + OWASP per finding.
2. **deps** — identify lock files (`uv.lock` / `package-lock.json` / `Cargo.lock` / `*.csproj`) from `providers.stacks`; run Python `uv run python -m ai_engineering.verify.tls_pip_audit --strict --desc`, Node `npm audit --json`, Rust `cargo audit --json`; mark unreachable paths reduced-severity with justification; report upgrade paths.
3. **secrets** — `gitleaks detect --source . --no-git --report-format json` (full) + `gitleaks protect --staged --no-banner` (staged); per finding: file, line, rule, remediation (rotate credential, move to vault).
4. **sbom** — `cdxgen -o sbom.json --spec-version 1.5` (CycloneDX JSON); validate every direct dep has version + license + package URL; flag copyleft (GPL/AGPL) conflicting with the project license.
5. **`--fix`** — secrets: remove from source, add to `.gitignore`, warn to rotate; deps: `pip install --upgrade <pkg>` for fixable vulns; lint: `semgrep --autofix` where rules support it; report what was fixed vs what needs manual work.

## Severity Classification

| Severity | Definition | Gate Impact |
|----------|-----------|-------------|
| Blocker | Actively exploitable, breach imminent | Blocks release |
| Critical | High-impact, exploit feasible | Blocks release |
| Major | Significant risk, requires conditions | Resolve before next release |
| Minor | Low risk, defense-in-depth | Resolve during maintenance |

## Output Contract

```markdown
# Security Report: [mode]
## Score: N/100
## Verdict: PASS (>=80) | WARN (60-79) | FAIL (<60)
## Findings
| # | Severity | OWASP | CWE | Description | Location | Fix |
|---|----------|-------|-----|-------------|----------|-----|
## Tool Outputs
- gitleaks: [N findings / clean]
- semgrep: [N findings / clean]
- pip-audit: [N findings / clean]
```

## Common Mistakes

- Suppressing findings with `# nosec` — fix the root cause or use risk acceptance.
- Ignoring transitive dependency vulns — they are still exploitable.
- Running `gitleaks detect` on the full repo for pre-commit — use `gitleaks protect --staged`.

## Examples

### Example — pre-merge security sweep

User: "is this PR secure to merge?"

```
/ai-security all
```

Runs SAST + deps + secrets (+ optional SBOM), scores against the gate, and emits PASS / WARN / FAIL with a fix hint per finding.

## Integration

Called by: `/ai-verify` (security mode delegation), `/ai-verify --release` (aggregates results), pre-commit hooks (gitleaks protect --staged), pre-push hooks (semgrep, pip-audit). Risk acceptances go to `decision-store.json` via `/ai-governance risk`. See also: `/ai-governance`, `/ai-mcp-audit` (skill behavior), `/ai-pipeline` (CI security), `/ai-schema` (DB schema/injection review).

## References

- Per-stack security minimums: `.ai-engineering/overrides/<stack>/security_floor.md`.
- `.ai-engineering/overrides/_shared/security_floor.md` — cross-stack security floor.
- `.ai-engineering/manifest.yml` — non-negotiables and gate thresholds.
- `.ai-engineering/reference/semgrep-update-model.md` — two-tier Semgrep scan + manual version-bump model.

$ARGUMENTS
