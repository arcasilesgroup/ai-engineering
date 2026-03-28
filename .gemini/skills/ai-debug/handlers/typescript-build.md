# Handler: TypeScript Build Resolver

## Purpose

Resolves TypeScript compilation errors, Node.js module resolution failures, and linting issues. Covers the full diagnostic chain from `tsc --noEmit` through `npm run build`, ESLint, and module bundler diagnostics. Handles strict mode violations, generic type constraints, React/JSX type errors, and Node.js module interop (ESM/CJS). Targets TypeScript 5.0+ with Node.js 18+.

## Activation

Activate this handler when:

- The project contains `tsconfig.json` or `tsconfig.*.json`
- Source files have `.ts`, `.tsx`, `.mts`, or `.cts` extensions
- Build errors reference TypeScript diagnostics (e.g., `TS2322`, `TS7006`, `TS2307`)
- The user reports issues with `tsc`, `npm run build`, `next build`, or bundler output

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Node.js and TypeScript versions
node --version
npx tsc --version

# 2. Verify dependencies are installed
if [ -f "package-lock.json" ]; then
    npm ci 2>&1
elif [ -f "pnpm-lock.yaml" ]; then
    pnpm install --frozen-lockfile 2>&1
elif [ -f "yarn.lock" ]; then
    yarn install --frozen-lockfile 2>&1
elif [ -f "bun.lockb" ] || [ -f "bun.lock" ]; then
    bun install --frozen-lockfile 2>&1
fi

# 3. Run TypeScript compiler in check mode (no output files)
npx tsc --noEmit 2>&1

# 4. Run the project build script
npm run build 2>&1

# 5. Run ESLint (if configured)
npx eslint . 2>&1

# 6. Run tests
npm test 2>&1

# 7. Check for type coverage (if type-coverage is installed)
npx type-coverage 2>/dev/null
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `Parameter 'X' implicitly has an 'any' type. (TS7006)` | The parameter has no type annotation and TypeScript cannot infer it (strict mode enabled via `noImplicitAny`). | Add an explicit type annotation: `(x: string)`. For event handlers, use the specific event type: `(e: React.ChangeEvent<HTMLInputElement>)`. |
| `Object is possibly 'undefined'. (TS2532)` | Accessing a property on a value that could be `undefined` (strict null checks enabled). | Add a null check: `if (obj) { obj.prop }`. Use optional chaining: `obj?.prop`. Use nullish coalescing: `obj ?? fallback`. For definite cases, use non-null assertion `obj!.prop` only with proof. |
| `Cannot find module 'X' or its corresponding type declarations. (TS2307)` | The module is not installed, has no type definitions, or the module resolution strategy cannot find it. | Install the package: `npm install X`. Install types: `npm install -D @types/X`. Check `moduleResolution` in tsconfig.json. For local modules, verify the path and file extension. |
| `Type 'X' is not assignable to type 'Y'. (TS2322)` | Type mismatch in assignment, return value, or property. | Narrow the type with type guards, adjust the type declaration, or use a union type. Check for missing properties in object literals. Do NOT cast with `as` unless type narrowing is impossible. |
| `Generic type 'X' requires N type argument(s). (TS2314)` | A generic type is used without providing the required type parameters. | Add type arguments: `Array<string>`, `Map<string, number>`. Check the generic definition for required vs optional type parameters. |
| `React Hook 'X' is called conditionally. (react-hooks/rules-of-hooks)` | A React hook is called inside an if statement, loop, or after an early return. | Move the hook call to the top level of the component, before any conditional logic. Use the hook unconditionally and handle the condition in the callback or effect body. |
| `Property 'X' does not exist on type 'Y'. (TS2339)` | Accessing a property that is not declared on the type. Common with DOM elements, API responses, or union types. | Add the property to the type definition, use a type guard to narrow the union, or extend the interface. For DOM elements, use the specific element type (`HTMLInputElement`). |
| `Argument of type 'X' is not assignable to parameter of type 'Y'. (TS2345)` | Function argument type does not match the parameter type. | Convert the argument, update the function signature, or use a type guard before the call. Check for literal type vs string type mismatches. |
| `Type 'X' is not assignable to type 'never'. (TS2322)` | TypeScript inferred an empty array or unreachable code path as type `never`. | Provide explicit type annotation for arrays: `const arr: string[] = []`. For switch/if exhaustiveness, add the missing case. |
| `Module 'X' has no exported member 'Y'. (TS2305)` | The named export `Y` does not exist in module `X`. Version change, renamed export, or wrong import syntax. | Check the module's exports: review `index.ts` or `index.d.ts`. Verify the installed version matches the expected API. Use `import X from` for default exports vs `import { Y } from` for named exports. |
| `JSX element type 'X' does not have any construct or call signatures. (TS2604)` | A value is used as a JSX component but TypeScript does not recognize it as a valid component type. | Ensure the component returns `JSX.Element` or `React.ReactNode`. Check that the import is correct (default vs named). Verify the component is a function or class component. |
| `'X' refers to a value, but is being used as a type here. (TS2749)` | Using a runtime value where a type is expected (e.g., `typeof` missing). | Use `typeof X` to get the type of a value. For class instances, use the class name directly as a type. For enums, use `typeof MyEnum[keyof typeof MyEnum]` for the value type. |
| `Cannot use namespace 'X' as a type. (TS2709)` | Importing a namespace as if it were a type, often with incorrect import syntax. | Use `import type { X } from 'module'` for type imports. Check if the module uses `export =` vs `export default`. |

