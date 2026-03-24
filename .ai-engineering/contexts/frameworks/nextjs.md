## Turbopack

Next.js 16+ uses Turbopack by default for local development: an incremental bundler written in Rust that significantly speeds up dev startup and hot module replacement (HMR).

**When to use which bundler:**

| Scenario | Bundler |
|----------|---------|
| Day-to-day development (default) | Turbopack |
| Turbopack bug or webpack-only plugin needed | Webpack (disable with `--webpack` or `--no-turbopack`) |
| Production build | Check Next.js docs for your version |

**Key features:**

- Incremental compilation -- only rebuilds what changed
- File-system caching under `.next/` -- restarts reuse previous work (5-14x faster on large projects)
- No extra config needed for basic use

**Commands:**

```bash
next dev      # Turbopack by default in Next.js 16+
next build    # production build
next start    # start production server
```

**Troubleshooting slow dev:**

- Verify Turbopack is active (default in Next.js 16+)
- Check that `.next/` cache is not being cleared unnecessarily
- Use Bundle Analyzer (Next.js 16.1+) to find heavy dependencies

## App Router Conventions


**File conventions:**

```
app/
  layout.tsx          # root layout (required)
  page.tsx            # root page (/)
  loading.tsx         # loading UI
  error.tsx           # error boundary
  not-found.tsx       # 404 page
  dashboard/
    layout.tsx        # nested layout
    page.tsx          # /dashboard
    [id]/
      page.tsx        # /dashboard/:id (dynamic segment)
  (auth)/
    login/
      page.tsx        # /login (route group -- no URL segment)
  api/
    users/
      route.ts        # /api/users (route handler)
```

**Rules:**

- `layout.tsx` wraps child routes and preserves state across navigations
- `page.tsx` is the unique UI for a route -- required to make a route accessible
- Use route groups `(name)` for organization without affecting the URL
- Use `loading.tsx` for instant loading states with React Suspense
- Use `error.tsx` for granular error boundaries per route segment

## Server vs Client Components


**Decision criteria:**

| Need | Component Type | Directive |
|------|---------------|-----------|
| Fetch data, access backend resources | Server (default) | None needed |
| Use hooks (useState, useEffect) | Client | `"use client"` |
| Browser APIs (window, document) | Client | `"use client"` |
| Event handlers (onClick, onChange) | Client | `"use client"` |
| Reduce JS sent to browser | Server (default) | None needed |

```typescript
// GOOD: server component (default) -- no directive needed
async function UserList() {
  const users = await db.users.findMany();
  return (
    <ul>
      {users.map(u => <li key={u.id}>{u.name}</li>)}
    </ul>
  );
}

// GOOD: client component -- add directive at top
"use client";
import { useState } from "react";

function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

**Rules:**

- Default to Server Components -- only add `"use client"` when you need interactivity
- Push `"use client"` boundaries as far down the tree as possible
- Server Components cannot import Client Components -- pass them as children instead

## Data Fetching


**Server-side data fetching (recommended):**

```typescript
// GOOD: fetch directly in Server Components
async function Dashboard() {
  const data = await fetch("https://api.example.com/stats", {
    next: { revalidate: 60 }, // ISR: revalidate every 60 seconds
  });
  const stats = await data.json();
  return <StatsDisplay stats={stats} />;
}
```

**Patterns:**

- Fetch data in Server Components, not in Client Components where possible
- Use `cache` and `revalidate` options to control caching behavior
- Use `generateStaticParams` for static generation of dynamic routes
- Parallel data fetching with `Promise.all` to avoid waterfalls

## Route Handlers


```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const page = parseInt(searchParams.get("page") || "1");
  const users = await db.users.findMany({ skip: (page - 1) * 20, take: 20 });
  return NextResponse.json({ data: users });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  // Validate with Zod, Pydantic, etc.
  const user = await db.users.create({ data: body });
  return NextResponse.json({ data: user }, { status: 201 });
}
```

**Rules:**

- Route handlers live in `app/api/**/route.ts`
- Export named functions matching HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Route handlers run server-side -- safe for database access, secrets, etc.
- For API design patterns (status codes, pagination, error format), see `api-design.md`

## Deployment


**Vercel (recommended):**

- Zero-config deployment for most Next.js features
- Automatic edge functions, ISR, image optimization
- Use `next.config.ts` for environment-specific settings

**Self-hosted:**

```bash
next build    # creates .next/ production build
next start    # starts Node.js production server
```

- Set `output: "standalone"` in `next.config.ts` for Docker deployments
- Configure `NEXT_PUBLIC_*` env vars at build time, server-only vars at runtime

## Common Anti-Patterns

**Components:**

- Adding `"use client"` to components that don't need interactivity -- increases JS bundle
- Fetching data in Client Components when a Server Component could do it
- Not using `loading.tsx` or Suspense -- users see blank screens during data fetching

**Routing:**

- Deeply nested layouts that re-render on every navigation
- Not using route groups to organize related routes
- Mixing Pages Router and App Router patterns in the same project

**Data fetching:**

- Sequential fetches when parallel fetches are possible (waterfall)
- Not setting `revalidate` on fetch calls -- data is never refreshed or cached unpredictably
- Fetching the same data in multiple components instead of lifting it to a shared layout

**Bundling:**

- Large client-side bundles -- audit with Bundle Analyzer and code-split
- Importing server-only code in Client Components (secrets, database clients)
- Clearing `.next/` cache unnecessarily -- slows down Turbopack restarts
