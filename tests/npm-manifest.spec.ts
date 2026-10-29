// The npm contract for a source-only package. The eight `ai-engineering-<target>`
// optionalDependencies that shipped through 2.5.0 never existed on the registry:
// OIDC trusted publishing cannot create a package (npm: "Package must exist"), so
// their publish always died with ENEEDAUTH, every release failed at `release.yml:245`,
// and every install warned 404. The runtime replaces the binaries — engines.bun is
// the requirement v0.13.0 carried as `requires-python`.
import { test, expect } from "bun:test";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const root = join(import.meta.dir, "..");
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
  optionalDependencies?: Record<string, string>;
  engines?: { bun?: string };
  files?: string[];
};

function filesBelow(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesBelow(path) : [path];
  });
}

function packageFiles(): string[] {
  return (pkg.files ?? []).flatMap((entry) => {
    const path = join(root, entry);
    if (!existsSync(path)) return [];
    const paths = statSync(path).isDirectory() ? filesBelow(path) : [path];
    return paths.map((file) => relative(root, file).split(sep).join("/"));
  });
}

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

test("skills ship in npm and packs do not", () => {
  expect(pkg.files?.some((path) => path === "skills" || path === "skills/")).toBe(true);
  const files = packageFiles();
  expect(files.some((path) => path.startsWith("skills/") && path.endsWith("/SKILL.md"))).toBe(true);
  expect(files.some((path) => path.startsWith("packs/"))).toBe(false);
});

test("test-only eval fixtures are absent from the npm package", () => {
  const files = packageFiles();
  expect(files.some((path) => /(?:^|\/)verify-tiers\/evals\//.test(path))).toBe(false);
  expect(files.some((path) => path.startsWith("tests/fixtures/verify-tiers/evals/"))).toBe(false);
});

test("ai-code-review's review and debt workflows live in ai-verify", () => {
  expect(existsSync(join(root, "skills", "ai-code-review"))).toBe(false);

  const aiVerify = readFileSync(join(root, "skills", "ai-verify", "SKILL.md"), "utf8");
  expect(aiVerify).toMatch(/over-engineering findings/i);
  expect(aiVerify).toMatch(/debt collection/i);
  expect(aiVerify).toMatch(/AGENTS\.md code style rules/i);
});
