# Framework Quality Profile (Sonar-like)

## Update Metadata

- Rationale: enforce 100% security and quality compliance as non-negotiable baseline; zero tolerance for security findings (medium+) and quality gate failures.
- Expected gain: every governed operation passes all gates; security posture fully enforced with tamper resistance.
- Potential impact: stricter enforcement blocks merges until all findings are remediated; no exceptions without risk acceptance.

## Enforcement Scope

- This profile applies to new and changed code by default.
- Team standards may add stricter checks but cannot relax this baseline.

## Required Quality Gates

- Coverage on changed code: ≥80%.
- Coverage on governance-critical paths: ≥90%.
- Duplicated lines on changed code: ≤3%.
- Reliability: no critical or blocker issues.
- Security: zero findings medium severity and above. No exceptions without risk acceptance.
- Maintainability: no critical debt items on changed code.

## Security Enforcement (Non-Negotiable)

- Quality gate pass rate: 100% on all governed operations.
- Security scan pass rate: 100% — zero medium/high/critical findings allowed.
- Secret detection: zero leaks. Any leak is a blocker.
- Dependency vulnerabilities: zero known vulnerabilities. Any vulnerability is a blocker.
- SAST findings (medium+): zero. Remediate or risk-accept before merge.
- Tamper resistance: hooks must be hash-verified, `--no-verify` bypass must be detectable.
- Hook integrity: SHA-256 verification mandatory at gate execution time.
- Cross-OS validation: all enforcement mechanisms must pass on Ubuntu, Windows, and macOS.

## Gate Structure

| Gate | Trigger | Checks |
|------|---------|--------|
| Pre-commit | `git commit` | ruff format, ruff check, gitleaks |
| Pre-push | `git push` | semgrep, pip-audit, pytest, ty check |
| PR | Pull request | All pre-push checks + coverage threshold + duplication check |
| Quality audit | On-demand | Full Sonar-like analysis (skills/quality/audit-code.md) |

## Quality Metrics

- Gate pass rate: 100% on governed operations (target, non-negotiable).
- Security scan pass rate: 100% (zero medium+ findings).
- Coverage trend (must not decrease).
- Remediation time for blocker/critical findings: immediate (blocks merge).
- Duplication trend (must not increase).
- Tamper resistance score: 100/100 (hook hash verification + bypass detection).

## Pull Request Rules

- PR must include evidence of local checks:
  - lint/format,
  - tests,
  - type checks,
  - security scans.
- Any accepted risk must be recorded in `state/decision-store.json` and `state/audit-log.ndjson`.

## Severity Policy

- blocker: merge is blocked.
- critical: merge is blocked unless explicit risk acceptance exists.
- major: fix before merge unless owner approves and logs rationale.
- minor/info: track and resolve incrementally.

## References

- `standards/framework/core.md` — non-negotiables and enforcement rules.
- `standards/framework/stacks/python.md` — stack-specific quality baseline.
- `skills/quality/audit-code.md` — quality audit skill (implements this contract).
- `skills/quality/audit-report.md` — quality report template.
