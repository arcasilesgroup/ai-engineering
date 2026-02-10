# Framework Quality Profile (Python)

## Update Metadata

- Rationale: align with v2 tooling baseline and explicit thresholds; define what Phase 5 quality skills enforce for Python.
- Expected gain: predictable quality outcomes in commit and push workflows with measurable criteria.
- Potential impact: missing tools or failing checks block governed operations.

## Mandatory Local Checks

- `ruff format --check`
- `ruff check`
- `ty check src`
- `pytest`
- `pip-audit`

## Test and Coverage Policy

- Minimum overall coverage target: 80 percent.
- Governance-critical paths (install, update safety, hooks, command workflows): target 90 percent.
- New behavior requires at least one unit or integration test.

## Complexity and Maintainability

- Functions: <50 lines, single responsibility.
- Cyclomatic complexity: target ≤10 per function.
- Cognitive complexity: target ≤15 per function.
- Prefer explicit branch handling over implicit side effects.
- Avoid introducing stack-specific behavior outside declared standards.

## Security Rules

- No secrets in source or committed artifacts.
- Dependencies must be audited locally before push.
- Security findings are fixed locally; bypass guidance is prohibited.
