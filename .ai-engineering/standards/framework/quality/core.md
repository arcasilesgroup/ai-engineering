# Framework Quality Profile (Sonar-like)

## Update Metadata

- Rationale: define quality contract (thresholds, metrics, gate structure) for v2; Phase 5 quality skills implement this contract.
- Expected gain: consistent quality thresholds across assistants and repositories with measurable gates.
- Potential impact: pull requests may fail until tests, complexity, and duplication targets are met.

## Enforcement Scope

- This profile applies to new and changed code by default.
- Team standards may add stricter checks but cannot relax this baseline.

## Required Quality Gates

- Coverage on changed code: ≥80%.
- Coverage on governance-critical paths: ≥90%.
- Duplicated lines on changed code: ≤3%.
- Reliability: no critical or blocker issues.
- Security: no critical or blocker issues.
- Maintainability: no critical debt items on changed code.

## Gate Structure

| Gate | Trigger | Checks |
|------|---------|--------|
| Pre-commit | `git commit` | ruff format, ruff check, gitleaks |
| Pre-push | `git push` | semgrep, pip-audit, pytest, ty check |
| PR | Pull request | All pre-push checks + coverage threshold + duplication check |
| Quality audit | On-demand | Full Sonar-like analysis (skills/quality/audit-code.md) |

## Quality Metrics

- Gate pass/fail ratio per governed operation.
- Coverage trend (must not decrease).
- Remediation time for blocker/critical findings.
- Duplication trend (must not increase).

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
