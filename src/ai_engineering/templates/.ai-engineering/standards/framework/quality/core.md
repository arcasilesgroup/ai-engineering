# Framework Quality Profile (Sonar-like)

## Update Metadata

- Rationale: consolidate quality thresholds as single source of truth; coverage target lowered to 90% to eliminate gap-filler bloat while keeping security enforcement non-negotiable.
- Expected gain: one authoritative location for quality baselines; stack-specific quality profiles removed (duplicated content now lives in stacks/*.md).
- Potential impact: coverage threshold change applies to all gates and CI; gap-filler tests can be removed.

## Enforcement Scope

- This profile applies to new and changed code by default.
- Team standards may add stricter checks but cannot relax this baseline.

## Required Quality Gates

- Coverage target: 90%.
- Coverage on governance-critical paths: 100%.
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

| Gate | Trigger | Checks | Test Tiers |
|------|---------|--------|------------|
| Pre-commit | `git commit` | ruff format, ruff check, gitleaks, documentation gate | — |
| Pre-push | `git push` | semgrep, pip-audit, pytest (unit tier scoped by changed modules), ty check | Unit (scoped) |
| PR / CI | Pull request | All tiers staged: unit → integration → E2E (scoped by changed modules) + coverage + duplication | Unit + Integration + E2E |
| Quality audit | On-demand | Full Sonar-like analysis (skills/quality/audit-code/SKILL.md) | All (Live opt-in) |

Test tier definitions are in `standards/framework/stacks/python.md`.

Selective test execution controls:

- `AI_ENG_TEST_SCOPE_MODE=shadow|enforce|off` controls scoped execution rollout.
- `AI_ENG_TEST_SCOPE=off` is the emergency bypass alias (forces full unit tier pre-push).
- Any scope computation failure, unmapped source, deletion in `src/**`, or high-risk/config trigger must fail closed to full tier execution.

## Test Performance Targets

| Gate | Target | Strategy |
|------|--------|----------|
| Pre-push | < 60s | Unit scoped by changed modules; fail closed to full unit tier when unsafe; parallel (`-n auto --dist worksteal`), no coverage |
| CI unit | < 90s | Parallel, full OS × Python matrix |
| CI integration | < 180s | Parallel, reduced matrix (1 Python version per OS) |
| CI E2E | < 300s | Sequential, single runner |

Test pyramid ratio target: ~50% unit, ~45% integration, ~5% E2E.

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
- `skills/quality/audit-code/SKILL.md` — quality audit skill (implements this contract).
