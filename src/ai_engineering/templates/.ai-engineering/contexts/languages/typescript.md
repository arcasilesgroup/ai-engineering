## Type Safety

**Critical type issues:**

- Using `any` type (be specific with types)
- Type assertions (`as`) hiding real type errors
- Missing null/undefined checks before access
- Implicit `any` from missing type annotations

**Best practices:**

- Enable `strict` mode in tsconfig.json
- Use union types instead of `any`
- Use `unknown` instead of `any` for truly unknown types
- Prefer interfaces for objects, types for unions

## Async/Promise Patterns

**Common mistakes:**

- Missing `await` on promises
- Not handling promise rejections
- Using `.then()` chains instead of async/await
- Floating promises (not awaited or handled)

**Best practices:**

```typescript
// Good: async/await with error handling
async function fetchData(): Promise<Data> {
    try {
        const response = await fetch('/api/data');
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch data:', error);
        throw error;
    }
}

// Bad: floating promise
fetch('/api/data'); // Promise not handled!
```text

## Generics & Type Constraints

**Effective generics:**

- Use generic constraints (`<T extends BaseType>`)
- Avoid overly complex generic signatures
- Name generic parameters descriptively (not just `T`)
- Use conditional types for advanced patterns

**Anti-patterns:**

- Generics with no constraints when they should have them
- Using `as` to bypass generic type checks
- Too many generic parameters (simplify)

## Null Safety

**Handle null/undefined:**

- Use optional chaining (`?.`)
- Use nullish coalescing (`??`)
- Check values before access
- Use TypeScript's `strictNullChecks`

**Patterns:**

```typescript
// Good: safe navigation
const name = user?.profile?.name ?? 'Unknown';

// Bad: unsafe access
const name = user.profile.name; // Crashes if null
```text

## Type Guards & Narrowing

**Type checking:**

- Use type predicates (`is` keyword)
- Use discriminated unions for state
- Implement proper type guards
- Leverage `typeof` and `instanceof`

**Example:**

```typescript
function isError(value: unknown): value is Error {
    return value instanceof Error;
}

if (isError(result)) {
    console.error(result.message); // TypeScript knows it's an Error
}
```text

## Module & Import Patterns

**Organize imports:**

- Absolute imports over relative when possible
- Group imports (external, internal, types)
- Use barrel exports (`index.ts`) carefully
- Avoid circular dependencies

**Anti-patterns:**

- Deep relative imports (`../../../`)
- Importing everything (`import *`)
- Circular module dependencies

## Common Anti-Patterns

**Type system misuse:**

- Type assertions to bypass errors
- `@ts-ignore` comments without explanation
- Using `Object`, `Function`, `String` wrapper types
- Excessive use of `as unknown as X`

**Runtime issues:**

- Comparing with `==` instead of `===`
- Mutating readonly arrays/objects
- Not validating external data
- Assuming types at runtime

## Error Handling

**TypeScript error patterns:**

- Create custom error classes
- Use discriminated unions for Results
- Type error objects properly
- Don't catch without handling

**Example:**

```typescript
type Result<T, E = Error> =
    | { success: true; value: T }
    | { success: false; error: E };

function parseData(input: string): Result<Data> {
    try {
        return { success: true, value: JSON.parse(input) };
    } catch (error) {
        return { success: false, error: error as Error };
    }
}
```text

## Performance

**TypeScript-specific:**

- Avoid excessive type computations
- Use type aliases for complex types
- Be careful with recursive types
- Monitor compilation times

**Runtime performance:**

- Same as JavaScript concerns
- Type guards have runtime cost
- Consider bundle size with type imports

## Node.js Specific

**Async patterns:**

- Use `async`/`await` over callbacks
- Handle stream errors properly
- Use `AbortController` for cancellation
- Implement graceful shutdown

**Type definitions:**

- Use `@types/*` packages
- Type Node.js APIs correctly
- Use `Buffer` type, not `Uint8Array`
- Type environment variables

## Testing

**Type testing:**

- Test complex type utilities
- Use `// @ts-expect-error` for negative tests
- Verify type inference works
- Test generic constraints

**Common patterns:**

- Mock with proper types
- Use `jest.Mock<ReturnType>` for typed mocks
- Type test fixtures properly
