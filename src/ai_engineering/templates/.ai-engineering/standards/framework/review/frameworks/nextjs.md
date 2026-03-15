# Next.js Review Guidelines

## Update Metadata
- Rationale: Next.js-specific patterns for App Router, server components, and data fetching.

## App Router Patterns
- Default to Server Components — use `'use client'` only when needed (interactivity, hooks, browser APIs).
- Use `loading.tsx` and `error.tsx` for route-level UI states.
- Colocate data fetching with the component that needs it.

## Data Fetching
- Use React Server Components for data fetching — no `useEffect` for initial data.
- Use `cache()` and `revalidate` for ISR patterns.
- Avoid waterfall requests — fetch in parallel with `Promise.all()`.

## Performance
- Use `next/image` for automatic image optimization.
- Use `next/font` for font loading optimization.
- Minimize client-side JavaScript — keep interactive islands small.

## Security
- Never expose server secrets in client components.
- Use Server Actions for mutations — validated server-side.
- Set CSP headers via `next.config.js`.

## References
- Enforcement: `standards/framework/stacks/nextjs.md`
