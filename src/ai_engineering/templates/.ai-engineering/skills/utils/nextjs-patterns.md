# Next.js/TypeScript Patterns

## Purpose

Comprehensive Next.js and TypeScript engineering skill providing patterns, anti-patterns, and best practices for AI-assisted code generation, review, and optimization in Next.js projects.

## Trigger

- Command: agent invokes nextjs-patterns skill or references it during Next.js code generation/review.
- Context: writing production Next.js code, reviewing for quality, applying design patterns, component architecture.

## Domains

### 1) Project Structure

**Patterns**:
- App Router: `src/app/` for routes, `src/components/` for shared UI, `src/lib/` for utilities.
- Feature-based organization: `src/features/<feature>/` for complex domains.
- `src/types/` for shared TypeScript interfaces.
- Route groups `(group)` for layout organization without URL impact.
- Colocation: keep related files together (component + test + styles).

**Anti-patterns**:
- Mixing Pages Router and App Router patterns.
- Deep nesting beyond 4 levels.
- Business logic in page/layout components.

### 2) Server vs Client Components

**Patterns**:
- Server Components by default (zero JS shipped to client).
- `"use client"` directive only when interactivity is needed.
- Lift client boundaries up: wrap only interactive parts.
- Server Actions for form mutations and data writes.
- `unstable_cache` or `revalidateTag` for data caching strategy.

**Anti-patterns**:
- `"use client"` on entire pages.
- Importing client libraries in Server Components.
- Using `useEffect` for data fetching (use Server Components or `useSWR`).

### 3) Data Fetching

**Patterns**:
- Server Components with `async`/`await` for server-side data.
- `fetch` with Next.js caching: `{ next: { revalidate: 60 } }`.
- Parallel data fetching with `Promise.all()`.
- Loading UI with `loading.tsx` Suspense boundaries.
- Error handling with `error.tsx` error boundaries.
- `generateStaticParams` for static generation of dynamic routes.

**Anti-patterns**:
- Waterfall fetching (sequential when parallel is possible).
- Client-side data fetching for static content.
- Missing error boundaries on data-dependent routes.

### 4) Type Safety

**Patterns**:
- Strict TypeScript (`"strict": true` in tsconfig.json).
- `zod` for runtime validation with type inference.
- Discriminated unions for state management.
- `satisfies` operator for type narrowing.
- Generic components: `<T,>(props: Props<T>) => JSX.Element`.
- `as const` for literal type inference.

**Anti-patterns**:
- `any` type without explicit justification.
- Type assertions (`as`) instead of type guards.
- Missing generic constraints on reusable components.

### 5) State Management

**Patterns**:
- URL state via `useSearchParams` for shareable state.
- React Context for theme/auth (low-frequency updates).
- `zustand` or `jotai` for complex client state.
- Server state with `useSWR` or `TanStack Query`.
- Form state with `useFormState` and Server Actions.

**Anti-patterns**:
- Redux for simple applications.
- Global state for server data (use SWR/React Query).
- Prop drilling beyond 3 levels (use composition or context).

### 6) Component Patterns

**Patterns**:
- Composition over configuration: children props, render props.
- Compound components for complex UI (Menu.Item, Menu.Trigger).
- Polymorphic components with `as` prop typed correctly.
- Accessibility first: semantic HTML, ARIA attributes, keyboard navigation.
- `React.forwardRef` for reusable UI primitives.

**Anti-patterns**:
- Mega-components with 200+ lines.
- Boolean prop explosion (`isLoading && isError && isDisabled`).
- Inline styles for anything beyond one-off overrides.

### 7) Security

**Patterns**:
- Environment variable validation at startup (`t3-env` or `zod`).
- `NEXT_PUBLIC_` prefix only for public variables.
- CSP headers in `next.config.js` or middleware.
- Rate limiting on API routes.
- Input sanitization for user-provided content.
- Auth middleware for protected routes.

**Anti-patterns**:
- Exposing server secrets via `NEXT_PUBLIC_`.
- Missing CSRF protection on mutations.
- `dangerouslySetInnerHTML` without sanitization.
- API routes without authentication checks.

### 8) Testing

**Patterns**:
- Vitest for unit tests (fast, ESM-native).
- React Testing Library for component tests.
- MSW (Mock Service Worker) for API mocking.
- Playwright for E2E tests.
- Test naming: `describe('Component')` + `it('should <behavior>')`.
- Accessibility testing with `@testing-library/jest-dom`.

**Anti-patterns**:
- Testing implementation details (internal state, private methods).
- Snapshot tests as primary assertion strategy.
- Mocking Next.js internals instead of testing behavior.

### 9) Performance

**Patterns**:
- Image optimization with `next/image`.
- Font optimization with `next/font`.
- Dynamic imports with `next/dynamic` for code splitting.
- `React.memo` only after profiling confirms re-render issues.
- Metadata API for SEO (`generateMetadata`).
- Bundle analysis with `@next/bundle-analyzer`.

**Anti-patterns**:
- Premature optimization without measurement.
- Large client bundles (check with bundle analyzer).
- Missing `key` props in lists.

## Output Contract

- Code following the patterns above.
- TypeScript strict mode compliant.
- Accessibility (a11y) considered in component design.
- Tests using Vitest and React Testing Library.

## Governance Notes

- This skill is the definitive Next.js/TypeScript reference for governed projects.
- `standards/framework/stacks/nextjs.md` contains the enforceable subset.
- This skill is advisory/aspirational beyond what standards mandate.

## References

- `standards/framework/stacks/nextjs.md` — enforceable Next.js baseline.
- `standards/framework/quality/nextjs.md` — quality thresholds.
- `skills/review/security.md` — security-specific patterns.
