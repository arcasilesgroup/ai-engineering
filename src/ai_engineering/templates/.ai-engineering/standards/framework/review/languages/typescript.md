# TypeScript Review Guidelines

## Update Metadata
- Rationale: TypeScript-specific patterns for type safety, async handling, and null safety.

## Idiomatic Patterns
- Enable `strict: true` in tsconfig — no exceptions.
- Use discriminated unions for result types: `type Result<T> = { ok: true; value: T } | { ok: false; error: Error }`.
- Prefer `unknown` over `any` — force explicit type narrowing.
- Use `as const` for literal types and readonly data.
- Optional chaining `?.` and nullish coalescing `??` over manual null checks.

## Performance Anti-Patterns
- **Blocking the event loop**: Avoid synchronous operations in async contexts.
- **Missing `Promise.all()`**: Sequential awaits when operations are independent.
- **Unnecessary re-renders**: In React contexts, missing `useMemo`/`useCallback`.

## Security Patterns
- Validate all API input with runtime validators (zod, io-ts) — TypeScript types are compile-time only.
- Sanitize HTML output — TypeScript does not prevent XSS.
- Never trust `as` assertions on user input.

## Testing Patterns
- Use `@ts-expect-error` for testing type errors, not `// @ts-ignore`.
- Prefer `vitest` or `jest` with type-aware assertions.
- Test discriminated unions exhaustively.

## Self-Challenge Questions
- Is the `any` usage genuinely needed or just laziness?
- Does the type assertion (`as`) hide a real type mismatch?

## References
- Enforcement: `standards/framework/stacks/typescript.md`
