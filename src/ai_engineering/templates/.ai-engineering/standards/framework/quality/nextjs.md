# Framework Quality Profile (Next.js/TypeScript)

## Update Metadata

- Rationale: define quality contract for Next.js/TypeScript stack; mirror python.md quality profile structure.
- Expected gain: predictable quality outcomes for Next.js projects with measurable criteria.
- Potential impact: missing tools or failing checks block governed operations for Next.js stacks.

## Mandatory Local Checks

- `prettier --check .`
- `eslint .`
- `tsc --noEmit`
- `vitest run`
- `npm audit`

## Test and Coverage Policy

- Minimum overall coverage target: 80 percent.
- Governance-critical paths (authentication, API routes, middleware): target 90 percent.
- New behavior requires at least one unit or integration test.

## Complexity and Maintainability

- Functions: <50 lines, single responsibility.
- Cyclomatic complexity: target <=10 per function.
- Cognitive complexity: target <=15 per function.
- No `any` type without explicit justification comment.
- Prefer explicit return types on exported functions.

## Security Rules

- No secrets in source or committed artifacts.
- Dependencies must be audited locally before push (`npm audit`).
- Security findings are fixed locally; bypass guidance is prohibited.
- Environment variables validated at startup.
- No client-side exposure of server secrets (NEXT_PUBLIC_ prefix only for public vars).
