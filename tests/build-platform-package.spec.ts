// Windows compiles land as `ai-eng-windows-*.exe`; the packager must find them
// the same way release.yml's attest glob does (`dist/ai-eng-${target}*`).
import { afterEach, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const roots: string[] = [];
const script = join(import.meta.dir, "..", "scripts", "build-platform-package.ts");

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

test("build-platform-package packs a Windows .exe when the bare name is absent", () => {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-plat-pkg-"));
  roots.push(root);
  const dist = join(root, "dist");
  mkdirSync(dist, { recursive: true });
  // Bigger than the 1 MB floor the packager enforces against placeholders.
  writeFileSync(join(dist, "ai-eng-windows-x64.exe"), Buffer.alloc(1024 * 1024 + 8, 1));
  writeFileSync(
    join(root, "package.json"),
    JSON.stringify({
      version: "0.0.0-test",
      license: "Apache-2.0",
      repository: { type: "git", url: "https://example.test/ai-engineering.git" },
    }),
  );
  const run = spawnSync(process.execPath, [script, "--target", "bun-windows-x64", "--out", dist], {
    cwd: root,
    encoding: "utf8",
  });
  expect(run.status).toBe(0);
  expect(run.stdout).toContain("ai-engineering-windows-x64@0.0.0-test");
  expect(run.stdout).toContain(join("ai-engineering-windows-x64", "bin", "ai-eng.exe"));
});
