# Framework Astro Stack Standards

## Update Metadata

- Rationale: establish Astro-specific patterns for content-rich sites with island architecture.
- Expected gain: consistent Astro code quality, performance patterns, and content collection standards.
- Potential impact: Astro projects get enforceable island, content, and SSG/SSR patterns.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Framework: Astro 4+ (content-first, island architecture).
- Base standard: extends `standards/framework/stacks/typescript.md` — all TS rules apply.
- Supporting formats: Markdown, MDX, YAML, JSON.
- Toolchain baseline: inherits from TypeScript + Astro CLI.
- Distribution: static build (SSG), server deployment (SSR), or hybrid.

## Required Tooling

- Inherits all tooling from `typescript.md`.
- CLI: `astro` commands (dev, build, preview, check).
- Content: Astro content collections with Zod schemas.
- E2E: Playwright for page-level testing.
- Integration testing: `astro:test` utilities.

## Minimum Gate Set

- Pre-commit: inherits from `typescript.md`.
- Pre-push: inherits from `typescript.md` + `astro check` (type checking Astro files).

## Quality Baseline

- Inherits all quality rules from `typescript.md`.
- Performance: target Lighthouse score 90+ across all categories.
- Zero layout shift (CLS < 0.1). Explicit image dimensions. Font preloading.
- Content collections must have Zod schemas for type-safe frontmatter.
- Accessibility: same WCAG 2.1 AA requirements as React standard.

## Code Patterns

- **Island architecture**: default to zero-JS static HTML. Add `client:*` directives only when interactivity is required.
- **Client directives**: `client:load` (immediate), `client:idle` (after page load), `client:visible` (intersection observer). Prefer `client:visible` or `client:idle` over `client:load`.
- **Content collections**: define schemas in `src/content/config.ts`. Use `getCollection()` and `getEntry()` for type-safe data access.
- **Integrations**: use official Astro integrations (@astrojs/react, @astrojs/tailwind, @astrojs/mdx).
- **Layouts**: reusable layout components in `src/layouts/`. Slot-based composition.
- **Styling**: scoped `<style>` in Astro components. Tailwind for utility classes. Global styles minimal.
- **API routes**: `src/pages/api/` for server endpoints (SSR mode only).
- **Project layout**: `src/pages/`, `src/components/`, `src/layouts/`, `src/content/`, `src/lib/`.

## Testing Patterns

- Inherits patterns from `typescript.md`.
- Page tests: Playwright for rendered output verification.
- Content tests: validate collection schemas against sample data.
- Component tests: island components tested with their framework's testing library (React Testing Library, etc.).
- Build tests: verify static build produces expected routes and assets.

## Update Contract

This file is framework-managed and may be updated by framework releases.
