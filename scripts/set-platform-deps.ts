#!/usr/bin/env bun
// scripts/set-platform-deps.ts — write the eight platform optionalDependencies
// into package.json at release time. They are NOT committed: their version is
// this package's own version, and a static list is a second source of truth
// that rots the day someone bumps the version and forgets the mirrors.
//
// release.yml runs this after `changeset version` has decided the number and
// before `npm publish`, so the published tarball is complete and the working
// tree stays clean (the step restores the file afterwards).
//
// Usage: bun scripts/set-platform-deps.ts [--restore]

import { readFileSync, writeFileSync } from "node:fs";

const TARGETS = [
  "darwin-arm64",
  "darwin-x64",
  "linux-x64",
  "linux-arm64",
  "linux-musl-x64",
  "linux-musl-arm64",
  "windows-x64",
  "windows-arm64",
];

const path = "package.json";
const original = readFileSync(path, "utf8");
const pkg = JSON.parse(original) as { version: string; optionalDependencies: Record<string, string> };

if (process.argv.includes("--restore")) {
  writeFileSync(path, original);
  console.log("set-platform-deps: package.json restored");
  process.exit(0);
}

pkg.optionalDependencies = Object.fromEntries(
  TARGETS.map((target) => [`ai-engineering-${target}`, pkg.version]),
);

// Deterministic output: same JSON.stringify the version step's diff expects,
// plus a trailing newline like every other generated file in this repository.
writeFileSync(path, `${JSON.stringify(pkg, null, 2)}\n`);
console.log(`set-platform-deps: ${TARGETS.length} optionalDependencies @ ${pkg.version}`);
