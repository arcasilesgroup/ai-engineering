# TypeScript — TDD Harness

`ai-build` runs RED → GREEN → REFACTOR through Vitest by default.
Tests are deterministic, parallel-safe, and never reach the network.

## Runner

- **Default**: `vitest` (Vite-native, ESM-first, fast watch).
- **Bun stack**: `bun test` is acceptable when the runtime is locked
  to Bun and matchers stay portable.
- **Node-only legacy**: `node --test` is the fallback when adding a
  dependency is forbidden.

Never introduce Jest in new code — it's slower, ESM-hostile, and
duplicates Vitest's API.

## Layout

```
src/feature/foo.ts
src/feature/foo.test.ts
src/feature/__fixtures__/sample.json
```

Co-locate `*.test.ts` next to the unit under test. Use `__fixtures__/`
for static test data; never write fixtures into `src/` paths the
bundler ships.

## Naming

- File: `<unit>.test.ts`.
- Suite: `describe('functionName', ...)`.
- Test: `it('returns X when Y', ...)` — assertion-first phrasing.

## RED → GREEN → REFACTOR

1. **RED** — write the failing test, run `vitest run path/to/foo.test.ts`,
   confirm the failure message matches the assertion you wrote.
2. **GREEN** — minimum implementation that flips the test to pass. Do
   not modify the test.
3. **REFACTOR** — restructure for clarity while the suite stays green.

## Watch flag

`vitest` (no args) enters watch mode. Use it during local TDD; CI
runs `vitest run` (one-shot) so it can't hang.

## Assertions

- Vitest's built-in `expect` (Chai-compatible).
- Prefer `toEqual` for deep equality, `toBe` for identity.
- `toMatchObject` when partial-shape is what you actually mean — not
  as a workaround for broken `toEqual`.
- Snapshot tests only for stable rendered output, never for objects
  with timestamps / IDs.

## Mocks

- `vi.fn()` for callable stubs, `vi.spyOn` to observe without replacing.
- Reset with `vi.restoreAllMocks()` in `afterEach` when a test mutates
  globals.
- Module mocks via `vi.mock('./client', () => ({ fetch: vi.fn() }))`.
- Avoid `jest.mock`-style hoisting tricks; use dependency injection.

## Async tests

- Always `await` async assertions.
- `vi.useFakeTimers()` for time-dependent code; restore in `afterEach`.
- `expect.assertions(n)` when control flow may skip a path.

## Coverage

- `vitest run --coverage` (V8 provider).
- Floor: 80 % statements, 70 % branches on touched files. Not the
  whole repo — touched code only, enforced by CI diff.
