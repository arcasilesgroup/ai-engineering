#!/usr/bin/env bun
// bin/ai-eng.js — the npm entry. Bun is the runtime, so the shebang names bun:
// the installed command must start on a host with bun and no node.
//
// Two layouts, two orders:
//
//   Dev checkout (scripts/build.ts is here; it is not in the published tarball):
//     1. dist/ai-eng-<target> or dist/ai-eng from `bun run build`, but only when
//        the build stamp written beside that very binary still names the version
//        in package.json;
//     2. the TypeScript source, via bun.
//
//   Published install (npm / bun add, no scripts/build.ts):
//     the TypeScript source under bun, always — the tarball ships src/ and no
//     binary, and engines.bun names the runtime it needs (the v0.13.0
//     requires-python contract, in npm terms). A dist/ that a previous install
//     left in the package root is never consulted.
//
// The version rule is the point: a compile freezes package.json into the
// executable, so a binary built from older source reports the older version and
// runs the older behaviour while the package around it says something newer.
// That is a real incident (3.3.1 installed, every command answering 3.2.2), and
// the stamp is what makes it impossible: bytes nobody can tie to this package's
// package.json do not run, and the source — which reads package.json — does.
//
// Still plain Node-compatible JS on purpose: `node bin/ai-eng.js` (or a shim
// that picks node) must keep working by handing the source to the bun on
// PATH. No bun there: an honest error, never a stack trace. It must not import
// anything from src/ statically — only bun can load the TypeScript source.

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, join } from "node:path";
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

/** The names `bun run build --target` gives one host's artifact: Bun appends the
 *  extension on Windows, so both spellings exist. Exported so scripts/build.ts
 *  clears exactly the names the launcher prefers. */
export function targetBinaryNames(target) {
  return target ? [`ai-eng-${target}`, `ai-eng-${target}.exe`] : [];
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

/** This machine's target suffix, the one a `bun run build --target` here names. */
export function hostTarget() {
  const musl = process.platform === "linux" ? isMusl() : false;
  return resolveTarget(process.platform, process.arch, musl);
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
 *  no scripts). Its presence is the dev checkout, including `bun link`. */
function isDevCheckout(root) {
  return existsSync(join(root, "scripts", "build.ts"));
}

/** The version this package claims to be. Absent or unreadable manifest: null,
 *  which no binary can match — the source runs and reports its own truth. */
function packageVersion(root) {
  try {
    return JSON.parse(readFileSync(join(root, "package.json"), "utf8")).version ?? null;
  } catch {
    return null;
  }
}

/** What `bun run build` recorded about the one binary it wrote: the version of the
 *  package.json that compile read. scripts/build.ts names the stamp after the
 *  artifact it vouches for, so a build for another target can never make older
 *  bytes look current. Its absence means unknown provenance (a build from before
 *  this rule, a copy, an unpacked artifact), not "probably fine". */
function buildStamp(binaryPath) {
  const artifact = basename(binaryPath).replace(/\.exe$/, "");
  try {
    return readFileSync(join(dirname(binaryPath), `BUILD-VERSION-${artifact}`), "utf8").trim();
  } catch {
    return null;
  }
}

/** A local compile, if one exists AND its own stamp says this package's version
 *  built it. The target-named file is a `bun run build --target` for this host;
 *  `dist/ai-eng` is what a plain `bun run build` writes. Windows may add `.exe`
 *  to either name. */
function localBinary(root, target) {
  const version = packageVersion(root);
  if (version === null) return null;
  for (const name of [...targetBinaryNames(target), "ai-eng", "ai-eng.exe"]) {
    const path = join(root, "dist", name);
    if (existsSync(path) && buildStamp(path) === version) return path;
  }
  return null;
}

/** The source through bun, even when this launcher itself is node (invoked as
 *  `node bin/ai-eng.js`). Never returns: honest error if bun is not on PATH. */
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
  const root = packageRoot();
  if (isDevCheckout(root)) {
    const local = localBinary(root, hostTarget());
    if (local) runBinary(local);
    runSource(root);
  }
  // A published install runs the source and nothing else: the tarball ships no
  // binary, so any dist/ here came from somewhere this package cannot vouch for.
  if (process.versions.bun) {
    await import(join(root, "src", "cli.ts"));
    return;
  }
  // Started by node rather than the bun shebang; the source still runs —
  // through the bun on PATH. runSource never returns (honest error when bun is absent).
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
