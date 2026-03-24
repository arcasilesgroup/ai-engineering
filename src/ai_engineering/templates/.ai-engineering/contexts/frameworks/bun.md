## Decision Tree: Bun vs Node

| Factor | Prefer Bun | Prefer Node |
|--------|-----------|-------------|
| New JS/TS projects | Yes | |
| Install/run speed matters | Yes | |
| Single toolchain (run + install + test + build) | Yes | |
| Maximum ecosystem compatibility | | Yes |
| Legacy tooling assumes Node | | Yes |
| Dependency has known Bun issues | | Yes |
| Vercel deployments with Bun runtime | Yes | |

When in doubt, start with Bun. Fall back to Node if a specific dependency or tool has compatibility issues.

## Four Roles

Bun replaces four separate tools with one binary:

**1. Runtime** -- Drop-in Node-compatible runtime built on JavaScriptCore (implemented in Zig). Runs `.ts` natively without a separate transpilation step.

**2. Package Manager** -- `bun install` replaces npm/yarn/pnpm. Significantly faster. Lockfile is `bun.lock` (text format) by default in current Bun; older versions used `bun.lockb` (binary).

**3. Bundler** -- Built-in bundler and transpiler for apps and libraries. No webpack/esbuild/rollup needed for basic use cases.

**4. Test Runner** -- Built-in `bun test` with Jest-compatible API. No separate test framework install required.

## Lockfile Naming

- Current Bun: `bun.lock` (text, human-readable)
- Older Bun versions: `bun.lockb` (binary)
- Always commit the lockfile for reproducible installs
- If migrating from an older Bun version, `bun install` regenerates the lockfile in the current format

## Migration from Node

```bash
# Replace runtime
# BAD: node script.js
# GOOD: bun run script.js (or just: bun script.js)

# Replace package manager
# BAD: npm install
# GOOD: bun install

# Replace npx
# BAD: npx some-tool
# GOOD: bun x some-tool

# Replace npm scripts
# BAD: npm run dev
# GOOD: bun run dev
```

Node built-ins are supported. Prefer Bun-native APIs where they exist for better performance.

## Vercel Deployment

Set runtime to Bun in Vercel project settings, then:

```bash
# Build
bun run build
# or directly:
bun build ./src/index.ts --outdir=dist

# Install (CI/CD -- frozen lockfile for reproducibility)
bun install --frozen-lockfile
```

## Native APIs

**File I/O:**

```typescript
// GOOD: Bun.file for fast file reads
const file = Bun.file("package.json");
const json = await file.json();

const text = await Bun.file("readme.txt").text();
const bytes = await Bun.file("image.png").arrayBuffer();
```

**HTTP server:**

```typescript
// GOOD: Bun.serve for HTTP
Bun.serve({
  port: 3000,
  fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/health") {
      return new Response("ok");
    }
    return new Response("Hello from Bun", { status: 200 });
  },
});
```

For full server patterns (middleware, routing, error handling), see the `nodejs.md` context -- those patterns apply to Bun's HTTP server as well.

## Testing with bun test

**Running tests:**

```bash
bun test              # run all tests
bun test --watch      # re-run on file changes
```

**Writing tests:**

```typescript
import { expect, test, describe, beforeEach } from "bun:test";

describe("UserService", () => {
  // Arrange (shared setup)
  let service: UserService;

  beforeEach(() => {
    service = new UserService();
  });

  test("creates a user with valid data", async () => {
    // Arrange
    const input = { name: "Alice", email: "alice@example.com" };

    // Act
    const user = await service.create(input);

    // Assert
    expect(user.id).toBeDefined();
    expect(user.name).toBe("Alice");
  });

  test("throws on duplicate email", async () => {
    // Arrange
    const input = { name: "Alice", email: "alice@example.com" };
    await service.create(input);

    // Act + Assert
    expect(service.create(input)).rejects.toThrow("Email already exists");
  });
});
```

## Commands Reference

```bash
bun install                      # install dependencies
bun install --frozen-lockfile    # CI: fail if lockfile would change
bun add <package>                # add dependency
bun add -d <package>             # add dev dependency
bun remove <package>             # remove dependency
bun run <script>                 # run package.json script
bun run <file.ts>                # run a file directly
bun <file.ts>                    # shorthand for bun run
bun x <tool>                     # like npx
bun test                         # run tests
bun build ./src/index.ts --outdir=dist  # bundle
bun run --env-file=.env dev      # load env file
```

## Common Anti-Patterns

**Migration:**

- Keeping both `package-lock.json` and `bun.lock` -- choose one package manager, delete the other lockfile
- Using `npx` when Bun is the runtime -- use `bun x` instead
- Not testing dependency compatibility before switching CI to Bun

**Lockfile:**

- Not committing the lockfile -- builds become non-reproducible
- Using `bun install` in CI instead of `bun install --frozen-lockfile`

**APIs:**

- Using `fs.readFileSync` when `Bun.file` is available -- miss Bun's optimized I/O
- Using Express/Fastify for simple servers when `Bun.serve` is sufficient
- Importing Node test frameworks (`jest`, `vitest`) when `bun:test` is built in

**General:**

- Assuming 100% Node compatibility -- test edge cases, especially native addons and C++ bindings
- Not pinning Bun version in CI -- Bun evolves quickly, breaking changes are possible
