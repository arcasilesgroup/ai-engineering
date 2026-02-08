# Framework Quality Profile (Python)

## Update Metadata

- Rationale: keep Python quality checks deterministic and local-first.
- Expected gain: predictable quality outcomes in commit and push workflows.
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

- Keep functions focused and small.
- Prefer explicit branch handling over implicit side effects.
- Avoid introducing stack-specific behavior outside declared standards.

## Security Rules

- No secrets in source or committed artifacts.
- Dependencies must be audited locally before push.
- Security findings are fixed locally; bypass guidance is prohibited.
