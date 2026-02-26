# Framework TypeScript Stack Standards

## Update Metadata

- Rationale: establish generic TypeScript baseline that framework-specific stacks (React, NestJS, Astro) extend.
- Expected gain: consistent TS patterns, tooling, and quality gates across all TypeScript-based projects.
- Potential impact: framework-specific stacks reference this file as their base; changes here cascade.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Supporting formats: Markdown, YAML, JSON, Bash.
- Toolchain baseline: `node` (LTS), `npm` (or `pnpm`/`bun`), `eslint`, `prettier`, `tsc`.
- Distribution: npm package, container image, or platform-specific deployment.

## Required Tooling

- Package/runtime: `node` (LTS) + package manager (`npm`, `pnpm`, or `bun` per project convention).
- Lint: `eslint` with TypeScript plugin (`@typescript-eslint`).
- Format: `prettier` (or `biome` if project convention).
- Type checking: `tsc --noEmit` (strict mode enabled in tsconfig.json).
- Test runner: `vitest` (preferred) or `jest`.
- Dependency vulnerability scan: `npm audit` (or `pnpm audit` / `bun audit`).
- Security SAST: `semgrep` (OWASP-oriented), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `prettier --check .`, `eslint .`, `gitleaks`.
- Pre-push: `semgrep`, `npm audit`, `tsc --noEmit`, `vitest run`.

## Quality Baseline

- TypeScript strict mode enabled (`"strict": true` in tsconfig.json).
- No `any` without documented justification (use `unknown` + narrowing).
- Test coverage target: per `standards/framework/quality/core.md`.
- ESLint zero warnings policy (warnings treated as errors in CI).
- JSDoc on all exported functions, types, and interfaces.

## Code Patterns

- **Type safety first**: prefer `unknown` over `any`, use discriminated unions, exhaustive switch.
- **Immutability**: prefer `readonly`, `as const`, `Readonly<T>` for data structures.
- **Null safety**: strict null checks enabled, use optional chaining and nullish coalescing.
- **Error handling**: typed errors with `Result<T, E>` pattern or discriminated unions, no bare `throw`.
- **Module organization**: barrel exports via `index.ts`, co-located tests.
- **Environment variables**: validated at startup with `zod` or `t3-env`.
- **Small focused functions**: <50 lines, single responsibility.
- **Path aliases**: configured in tsconfig.json (`@/` prefix convention).
- **Project layout**: `src/` for source, `tests/` (or co-located `*.test.ts`).

## Testing Patterns

- Vitest as test runner (or Jest if project convention).
- One test file per module, AAA pattern (Arrange-Act-Assert).
- Naming: `describe('ModuleName')` + `it('should <behavior>')`.
- Mock external dependencies with MSW or vi.mock/jest.mock.
- Type-check test files alongside source.
- Integration tests use in-memory or containerized dependencies.

## Update Contract

This file is framework-managed and may be updated by framework releases.
