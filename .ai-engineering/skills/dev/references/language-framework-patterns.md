# Language and Framework Patterns

On-demand reference for multi-stack code generation and review. Load sections selectively by stack.

## Python

- **Typing-first**: `from __future__ import annotations`, all public APIs typed.
- **Pydantic models**: `BaseModel` for data validation, `model_validator` for complex rules.
- **Side-effect isolation**: pure functions at core, I/O at boundaries.
- **Dependency injection**: constructor injection, no global state.
- **CLI**: Typer for CLI layer, service modules for business logic.
- **Async**: `asyncio` for I/O-bound, `concurrent.futures` for CPU-bound.
- **Path handling**: `pathlib.Path` exclusively, no `os.path`.
- **Error handling**: custom exception hierarchy, `try/except` at boundaries only.

## TypeScript (Generic)

- **Strict mode**: `"strict": true` in tsconfig.json, no `any`.
- **Discriminated unions**: for state modeling and exhaustive type checking.
- **Immutability**: `readonly`, `as const`, `Readonly<T>`.
- **Error handling**: `Result<T, E>` pattern or typed error classes.
- **Zod validation**: for runtime validation of external data.
- **Path aliases**: `@/` prefix, configured in tsconfig.json.

## React

- **Server Components**: default for data-fetching, Client Components only for interactivity.
- **Component composition**: slots and render props over deep prop drilling.
- **State**: `useState` local, Zustand/Jotai global, TanStack Query server.
- **Design tokens**: HSL custom properties in `:root`, semantic names.
- **Forms**: `react-hook-form` + `zod` for type-safe validation.
- **Error boundaries**: wrap route-level and feature-level components.
- **Accessibility**: semantic HTML, ARIA, keyboard navigation, color contrast.

## React Native

- **Navigation**: React Navigation with typed routes (`RootStackParamList`).
- **Styling**: `StyleSheet.create`, themed via context, no inline style objects.
- **Native modules**: prefer Expo SDK, `expo-modules-api` for custom.
- **Offline**: AsyncStorage for simple, WatermelonDB/MMKV for complex.
- **Performance**: `React.memo` for list items, avoid inline styles in FlatList.
- **Platform code**: `.ios.ts`/`.android.ts` or `Platform.OS` checks.

## Next.js

- **App Router**: Server Components default, `'use client'` only when needed.
- **Server Actions**: for form mutations and data writes.
- **Data fetching**: RSC for initial data, TanStack Query for client-side.
- **API routes**: `src/app/api/` with typed request/response handlers.
- **Middleware**: `middleware.ts` for auth, redirects, headers.
- **Image**: `next/image` with explicit width/height.

## NestJS

- **Modules**: one per domain, declare controllers/providers/imports/exports.
- **DI**: constructor injection via NestJS IoC container.
- **Controllers**: thin, delegate to services, decorators for routing/validation.
- **DTOs**: separate request/response, `class-validator` + `class-transformer`.
- **Guards/Interceptors**: cross-cutting auth, logging, caching.
- **Exception filters**: centralized error handling with `@Catch()`.

## Astro

- **Islands**: zero-JS default, `client:visible`/`client:idle` preferred.
- **Content collections**: Zod schemas in `src/content/config.ts`.
- **Layouts**: slot-based composition in `src/layouts/`.
- **Integrations**: `@astrojs/react`, `@astrojs/tailwind`, `@astrojs/mdx`.
- **Performance**: Lighthouse 90+, zero CLS, explicit image dimensions.

## .NET / C#

- **Minimal APIs**: preferred for new services, Controllers for complex routing.
- **DI**: built-in `Microsoft.Extensions.DependencyInjection`.
- **Configuration**: `IOptions<T>` pattern with appsettings hierarchy.
- **Nullable reference types**: `<Nullable>enable</Nullable>`.
- **Async**: `async/await` for all I/O, no `.Result` or `.Wait()`.
- **Entity Framework**: code-first, `IQueryable` for composable queries.

## Rust

- **Error handling**: `thiserror` for library, `anyhow` for app. `?` operator.
- **Ownership**: prefer borrowing, `Arc<T>` for shared ownership.
- **Async**: `tokio` runtime, `rayon` for data parallelism.
- **CLI**: `clap` derive macro for argument parsing.
- **HTTP**: `axum` preferred, `reqwest` for clients.
- **Logging**: `tracing` for structured logging and spans.

## Node.js (Backend)

- **Async/await**: all I/O operations, no callbacks.
- **Streams**: for large data processing with backpressure.
- **Worker threads**: CPU-intensive tasks off the event loop.
- **Graceful shutdown**: handle `SIGTERM`/`SIGINT`, drain connections.
- **Structured logging**: JSON format with correlation IDs.
- **Health checks**: `/health` and `/ready` endpoints.

## Bash / PowerShell

- **Bash**: `set -euo pipefail`, `#!/usr/bin/env bash`, `[[ ]]` tests, local variables.
- **PowerShell**: `Set-StrictMode -Version Latest`, `$ErrorActionPreference = 'Stop'`, `CmdletBinding`.
- **Cross-OS**: dual `.sh`/`.ps1` scripts, `Join-Path`, LF vs CRLF via `.gitattributes`.
