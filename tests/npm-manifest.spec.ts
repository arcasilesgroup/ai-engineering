// The npm contract for a source-only package. The eight `ai-engineering-<target>`
// optionalDependencies that shipped through 2.5.0 never existed on the registry:
// OIDC trusted publishing cannot create a package (npm: "Package must exist"), so
// their publish always died with ENEEDAUTH, every release failed at `release.yml:245`,
// and every install warned 404. The runtime replaces the binaries — engines.bun is
// the requirement v0.13.0 carried as `requires-python`.
import { test, expect } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..");
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
  optionalDependencies?: Record<string, string>;
  engines?: { bun?: string };
};

test("the package declares no optionalDependencies — the platform scheme is gone", () => {
  expect(pkg.optionalDependencies).toBeUndefined();
});

test("the platform-package scripts are gone with the scheme", () => {
  expect(existsSync(join(root, "scripts", "build-platform-package.ts"))).toBe(false);
  expect(existsSync(join(root, "scripts", "set-platform-deps.ts"))).toBe(false);
});

test("the runtime the source-only package requires is declared", () => {
  expect(pkg.engines?.bun).toBeDefined();
});