## Cache Recovery Section

```bash
# Clear TypeScript build cache
rm -rf tsconfig.tsbuildinfo
rm -rf .tsbuildinfo

# Clear node_modules and reinstall
rm -rf node_modules
rm -rf .next           # Next.js cache
rm -rf dist            # Build output
rm -rf .turbo          # Turborepo cache
npm ci                 # or pnpm install --frozen-lockfile

# Clear npm cache
npm cache clean --force

# Clear pnpm cache
pnpm store prune

# Regenerate lockfile (caution: may change dependency versions)
# rm package-lock.json && npm install

# Clear ESLint cache
rm -rf .eslintcache

# Clear Jest cache
npx jest --clearCache

# Verify TypeScript can find all project files
npx tsc --listFiles --noEmit 2>&1 | head -30

# Check which tsconfig is being used
npx tsc --showConfig 2>&1

# Verify module resolution for a specific import
npx tsc --traceResolution 2>&1 | grep "module-name" | head -10
```

## Module Resolution Troubleshooting

```bash
# Check the module resolution strategy
npx tsc --showConfig 2>&1 | grep -A2 "moduleResolution"

# Trace how TypeScript resolves a specific module
npx tsc --traceResolution 2>&1 | grep "X" | head -20

# Verify path aliases are configured correctly
# Check tsconfig.json "paths" and "baseUrl"
cat tsconfig.json | grep -A10 '"paths"'

# For ESM/CJS interop issues, check package.json "type" field
cat package.json | grep '"type"'

# Verify @types packages are installed
npm ls @types/ 2>&1

# Check for duplicate type definitions
npm ls | grep @types | sort

# For monorepo module resolution
npx tsc --listFiles 2>&1 | grep "node_modules" | sort -u | head -20
```

## tsconfig Troubleshooting

```bash
# Show the effective tsconfig (with extends resolved)
npx tsc --showConfig 2>&1

# Verify strict mode settings
npx tsc --showConfig 2>&1 | grep -E "strict|noImplicit|null"

# Common tsconfig fixes for build errors:

# 1. Missing file extensions in imports (ESM)
#    Set: "moduleResolution": "bundler" or "node16"

# 2. Cannot find module for path aliases
#    Set: "baseUrl": "." and "paths": { "@/*": ["src/*"] }
#    ALSO configure the bundler (webpack/vite alias)

# 3. JSX not recognized
#    Set: "jsx": "react-jsx" (React 17+) or "jsx": "react" (React 16)

# 4. Declaration files not found
#    Set: "typeRoots": ["./node_modules/@types", "./types"]

# 5. Files not included in compilation
#    Check: "include" and "exclude" patterns in tsconfig.json
```

## Hard Rules

- **NEVER** use `as any` to silence type errors. Fix the types.
- **NEVER** add `@ts-ignore` or `@ts-expect-error` without a paired regression test that proves the suppression is necessary and temporary.
- **NEVER** relax `strict` mode or disable `strictNullChecks`, `noImplicitAny`, or other strict flags in tsconfig.json.
- **NEVER** add `eslint-disable` comments to bypass linting rules. Fix the code.
- **NEVER** use `// @ts-nocheck` to suppress all type checking in a file.
- **ALWAYS** use explicit type annotations for function parameters and return types in public API surfaces.
- **ALWAYS** run `npx tsc --noEmit` as the primary type check, not just the bundler build.
- **ALWAYS** verify that the TypeScript version and tsconfig settings are compatible.
- **ALWAYS** install `@types/*` packages as devDependencies, not dependencies.

## Stop Conditions

- The error requires downgrading TypeScript or relaxing strict mode to resolve a fundamental type incompatibility with a third-party library. Escalate with the library name and version.
- The error is in a `.d.ts` declaration file from a third-party package that the team does not control. Document the type definition bug and escalate.
- Two fix attempts have failed for the same type error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <TS error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <TS error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | tsc --noEmit | eslint | npm test
```
