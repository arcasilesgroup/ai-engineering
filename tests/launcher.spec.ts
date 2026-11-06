// bin/ai-eng.js decides whether the CLI runs at all: the dist binary, the bun
// source path, or the honest error. Every case runs a staged copy under
// os.tmpdir(), never the checkout's own launcher: the checkout is a dev
// checkout whose dist/ may or may not exist, and the result would depend on
// whether `bun run build` ran first. The staged cases execute shebangs and
// `#!/bin/sh` fakes, which only a POSIX kernel can, so Windows skips them; the
// Windows shims are covered by scripts/package-consumer-smoke.ts.
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { afterAll, describe, expect, test } from "bun:test";
import { resolveTarget } from "../bin/ai-eng.js";

const ROOT = join(import.meta.dir, "..");
const LAUNCHER = join(ROOT, "bin", "ai-eng.js");
const VERSION = (JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")) as { version: string }).version;
const IS_WINDOWS = process.platform === "win32";
const NO_BUN_ERROR = "ai-eng: no bun runtime on PATH to run the source.\n  install bun: https://bun.com\n";

// musl (Alpine) is excluded: CI runs Ubuntu glibc, and local dev is macOS.
const TARGET = resolveTarget(process.platform, process.arch, false) ?? "linux-x64";

/** Real node, the runtime a `node bin/ai-eng.js` shim uses. `bun test` sets
 *  process.execPath to bun, so node is found on PATH, as an absolute path
 *  because several cases strip PATH. */
function findNode(): string {
  if (process.env.AI_ENG_TEST_NODE) return process.env.AI_ENG_TEST_NODE;
  const executable = IS_WINDOWS ? "node.exe" : "node";
  const found = (process.env.PATH ?? "")
    .split(delimiter)
    .map((directory) => join(directory, executable))
    .find((path) => existsSync(path));
  if (!found) throw new Error("Node is required to exercise the launcher's node entry");
  return found;
}

const NODE = findNode();
const stagingRoots: string[] = [];

afterAll(() => {
  for (const stagingRoot of stagingRoots.splice(0)) rmSync(stagingRoot, { recursive: true, force: true });
});

type Staged = { stagingRoot: string; packageRoot: string; launcher: string };

/** A consumer-shaped install, node_modules/ai-engineering/bin/ai-eng.js, with
 *  nothing else next to it: each case adds the dist build, source, dev marker
 *  or leftover package it is about. realpath: macOS's tmpdir is a symlink. */
function stageLauncher(prefix: string): Staged {
  const stagingRoot = mkdtempSync(join(realpathSync(tmpdir()), prefix));
  stagingRoots.push(stagingRoot);
  const packageRoot = join(stagingRoot, "node_modules", "ai-engineering");
  const launcher = join(packageRoot, "bin", "ai-eng.js");
  mkdirSync(dirname(launcher), { recursive: true });
  copyFileSync(LAUNCHER, launcher);
  chmodSync(launcher, 0o755);
  return { stagingRoot, packageRoot, launcher };
}

/** The real CLI source, as a published install ships it. */
function addRealSource({ packageRoot }: Staged): void {
  symlinkSync(join(ROOT, "src"), join(packageRoot, "src"));
  copyFileSync(join(ROOT, "package.json"), join(packageRoot, "package.json"));
}

/** A stand-in src/cli.ts whose output names the in-process import, so it can
 *  never be mistaken for a spawned bun or a dist binary. */
function addMarkerSource({ packageRoot }: Staged): void {
  mkdirSync(join(packageRoot, "src"), { recursive: true });
  writeFileSync(
    join(packageRoot, "src", "cli.ts"),
    'console.log("from-in-process-import", ...process.argv.slice(2));\n',
  );
}

function markDevCheckout({ packageRoot }: Staged): void {
  mkdirSync(join(packageRoot, "scripts"), { recursive: true });
  writeFileSync(join(packageRoot, "scripts", "build.ts"), "// dev checkout marker\n");
}

function writeFakeExecutable(path: string, output: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `#!/bin/sh\necho ${output} "$@"\n`);
  chmodSync(path, 0o755);
}

