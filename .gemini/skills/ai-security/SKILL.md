---
name: ai-security
description: "Runs security gates: SAST with OWASP/CWE mapping, dependency vulnerability scans, secret detection, SBOM generation for compliance, pre-release security verdict. Trigger for 'is this secure', 'audit dependencies', 'check for secrets', 'security report', 'is this package safe', 'compliance review'. Not for governance process; use /ai-governance instead. Not for runtime payload inspection; use prompt-injection-guard hook instead."
effort: max
argument-hint: "all|static|deps|secrets|sbom|--fix"
tags: [security, sast, dependencies, sbom, owasp, enterprise]
requires:
  anyBins:
  - cdxgen
  - pip-audit
  bins:
  - gitleaks
  - semgrep
mirror_family: gemini-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-security/SKILL.md
edit_policy: generated-do-not-edit
---



# Security Scanning

## Quick start

```
/ai-security all       # full sweep (static + deps + secrets + sbom)
/ai-security deps      # dependency audit only
/ai-security secrets   # gitleaks scan
/ai-security sbom      # CycloneDX SBOM for compliance
/ai-security --fix     # auto-remediate where safe
```

Unified security assessment for regulated industries. Modes: `static` (SAST with semgrep), `deps` (pip-audit/npm audit), `secrets` (gitleaks), `sbom` (CycloneDX). Zero tolerance for medium+ findings. Each finding includes severity, location, fix suggestion, and CWE reference.

## When to Use

- Security review, pre-release gate, dependency audit, compliance reporting.
- NOT for code quality metrics -- use `/ai-verify quality`.
- NOT for governance compliance -- use `/ai-governance`.

## Process

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Modes

### all -- Full Scan (default)

The `all` mode runs static, deps, and secrets in sequence and produces an aggregated report. This is the default when `/ai-security` is invoked without a mode argument.

### static -- SAST

1. **Read stacks** -- read `.ai-engineering/manifest.yml` field `providers.stacks` for active languages.
2. **Secret detection** -- `gitleaks detect --source . --no-git`. Any finding is critical. Note: this is intentional for full-repo SAST scans, distinct from the `gitleaks protect --staged` pattern used in pre-commit hooks.
3. **Semgrep** -- `semgrep scan --config auto --json`. Parse for rule IDs, severity, CWE.
4. **Manual analysis** -- review what tools miss:
   - Authentication on every endpoint (A01)
   - Parameterized queries only (A03)
   - Secrets from env/vault, never hardcoded (A02)
   - HTTP security headers (A05)
   - No user-controlled URLs in HTTP clients (A10)
5. **Classify** -- severity + OWASP category per finding.

### deps -- Dependency Audit

1. **Identify lock files** -- read `providers.stacks` from `.ai-engineering/manifest.yml`, then check for matching lock files (`uv.lock`, `package-lock.json`, `Cargo.lock`, `*.csproj`).
2. **Run audit** -- Python: `uv run python -m ai_engineering.verify.tls_pip_audit --strict --desc`. Node: `npm audit --json`. Rust: `cargo audit --json`.
3. **Assess exploitability** -- mark unreachable paths as reduced severity with justification.
4. **Report** with upgrade paths.

### secrets -- Secret Detection

1. **Full scan** -- `gitleaks detect --source . --no-git --report-format json`.
2. **Staged scan** -- `gitleaks protect --staged --no-banner`.
3. **For each finding**: file, line, rule, remediation (rotate credential, store in vault).

### sbom -- Software Bill of Materials

1. **Generate** -- `cdxgen -o sbom.json --spec-version 1.5` (CycloneDX JSON).
2. **Validate** -- all direct deps with versions, license info, package URLs.
3. **Flag license risks** -- copyleft (GPL, AGPL) conflicting with project license.

### `--fix` -- Auto-fix

When `--fix` is passed, attempt automatic remediation:
- Secrets: remove from source, add to `.gitignore`, warn to rotate.
- Dependencies: `pip install --upgrade <pkg>` for fixable vulns.
- Lint findings: `semgrep --autofix` where rules support it.
- Report what was fixed and what requires manual intervention.

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

## Quick Reference

```
/ai-security              # run all modes (static, deps, secrets in sequence; aggregated report)
/ai-security static       # SAST only
/ai-security deps         # dependency audit only
/ai-security secrets      # secret detection only
/ai-security sbom         # generate SBOM
/ai-security deps --fix   # audit + auto-fix
```

## Common Mistakes

- Suppressing findings with `# nosec` -- fix the root cause or use risk acceptance.
- Ignoring transitive dependency vulns -- they are still exploitable.
- Running `gitleaks detect` on the full repo for pre-commit -- use `gitleaks protect --staged`.

## Examples

### Example 1 — pre-merge security sweep

User: "is this PR secure to merge?"

```
/ai-security all
```

Runs SAST + deps + secrets + (optional) SBOM, scores against the gate, emits PASS / WARN / FAIL with fix hints per finding.

### Example 2 — dependency audit before adding a new package

User: "is this new npm package safe?"

```
/ai-security deps
```

Runs pip-audit / npm audit / cargo-audit per stack, flags CVEs with severity + remediation.

## Integration

Called by: `/ai-verify` (security mode delegation), `/ai-verify --release` (aggregates results), pre-commit hooks (gitleaks protect --staged), pre-push hooks (semgrep, pip-audit). Risk acceptances go to: `state.db.decisions` via `/ai-governance risk`. See also: `/ai-governance`, `/ai-mcp-audit` (skill behavior), `/ai-pipeline` (CI security).

## References

- `.ai-engineering/contexts/frameworks/` -- security and OWASP control mapping.
- `.ai-engineering/manifest.yml` -- non-negotiables and gate thresholds.

$ARGUMENTS
