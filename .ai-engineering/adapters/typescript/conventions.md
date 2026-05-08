<!-- source: contexts/languages/typescript.md @ 3cf8b83f9f5a7f4bdb7222ffdcd9c903c44d4f48 -->

# TypeScript — Build Conventions

Authoritative reference for the `ai-build` agent when generating
TypeScript code. Distilled from `contexts/languages/typescript.md` plus
`contexts/frameworks/{nextjs,react,nodejs,bun}.md`.

## Toolchain

- **Runtime / package manager**: prefer `bun` for greenfield apps,
  `pnpm` for workspaces, `npm` only when the repo already standardises
  on it. Never mix lockfiles.
- **TS execution**: `tsx` (or `bun run`) over `ts-node`.
- **Compiler**: `tsc --noEmit` for type-checking; ship JavaScript via
  `bun build`, `tsup`, or framework bundlers (Next.js, Vite).
- **Linter / formatter**: `eslint` + `prettier`, or `biome` for new
  repos. Always run formatter checks in CI.

## tsconfig.json baseline

- `"strict": true` is non-negotiable.
- `"noUncheckedIndexedAccess": true` so `arr[0]` is `T | undefined`.
- `"exactOptionalPropertyTypes": true`.
- `"target": "ES2022"` minimum; `"module": "ESNext"` for ESM-only.
- `"moduleResolution": "bundler"` for Vite / Next.js, `"NodeNext"` for
  pure Node.

## Naming

| Element | Convention | Example |
|---|---|---|
| Functions | `verb-noun` camelCase | `fetchMarketData` |
| Booleans | `is`/`has`/`should` prefix | `isValid`, `hasPermission` |
| React components | PascalCase | `MarketCard` |
| Hooks | `use` prefix | `useMarketData` |
| Types/Interfaces | PascalCase, **no** `I` prefix | `MarketData` (not `IMarketData`) |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Type-only files | `.types.ts` suffix | `market.types.ts` |

## Type system

- `any` is forbidden. Reach for `unknown` and narrow.
- Type assertions (`as Foo`) require a comment justifying why the
  compiler is wrong.
- Discriminated unions over enums; `as const` over `enum`.
- Prefer `interface` for object shapes the consumer extends, `type`
  for unions, mapped, conditional.
- `readonly T[]` and `Readonly<T>` for inputs that must not mutate.

## Async & errors

- Async/await over `.then()` chains.
- No floating promises — every promise is `await`ed, `void`'d, or
  passed to a runner. Enable `@typescript-eslint/no-floating-promises`.
- `Promise.all` for independent awaits; `Promise.allSettled` when one
  failure must not abort siblings.
- Errors: prefer `Result<T, E>` discriminated unions for expected
  failure paths; `throw` for invariants and bugs.

## Imports

- ESM-only. No `require`. No `__dirname`/`__filename` in new code —
  use `import.meta.url`.
- One named export per public symbol; default exports only when a
  framework requires them (Next.js pages, dynamic imports).
- Path aliases (`@/foo`) configured in `tsconfig.paths` AND the bundler
  config — both must agree.

## Immutability

- `as const` for literal data tables.
- `Readonly<T>` / `ReadonlyArray<T>` on parameters that must not be
  mutated.
- React state updaters return new objects; never `.push` / `.splice`
  on state.

## Performance

- Watch out for cascading `useEffect` chains in React.
- Memoise expensive selectors; `React.memo` only with stable props.
- In Node, prefer streams for large payloads; avoid loading full files
  into memory.

## Quality gate (pre-commit)

1. `tsc --noEmit`
2. `eslint .` (or `biome check`)
3. `prettier --check .` (or `biome format --check`)
4. `vitest run` (unit) — see `tdd_harness.md`