/** A PATH holding bun and nothing else: no node, no system tools. */
function bunOnlyPath({ stagingRoot }: Staged): string {
  const directory = join(stagingRoot, "bun-only");
  mkdirSync(directory);
  symlinkSync(process.execPath, join(directory, "bun"));
  return directory;
}

function run(command: string, args: string[], path: string) {
  const done = spawnSync(command, args, { encoding: "utf8", env: { ...process.env, PATH: path } });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

describe("resolveTarget", () => {
  test("maps the seven host shapes to package suffixes", () => {
    expect(resolveTarget("darwin", "arm64", false)).toBe("darwin-arm64");
    expect(resolveTarget("darwin", "x64", false)).toBe("darwin-x64");
    expect(resolveTarget("win32", "arm64", false)).toBe("windows-arm64");
    expect(resolveTarget("linux", "x64", false)).toBe("linux-x64");
    expect(resolveTarget("linux", "x64", true)).toBe("linux-musl-x64");
    expect(resolveTarget("linux", "arm64", true)).toBe("linux-musl-arm64");
    expect(resolveTarget("sunos", "x64", false)).toBeNull();
  });

  test("musl only applies to linux", () => {
    expect(resolveTarget("darwin", "arm64", true)).toBe("darwin-arm64");
    expect(resolveTarget("win32", "x64", true)).toBe("windows-x64");
  });
});

test("the npm executable declares Bun as its shebang runtime", () => {
  const launcher = readFileSync(LAUNCHER, "utf8");
  expect(launcher.slice(0, launcher.indexOf("\n"))).toBe("#!/usr/bin/env bun");
});

describe.skipIf(IS_WINDOWS)("published install", () => {
  test("the executable runs the source with Bun and no Node on PATH", () => {
    const staged = stageLauncher("ai-eng-launcher-bun-only-");
    addRealSource(staged);

    expect(run(staged.launcher, ["--version"], bunOnlyPath(staged))).toEqual({
      status: 0,
      stdout: `ai-eng ${VERSION}\n`,
      stderr: "",
    });
  });

  test("the node entry with no binary hands the source to the bun on PATH", () => {
    const staged = stageLauncher("ai-eng-launcher-node-");
    addRealSource(staged);

    expect(run(NODE, [staged.launcher, "--version"], bunOnlyPath(staged))).toEqual({
      status: 0,
      stdout: `ai-eng ${VERSION}\n`,
      stderr: "",
    });
  });

  test("the node entry refuses clearly when Bun is absent — never a stack trace", () => {
    const staged = stageLauncher("ai-eng-launcher-no-bun-");
    addRealSource(staged);

    expect(run(NODE, [staged.launcher, "--version"], "")).toEqual({
      status: 1,
      stdout: "",
      stderr: NO_BUN_ERROR,
    });
  });

  test("a leftover platform package is never consulted — the scheme is gone", () => {
    const staged = stageLauncher("ai-eng-launcher-pkg-");
    addRealSource(staged);
    // Both places npm could have left one: nested under the package, or hoisted
    // beside it. Were either consulted, its output would appear.
    for (const modules of [join(staged.packageRoot, "node_modules"), join(staged.stagingRoot, "node_modules")]) {
      const platformPackage = join(modules, `ai-engineering-${TARGET}`);
      writeFakeExecutable(join(platformPackage, "bin", "ai-eng"), "from-platform-package");
      writeFileSync(join(platformPackage, "package.json"), '{"name":"fake","version":"0.0.0"}\n');
    }

    expect(run(NODE, [staged.launcher, "--version"], "")).toEqual({
      status: 1,
      stdout: "",
      stderr: NO_BUN_ERROR,
    });
  });

  test("a dist build for this host runs before the source", () => {
    const staged = stageLauncher("ai-eng-launcher-dist-");
    addRealSource(staged);
    writeFakeExecutable(join(staged.packageRoot, "dist", `ai-eng-${TARGET}`), "from-dist");

    expect(run(NODE, [staged.launcher, "--version"], "")).toEqual({
      status: 0,
      stdout: "from-dist --version\n",
      stderr: "",
    });
  });
});

describe.skipIf(IS_WINDOWS)("dev checkout", () => {
  test("runs dist/ai-eng from `bun run build`", () => {
    // `bun link` of this repo: scripts/build.ts is the marker the tarball lacks.
    const staged = stageLauncher("ai-eng-launcher-dev-");
    markDevCheckout(staged);
    writeFakeExecutable(join(staged.packageRoot, "dist", "ai-eng"), "from-dist-plain");

    expect(run(NODE, [staged.launcher, "--version"], "")).toEqual({
      status: 0,
      stdout: "from-dist-plain --version\n",
      stderr: "",
    });
  });

  test("with no dist, the node entry spawns the source through the bun on PATH", () => {
    const staged = stageLauncher("ai-eng-launcher-dev-source-");
    markDevCheckout(staged);
    const fakeBin = join(staged.stagingRoot, "fake-bin");
    writeFakeExecutable(join(fakeBin, "bun"), "from-bun-source");

    expect(run(NODE, [staged.launcher, "--version"], fakeBin)).toEqual({
      status: 0,
      stdout: `from-bun-source ${join(staged.packageRoot, "src", "cli.ts")} --version\n`,
      stderr: "",
    });
  });

  test("with no dist and no bun, refuses clearly", () => {
    const staged = stageLauncher("ai-eng-launcher-dev-none-");
    markDevCheckout(staged);

    expect(run(NODE, [staged.launcher, "--version"], "")).toEqual({
      status: 1,
      stdout: "",
      stderr: NO_BUN_ERROR,
    });
  });
});

// The shebang path: the launcher itself runs under bun, so in a published
// install it imports the source in-process, while a dev checkout still spawns
// the bun on PATH. The fake bun and the marker source print different lines,
// so the output names the branch the launcher took.
describe.skipIf(IS_WINDOWS)("under bun", () => {
  function stageUnderBun(prefix: string): { staged: Staged; fakeBin: string } {
    const staged = stageLauncher(prefix);
    addMarkerSource(staged);
    const fakeBin = join(staged.stagingRoot, "fake-bin");
    writeFakeExecutable(join(fakeBin, "bun"), "from-spawned-bun");
    return { staged, fakeBin };
  }

  test("a published install imports the source in-process", () => {
    const { staged, fakeBin } = stageUnderBun("ai-eng-launcher-bun-published-");

    expect(run(process.execPath, [staged.launcher, "--version"], fakeBin)).toEqual({
      status: 0,
      stdout: "from-in-process-import --version\n",
      stderr: "",
    });
  });

  test("a dev checkout spawns the source through the bun on PATH", () => {
    const { staged, fakeBin } = stageUnderBun("ai-eng-launcher-bun-dev-");
    markDevCheckout(staged);

    expect(run(process.execPath, [staged.launcher, "--version"], fakeBin)).toEqual({
      status: 0,
      stdout: `from-spawned-bun ${join(staged.packageRoot, "src", "cli.ts")} --version\n`,
      stderr: "",
    });
  });

  test("a published install runs a dist build for this host before the in-process source", () => {
    const { staged, fakeBin } = stageUnderBun("ai-eng-launcher-bun-dist-");
    writeFakeExecutable(join(staged.packageRoot, "dist", `ai-eng-${TARGET}`), "from-dist");

    expect(run(process.execPath, [staged.launcher, "--version"], fakeBin)).toEqual({
      status: 0,
      stdout: "from-dist --version\n",
      stderr: "",
    });
  });
});

test.skipIf(IS_WINDOWS)("argv through a symlink still launches (realpath invocation guard)", () => {
  const staged = stageLauncher("ai-eng-launcher-symlink-");
  const link = join(staged.stagingRoot, "ai-eng-link.js");
  symlinkSync(staged.launcher, link);
  writeFakeExecutable(join(staged.packageRoot, "dist", `ai-eng-${TARGET}`), "via-symlink");

  expect(run(NODE, [link, "--version"], "")).toEqual({
    status: 0,
    stdout: "via-symlink --version\n",
    stderr: "",
  });
});
