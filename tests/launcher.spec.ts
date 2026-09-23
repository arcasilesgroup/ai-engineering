// bin/ai-eng.js is the launcher that decides whether the CLI runs at all: the
// platform package binary, the dev-checkout dist binary, the bun source path,
// or the honest error. The realpath invocation guard already broke once (a
// symlink made the launcher a silent no-op); these tests keep that class of
// failure out. The shim is plain Node JS on purpose, so the suite runs it with
// `node` — the same runtime npm installs use.
import { spawnSync } from "node:child_process";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { afterAll, describe, expect, test } from "bun:test";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { resolveTarget } from "../bin/ai-eng.js";

const LAUNCHER = new URL("../bin/ai-eng.js", import.meta.url).pathname;

const roots: string[] = [];
const PATH_BEFORE = process.env.PATH ?? "";

function stagedLauncher(prefix: string): { root: string; launcher: string } {
  const root = mkdtempSync(join(tmpdir(), prefix));
  roots.push(root);
  // Copy the launcher into a staging tree so each case controls what sits
  // next to it: an installed platform package, a dist build, or neither.
  const bin = join(root, "ai-engineing", "bin", "ai-eng.js");
  mkdirSync(dirname(bin), { recursive: true });
  copyFileSync(LAUNCHER, bin);
  chmodSync(bin, 0o755);
  return { root, launcher: bin };
}

/** Run the staged launcher under real node — the runtime npm installs use.
 *  `bun test` sets process.execPath to bun, and under bun the launcher takes
 *  its source path instead of the binary paths under test. Resolved to an
 *  absolute path because the no-binary case strips PATH. */
const NODE = (() => {
  if (process.env.AI_ENG_TEST_NODE) return process.env.AI_ENG_TEST_NODE;
  const found = spawnSync("sh", ["-c", "command -v node"], { encoding: "utf8" });
  return found.status === 0 ? found.stdout.trim() : "node";
})();

function run(launcher: string, args: string[]) {
  const done = spawnSync(NODE, [launcher, ...args], { encoding: "utf8" });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

afterAll(() => {
  if (PATH_BEFORE === undefined) delete process.env.PATH;
  else process.env.PATH = PATH_BEFORE;
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

describe("resolveTarget", () => {
  test("maps the seven host shapes to package suffixes", () => {
    expect(resolveTarget("darwin", "arm64", false)).toBe("darwin-arm64");
    expect(resolveTarget("darwin", "x64", false)).toBe("darwin-x64");
    expect(resolveTarget("win32", "arm64", false)).toBe("windows-arm64");
    expect(resolveTarget("linux", "x64", false)).toBe("linux-x64");
    expect(resolveTarget("linux", "x64", true)).toBe("linux-musl-x64");
    expect(resolveTarget("linux", "arm64", true)).toBe("linux-musl-arm64");
    expect(resolveTarget("sunos", "x64", false)).toBeNull(); // not a supported host
  });

  test("musl only applies to linux", () => {
    expect(resolveTarget("darwin", "arm64", true)).toBe("darwin-arm64");
    expect(resolveTarget("win32", "x64", true)).toBe("windows-x64");
  });
});

describe("launcher resolution order", () => {
  test("runs the platform package binary when it is installed", () => {
    const { root, launcher } = stagedLauncher("ai-eng-launcher-pkg-");
    const pkgDir = join(root, "ai-engineing", "node_modules", "ai-engineering-darwin-arm64");
    mkdirSync(join(pkgDir, "bin"), { recursive: true });
    // The launcher resolves `ai-engineing-<target>/package.json` — without a
    // package.json the subpath resolve misses, exactly like a broken install.
    writeFileSync(join(pkgDir, "package.json"), '{"name":"fake","version":"0.0.0"}\n');
    writeFileSync(join(pkgDir, "bin", "ai-eng"), '#!/bin/sh\necho from-platform-package "$@"\n');
    chmodSync(join(pkgDir, "bin", "ai-eng"), 0o755);

    const { status, stdout } = run(launcher, ["--version"]);
    expect(status).toBe(0);
    expect(stdout).toContain("from-platform-package");
  });

  test("falls back to the dist binary of a dev checkout", () => {
    const { launcher } = stagedLauncher("ai-eng-launcher-dist-");
    const dist = join(dirname(dirname(launcher)), "dist");
    mkdirSync(dist, { recursive: true });
    writeFileSync(join(dist, "ai-eng-darwin-arm64"), "#!/bin/sh\necho from-dist \"$@\"\n");
    chmodSync(join(dist, "ai-eng-darwin-arm64"), 0o755);

    const { status, stdout } = run(launcher, ["--version"]);
    expect(status).toBe(0);
    expect(stdout).toContain("from-dist");
  });

  test("prefers the platform package over the dist build", () => {
    const { root, launcher } = stagedLauncher("ai-eng-launcher-both-");
    const pkgDir = join(root, "ai-engineing", "node_modules", "ai-engineering-darwin-arm64");
    mkdirSync(join(pkgDir, "bin"), { recursive: true });
    writeFileSync(join(pkgDir, "package.json"), '{"name":"fake","version":"0.0.0"}\n');
    writeFileSync(join(pkgDir, "bin", "ai-eng"), '#!/bin/sh\necho from-platform-package\n');
    chmodSync(join(pkgDir, "bin", "ai-eng"), 0o755);
    const dist = join(dirname(dirname(launcher)), "dist");
    mkdirSync(dist, { recursive: true });
    writeFileSync(join(dist, "ai-eng-darwin-arm64"), "#!/bin/sh\necho from-dist\n");
    chmodSync(join(dist, "ai-eng-darwin-arm64"), 0o755);

    const { stdout } = run(launcher, ["--version"]);
    expect(stdout).toContain("from-platform-package");
  });

  test("with no binary anywhere, exits 1 with the honest error — never a stack trace", () => {
    const { launcher } = stagedLauncher("ai-eng-launcher-none-");
    // No node_modules platform package, no dist/. Also no bun on PATH: the
    // launcher must report the miss, not crash importing src/cli.ts.
    const { status, stderr } = spawnSync(NODE, [launcher, "--version"], {
      encoding: "utf8",
      env: { ...process.env, PATH: "/usr/bin:/bin" },
    });
    expect(status).toBe(1);
    expect(stderr).toContain("no prebuilt binary for darwin-arm64");
    expect(stderr).not.toContain("Error");
  });

  test("argv through a symlink still launches (realpath invocation guard)", () => {
    const { root, launcher } = stagedLauncher("ai-eng-launcher-symlink-");
    const link = join(root, "ai-eng-link.js");
    symlinkSync(launcher, link);
    const dist = join(dirname(dirname(launcher)), "dist");
    mkdirSync(dist, { recursive: true });
    writeFileSync(join(dist, "ai-eng-darwin-arm64"), "#!/bin/sh\necho via-symlink \"$@\"\n");
    chmodSync(join(dist, "ai-eng-darwin-arm64"), 0o755);

    const { status, stdout } = run(link, ["--version"]);
    expect(status).toBe(0);
    expect(stdout).toContain("via-symlink");
  });
});
