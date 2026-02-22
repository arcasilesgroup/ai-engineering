# Framework Next.js/TypeScript Stack Standards

## Update Metadata

- Rationale: extend multi-stack support to Next.js/TypeScript projects; mirror python.md structure for consistency.
- Expected gain: predictable Next.js/TS baseline with explicit patterns for AI-assisted code generation and review.
- Potential impact: Next.js tooling requirements and code patterns become enforceable during generation and review.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Framework: Next.js (App Router preferred).
- Supporting formats: Markdown, YAML, JSON, Bash.
- Toolchain baseline: `node`, `npm` (or `pnpm`/`yarn`), `eslint`, `prettier`, `tsc`.
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
- Test coverage target: >=80% overall, >=90% for governance-critical paths.
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

## Update Contract

This file is framework-managed and may be updated by framework releases.
