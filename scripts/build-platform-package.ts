#!/usr/bin/env bun
// scripts/build-platform-package.ts — pack one compiled binary into the npm
// platform package release.yml publishes: ai-engineing-<target>@<version>.
//
// The binary IS the payload (blueprint 07): everything the CLI needs travels
// inside the executable, so the package is one file plus its metadata. A
// package without its binary refuses to publish — a package that names a
// binary it does not carry is the exact "registry artifact with no payload"
// this repository's release rules forbid (release.yml:19-20, one channel per
// artifact).
//
// Usage: bun scripts/build-platform-package.ts --target bun-linux-x64 [--out dist]

import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const args = process.argv.slice(2);

function flag(name: string): string | null {
  const at = args.indexOf(`--${name}`);
  if (at === -1) return null;
  const value = args[at + 1];
  if (!value || value.startsWith("--")) throw new Error(`flag --${name} needs a value`);
  return value;
}

const target = flag("target");
const outDir = flag("out") ?? "dist";
if (!target) {
  process.stderr.write("usage: bun scripts/build-platform-package.ts --target bun-linux-x64 [--out dist]\n");
  process.exit(2);
}
// Same shape build.ts accepts: bun-linux-x64, bun-darwin-arm64, …
const suffix = target.replace(/^bun-/, "");
const packageName = `ai-engineering-${suffix}`;
const pkg = JSON.parse(readFileSync("package.json", "utf8")) as {
  version: string;
  license: string;
  repository: { type: string; url: string };
};
const binName = suffix.startsWith("windows-") ? "ai-eng.exe" : "ai-eng";

const binary = join(outDir, `ai-eng-${suffix}`);
const stage = join(outDir, packageName);

let binaryBytes: Buffer;
try {
  binaryBytes = readFileSync(binary);
} catch {
  process.stderr.write(`build-platform-package: ${binary} not found — run \`bun run build --target ${target}\` first\n`);
  process.exit(1);
}
// A real compile is ~59-85 MB; anything smaller is a truncated or placeholder
// artifact, and publishing it would break every npm install.
if (binaryBytes.length < 1024 * 1024) {
  process.stderr.write(`build-platform-package: ${binary} is ${(binaryBytes.length / 1024 / 1024).toFixed(1)} MB — too small to be a compiled ai-eng; refusing to pack\n`);
  process.exit(1);
}

mkdirSync(join(stage, "bin"), { recursive: true });
copyFileSync(binary, join(stage, "bin", binName));

const manifest = {
  name: packageName,
  version: pkg.version,
  description: `ai-engineing compiled binary for ${suffix} — installed as an optional dependency of ai-engineing`,
  license: pkg.license,
  repository: pkg.repository,
  os: [suffix.startsWith("windows-") ? "win32" : suffix.startsWith("darwin-") ? "darwin" : "linux"],
  cpu: [suffix.endsWith("-arm64") ? "arm64" : "x64"],
  files: ["bin"],
};

writeFileSync(join(stage, "package.json"), `${JSON.stringify(manifest, null, 2)}\n`);

const muslNote = suffix.includes("musl") ? " (musl)" : "";
console.log(`build-platform-package: staged ${packageName}@${pkg.version}${muslNote} — ${join(stage, "bin", binName)}`);
