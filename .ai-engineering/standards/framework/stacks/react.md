# Framework React Stack Standards

## Update Metadata

- Rationale: establish React-specific patterns for component architecture, design systems, and UI testing.
- Expected gain: consistent React code quality, accessibility, and design system enforcement.
- Potential impact: React projects get enforceable component, state, and testing patterns.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Framework: React 18+ with Vite (or CRA/Remix per project convention).
- Base standard: extends `standards/framework/stacks/typescript.md` — all TS rules apply.
- Supporting formats: CSS/Tailwind, Markdown, JSON.
- Toolchain baseline: inherits from TypeScript + React-specific tooling.
- Distribution: static build, container image, or platform deployment (Vercel, Netlify, Cloudflare Pages).

## Required Tooling

- Inherits all tooling from `typescript.md`.
- Component testing: React Testing Library (`@testing-library/react`).
- API mocking: MSW (Mock Service Worker).
- E2E: Playwright (preferred) or Cypress.
- Accessibility: `eslint-plugin-jsx-a11y`, `axe-core`.

## Minimum Gate Set

- Pre-commit: inherits from `typescript.md`.
- Pre-push: inherits from `typescript.md` + `eslint-plugin-jsx-a11y` rules enforced.

## Quality Baseline

- Inherits all quality rules from `typescript.md`.
- Accessibility: WCAG 2.1 AA compliance. All interactive elements keyboard-navigable. ARIA attributes where semantic HTML is insufficient.
- Design system: use semantic design tokens (CSS custom properties or theme object). Never use raw color values or direct utility classes for colors — use token references.
- Responsive: all components must render correctly at mobile (320px), tablet (768px), and desktop (1280px) breakpoints.
- SEO (where applicable): semantic HTML, single H1, alt text on images, meta description.

## Code Patterns

- **Component composition**: prefer composition over prop drilling. Use React context sparingly.
- **Server vs Client**: default to server components (Next.js/Remix). Use `'use client'` only when needed.
- **State management**: local state first (`useState`, `useReducer`). Global state with Zustand/Jotai (lightweight). Server state with TanStack Query or SWR.
- **Design system tokens**: define colors as HSL custom properties in `:root`. Use semantic names (`--color-primary`, `--color-surface`). Never hardcode hex/rgb in components.
- **Form handling**: use `react-hook-form` with `zod` validation schemas.
- **Error boundaries**: wrap route-level components with error boundaries.
- **Small focused components**: <100 JSX lines per component.
- **Project layout**: `src/components/` (shared UI), `src/features/` (domain modules), `src/hooks/`, `src/lib/`.

## Testing Patterns

- Inherits patterns from `typescript.md`.
- Component tests: render with React Testing Library, query by accessible role/label, avoid implementation details.
- User interaction: `@testing-library/user-event` for realistic event simulation.
- Visual regression: Playwright visual comparisons or Storybook + Chromatic.
- Snapshot tests: discouraged — prefer explicit assertions.
- Accessibility tests: `axe-core` integration in component tests.

## Update Contract

This file is framework-managed and may be updated by framework releases.
