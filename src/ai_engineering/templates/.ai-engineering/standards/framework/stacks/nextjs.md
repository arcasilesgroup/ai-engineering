# Framework Next.js/TypeScript Stack Standards

## Update Metadata

- Rationale: align with TypeScript base standard; add bun support and design system token patterns from audit.
- Expected gain: consistent Next.js baseline extending TypeScript base with framework-specific patterns.
- Potential impact: Next.js projects inherit TypeScript base rules and get design system enforcement.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Framework: Next.js 14+ (App Router preferred).
- Base standard: extends `standards/framework/stacks/typescript.md` — all TS rules apply.
- Supporting formats: Markdown, YAML, JSON, Bash.
- Toolchain baseline: `node`, `npm` (or `pnpm`/`bun`), `eslint`, `prettier`, `tsc`.
- Distribution: Vercel deployment, Docker container, or static export.

## Required Tooling

- Package/runtime: `node` (LTS) + `npm` (or project-configured package manager).
- Lint: `eslint` with TypeScript plugin.
- Format: `prettier`.
- Type checking: `tsc --noEmit` (strict mode enabled in tsconfig.json).
- Test runner: `vitest` (preferred) or `jest`.
- Dependency vulnerability scan: `npm audit`.
- Security SAST: `semgrep` (OWASP-oriented), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `prettier --check .`, `eslint .`, `gitleaks`.
- Pre-push: `semgrep`, `npm audit`, `tsc --noEmit`, `vitest run`.

## Quality Baseline

- TypeScript strict mode enabled (`"strict": true` in tsconfig.json).
- Test coverage target: 100%.
- ESLint zero warnings policy (warnings treated as errors in CI).
- JSDoc on all exported functions and components.

## Code Patterns

- **App Router**: prefer Server Components by default, Client Components only when needed.
- **Server Actions**: for form mutations and data writes.
- **Type safety**: strict TypeScript, no `any` without justification.
- **Environment variables**: validated at startup with `zod` or `t3-env`.
- **Small focused functions**: <50 lines, single responsibility.
- **Component composition**: prefer composition over prop drilling.
- **Project layout**: `src/app/` for routes, `src/components/` for shared UI, `src/lib/` for utilities.

## Testing Patterns

- Vitest as test runner (or Jest if project convention).
- React Testing Library for component tests.
- One test file per module, AAA pattern (Arrange-Act-Assert).
- Integration tests use `next/test` utilities or Playwright for E2E.
- Naming: `describe('ComponentName')` + `it('should <behavior>')`.
- Mock external APIs with MSW (Mock Service Worker).

## Performance

_Stack-specific performance patterns will be added as the standard evolves. Refer to `review/performance/SKILL.md` for general performance review procedures._

## Security

_Stack-specific security patterns will be added as the standard evolves. Refer to `review/security/SKILL.md` for general security review procedures._

## Update Contract

This file is framework-managed and may be updated by framework releases.
