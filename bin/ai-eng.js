#!/usr/bin/env node
// bin/ai-eng.js — the npm entry. Two layouts, two orders:
//
//   Dev checkout (scripts/build.ts is here; it is not in the published tarball):
//     1. dist/ai-eng-<target> or dist/ai-eng from `bun run build`;
//     2. the TypeScript source, via bun.
//
//   Published install (npm / bun add, no scripts/build.ts):
//     the TypeScript source under bun — the tarball ships src/ and no binary,
//     and engines.bun names the runtime it needs (the v0.13.0 requires-python
//     contract, in npm terms).
//
// No bun: an honest error, never a stack trace. This file is plain
// Node-compatible JS on purpose: it runs under node (npm path) and bun (the
// source path), and must not import anything from src/ statically — the source
// path is spawned through bun, which is the one runtime that can load it.

import { spawnSync } from "node:child_process";
import { existsSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/** Which dist binary this host wants: `bun run build --target` writes
 *  dist/ai-eng-<target>, and musl only applies to linux — the same kernel, two
 *  libc forks, two different binaries. */
export function resolveTarget(platform, arch, musl = false) {
  if (platform === "darwin") return `darwin-${arch}`;
  if (platform === "win32") return `windows-${arch}`;
  if (platform === "linux") return `linux-${musl ? "musl-" : ""}${arch}`;
  return null;
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

function packageRoot() {
  return join(dirname(fileURLToPath(import.meta.url)), "..");
}

/** scripts/build.ts ships in the repo and not in the npm tarball (`files` lists
 *  scripts/.embed only). Its presence is the dev checkout, including `bun link`. */
function isDevCheckout(root) {
  return existsSync(join(root, "scripts", "build.ts"));
}

/** A local compile, if one exists. The target-named file is a `bun run build
 *  --target` for this host; `dist/ai-eng` is what a plain `bun run build` writes.
 *  Windows may add `.exe` to either name. */
function localBinary(root, target) {
  const names = [];
  if (target) names.push(`ai-eng-${target}`, `ai-eng-${target}.exe`);
  names.push("ai-eng", "ai-eng.exe");
  for (const name of names) {
    const path = join(root, "dist", name);
    if (existsSync(path)) return path;
  }
  return null;
}

/** The source through bun, even when this launcher itself is node (the npm
 *  shebang). Never returns: honest error if bun is not on PATH. */
function runSource(root) {
  const cli = join(root, "src", "cli.ts");
  const run = spawnSync("bun", [cli, ...process.argv.slice(2)], { stdio: "inherit" });
  if (run.error) {
    process.stderr.write(
      "ai-eng: no bun runtime on PATH to run the source.\n" +
        "  install bun: https://bun.com\n",
    );
    process.exit(1);
  }
  process.exit(run.status ?? 1);
}

async function main() {
  const musl = process.platform === "linux" ? isMusl() : false;
  const target = resolveTarget(process.platform, process.arch, musl);
  const root = packageRoot();
  if (isDevCheckout(root)) {
    const local = localBinary(root, target);
    if (local) runBinary(local);
    runSource(root);
  }
  const local = localBinary(root, target);
  if (local) runBinary(local);
  if (process.versions.bun) {
    await import(join(root, "src", "cli.ts"));
    return;
  }
  // npm's shebang runs this under node; the source still runs — through the
  // bun on PATH. runSource never returns (honest error when bun is absent).
  runSource(root);
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
