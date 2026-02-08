# SonarLint-like Local Profile

## Update Metadata

- Rationale: provide editor-friendly local quality guidance aligned with framework gates.
- Expected gain: earlier feedback before pre-commit and pre-push checks.
- Potential impact: developers may need to tune editor rules to avoid noise while preserving severity.

## Rule Families

- correctness and reliability issues,
- maintainability and complexity issues,
- security-sensitive coding patterns,
- duplication and readability issues.

## Recommended Policy

- Treat blocker and critical findings as errors.
- Treat major findings as warnings that must be resolved before merge.
- Treat minor/info findings as backlog improvements.

## Integration Guidance

- Use this profile as local coding baseline in IDE diagnostics.
- Keep server-side Sonar integration optional; do not require local SonarQube server.
- Preserve parity with framework quality profile in `quality/core.md`.
