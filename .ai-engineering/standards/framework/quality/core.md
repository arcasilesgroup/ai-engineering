# Framework Quality Profile (Sonar-like)

## Update Metadata

- Rationale: provide measurable quality gates without requiring local SonarQube server setup.
- Expected gain: consistent quality thresholds across assistants and repositories.
- Potential impact: pull requests may fail until tests, complexity, and duplication targets are met.

## Enforcement Scope

- This profile applies to new and changed code by default.
- Team standards may add stricter checks but cannot relax this baseline.

## Required Quality Gates

- Coverage on changed code: at least 75 percent.
- Duplicated lines on changed code: at most 3 percent.
- Reliability: no critical or blocker issues.
- Security: no critical or blocker issues.
- Maintainability: no critical debt items on changed code.

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

- `.ai-engineering/standards/framework/core.md`
- `.ai-engineering/standards/framework/stacks/python.md`
