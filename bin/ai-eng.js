#!/usr/bin/env node
// bin/ai-eng.js — the npm entry. Resolution order:
//
//   1. the compiled binary from the platform package (ai-engineing-<target>, an
//      optional dependency) — npm installs with no runtime at all;
//   2. the TypeScript source under bun, which is what the package did before the
//      platform packages existed — so `bun add -g` and `bun link` keep working
//      even on a dev checkout where the platform packages are not published.
//
// No binary and no bun: an honest error, never a stack trace. This file is plain
// Node-compatible JS on purpose: it runs under node (npm path) and bun (fallback),
// and must not import anything from src/ statically — the source path is a dynamic
// import only bun can serve.

import { spawnSync } from "node:child_process";
import { existsSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const TARGETS = [
  "darwin-arm64",
  "darwin-x64",
  "linux-x64",
  "linux-arm64",
  "linux-musl-x64",
  "linux-musl-arm64",
  "windows-x64",
  "windows-arm64",
];

/** Which platform package carries this machine's binary. musl only applies to
 *  linux — the same kernel, two libc forks, two different binaries. */
export function resolveTarget(platform, arch, musl = false) {
  if (platform === "darwin") return `darwin-${arch}`;
  if (platform === "win32") return `windows-${arch}`;
  if (platform === "linux") return `linux-${musl ? "musl-" : ""}${arch}`;
  return null;
}

export function binaryName(platform) {
  return platform === "win32" ? "ai-eng.exe" : "ai-eng";
}

/** musl vs glibc: the runtime report names the libc it was linked against; its
 *  absence on Linux is musl (Alpine and friends). Any runtime without a report
 *  falls through to glibc — the common case — and a wrong guess still gets the
 *  bun fallback or the honest error below. */
function isMusl() {
  try {
    const header = process.report?.getReport?.()?.header;
    if (header) return !header.glibcVersionRuntime;
  } catch {
    /* no report: assume glibc */
  }
  return false;
}

/** Spawn one candidate binary and exit with its status. Never returns. */
function runBinary(bin) {
  const run = spawnSync(bin, process.argv.slice(2), { stdio: "inherit" });
  if (run.error) {
    process.stderr.write(`ai-eng: ${bin} could not be executed: ${run.error.message}\n`);
    process.exit(1);
  }
  process.exit(run.status ?? 1);
}

async function main() {
  const musl = process.platform === "linux" ? isMusl() : false;
  const target = resolveTarget(process.platform, process.arch, musl);
  if (target) {
    let pkgDir = null;
    try {
      pkgDir = dirname(createRequire(import.meta.url).resolve(`ai-engineering-${target}/package.json`));
    } catch {
      /* the platform package is not installed — fall through */
    }
    if (pkgDir) {
      const bin = join(pkgDir, "bin", binaryName(process.platform));
      if (existsSync(bin)) {
        runBinary(bin);
      }
    }
  }
  // Dev checkout with a fresh build: dist/ai-eng-darwin-arm64 exists and
  // matches this machine even though the platform package was never installed.
  if (target) {
    const local = join(dirname(fileURLToPath(import.meta.url)), "..", "dist", `ai-eng-${target}`);
    if (existsSync(local)) runBinary(local);
  }
  if (process.versions.bun) {
    // cli.ts reads process.argv and exits on its own — importing it is running it.
    await import(join(dirname(fileURLToPath(import.meta.url)), "..", "src", "cli.ts"));
    return;
  }
  process.stderr.write(
    `ai-eng: no prebuilt binary for ${target ?? `${process.platform}-${process.arch}`} and no bun runtime to run the source.\n` +
      "  reinstall the package: npm install -g ai-engineering@latest\n" +
      "  or install bun: https://bun.com\n",
  );
  process.exit(1);
}

// "Am I the script node was pointed at?" — compared on real paths, because
// argv[1] and import.meta.url can disagree through a symlink (/tmp →
// /private/tmp on macOS) and a mismatched guard makes the launcher a silent
// no-op: exit 0, no output, nothing on stderr.
const invoked = (() => {
  try {
    return realpathSync(process.argv[1] ?? "") === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
})();
if (invoked) main();
