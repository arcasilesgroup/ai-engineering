// The npm contract for a source-only package. The eight `ai-engineering-<target>`
// optionalDependencies that shipped through 2.5.0 never existed on the registry:
// OIDC trusted publishing cannot create a package (npm: "Package must exist"), so
// their publish always died with ENEEDAUTH, every release failed at `release.yml:245`,
// and every install warned 404. The runtime replaces the binaries — engines.bun is
// the requirement v0.13.0 carried as `requires-python`.
import { test, expect } from "bun:test";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { runCommand } from "../scripts/package-consumer-smoke.ts";

const root = join(import.meta.dir, "..");
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
  bin?: Record<string, string>;
  dependencies?: Record<string, string>;
  optionalDependencies?: Record<string, string>;
  engines?: { bun?: string };
  files?: string[];
};

/** The files npm would pack below a folder. `.DS_Store` is on npm's always-ignored list, so
 *  one Finder left in a macOS checkout is never shipped and must not be expected. */
function filesBelow(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.name === ".DS_Store") return [];
    return entry.isDirectory() ? filesBelow(path) : [path];
  });
}

let packedFilesCache: string[] | undefined;

function packedFiles(): string[] {
  if (packedFilesCache) return packedFilesCache;

  // runCommand runs npm through cmd.exe on Windows, where npm is npm.cmd.
  const result = runCommand("npm", ["pack", "--dry-run", "--json", "--ignore-scripts"], root);
  if (result.status !== 0) {
    throw new Error(`npm pack dry run failed (${result.status ?? result.errorCode}): ${result.stderr}`);
  }

  const packResults = JSON.parse(result.stdout) as Array<{ files: Array<{ path: string }> }>;
  if (packResults.length !== 1) throw new Error(`Expected one npm pack result, got ${packResults.length}`);
  packedFilesCache = packResults[0]!.files.map(({ path }) => path).sort();
  return packedFilesCache;
}

function repositoryPaths(paths: string[]): string[] {
  return paths.map((path) => relative(root, path).split(sep).join("/")).sort();
}

test("the manifest declares the Bun executable and exact runtime contract", () => {
  expect(pkg.bin).toEqual({ "ai-eng": "bin/ai-eng.js" });
  expect(pkg.engines).toEqual({ bun: ">=1.4.4" });
  expect(pkg.dependencies).toEqual({ "@clack/prompts": "1.7.0", "fast-wrap-ansi": "0.2.2" });
  expect(pkg.files).toEqual([
    "bin",
    "src",
    "skills",
    "agents",
    "scripts/.embed",
    "templates",
    "NOTICE.md",
    "THIRD-PARTY-NOTICES.md",
    "CHANGELOG.md",
  ]);
});

test("the source-only package declares no optional platform dependencies", () => {
  expect(pkg.optionalDependencies).toBeUndefined();
});

test("the platform-package scripts are gone with the scheme", () => {
  expect(existsSync(join(root, "scripts", "build-platform-package.ts"))).toBe(false);
  expect(existsSync(join(root, "scripts", "set-platform-deps.ts"))).toBe(false);
});

test("npm's packed runtime includes every launcher, source, and embedded asset file", () => {
  const files = packedFiles();
  const expectedRuntimeFiles = repositoryPaths(
    ["bin", "src", "scripts/.embed"].flatMap((directory) => filesBelow(join(root, directory))),
  );
  const actualRuntimeFiles = files
    .filter((path) => path.startsWith("bin/") || path.startsWith("src/") || path.startsWith("scripts/.embed/"))
    .sort();

  expect(actualRuntimeFiles).toEqual(expectedRuntimeFiles);
  expect(files.filter((path) => path === "package.json")).toEqual(["package.json"]);
  expect(files.filter((path) => path.startsWith("dist/"))).toEqual([]);
  expect(files.filter((path) => path === "scripts/build.ts")).toEqual([]);
});

test("skills ship in npm and packs do not", () => {
  expect(packedFiles().filter((path) => path.startsWith("skills/"))).toEqual(
    repositoryPaths(filesBelow(join(root, "skills"))),
  );
  expect(packedFiles().filter((path) => path.startsWith("packs/"))).toEqual([]);
});

test("test-only eval fixtures are absent from the npm package", () => {
  expect(
    packedFiles().filter(
      (path) =>
        /(?:^|\/)verify-tiers\/evals\//.test(path) ||
        path.startsWith("tests/fixtures/verify-tiers/evals/"),
    ),
  ).toEqual([]);
});

test("ai-code-review's review and debt workflows live in ai-verify", () => {
  expect(existsSync(join(root, "skills", "ai-code-review"))).toBe(false);

  const aiVerify = readFileSync(join(root, "skills", "ai-verify", "SKILL.md"), "utf8");
  expect(aiVerify).toMatch(/over-engineering findings/i);
  expect(aiVerify).toMatch(/debt collection/i);
  expect(aiVerify).toMatch(/AGENTS\.md code style rules/i);
});
