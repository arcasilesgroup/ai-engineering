// The program behind tests/fixtures/gitleaks-shim.ts: compiled into a real `gitleaks`
// executable, so the floor resolves it from PATH the way it resolves the real binary on
// every platform (Windows runs no `#!/bin/sh` script). What it answers is read from the
// gitleaks-shim.json written beside it, so one compile serves every test in a file.
import { copyFileSync, lstatSync, readdirSync, readFileSync, statSync, writeFileSync, writeSync } from "node:fs";
import { dirname, join } from "node:path";
import type { GitleaksBehaviour } from "./gitleaks-shim.ts";

const behaviour = JSON.parse(readFileSync(join(dirname(process.execPath), "gitleaks-shim.json"), "utf8")) as GitleaksBehaviour;
const args = process.argv.slice(2);

function isDirectory(path: string | undefined): boolean {
  if (path === undefined) return false;
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

/** The first text file under `root` that carries an AWS key id, as `grep -rIl` finds it.
 *  `allowed` decides per relative path; the default scans everything. */
function firstLeak(root: string, allowed: (relative: string) => boolean = () => true, prefix = ""): string | null {
  for (const name of readdirSync(root)) {
    const path = join(root, name);
    const relative = prefix.length === 0 ? name : `${prefix}/${name}`;
    const entry = lstatSync(path);
    if (entry.isDirectory()) {
      const nested = firstLeak(path, allowed, relative);
      if (nested !== null) return nested;
      continue;
    }
    if (!entry.isFile() || !allowed(relative)) continue;
    const bytes = readFileSync(path);
    if (bytes.includes(0)) continue;
    if (/AKIA[0-9A-Z]+/.test(bytes.toString("utf8"))) return path;
  }
  return null;
}

function answer(stdout: string, code: number): never {
  if (stdout.length > 0) writeSync(1, stdout);
  process.exit(code);
}

if (args[0] === "version") answer("8.18.0\n", behaviour.mode === "strict" ? behaviour.versionExit ?? 0 : 0);

if (behaviour.mode === "grep") {
  const target = args.findLast((arg) => isDirectory(arg)) ?? ".";
  const hit = firstLeak(target);
  if (hit === null) answer("", 0);
  answer(`Finding:     AWS access token\nFile:        ${hit}\nRuleID:      aws-access-token\n`, 1);
}

if (behaviour.mode === "record-env") {
  const config = process.env["GITLEAKS_CONFIG"];
  writeFileSync(behaviour.record, config ?? "unset");
  if (config) copyFileSync(config, `${behaviour.record}.copy`);
  answer("", 0);
}

if (behaviour.mode === "leaky") {
  const target = args.findLast((arg) => isDirectory(arg)) ?? ".";
  const exemptions: string[] = [];
  const config = process.env["GITLEAKS_CONFIG"];
  if (config) {
    try {
      const parsed = Bun.TOML.parse(readFileSync(config, "utf8")) as { allowlist?: { paths?: string[] } };
      exemptions.push(...(parsed.allowlist?.paths ?? []));
    } catch {
      // a config this fixture cannot read exempts nothing
    }
  }
  // The fixture is blunt about .gitleaksignore: its presence in the scan root
  // suppresses the one finding the fixture can produce.
  let isIgnored = false;
  try {
    readFileSync(join(target, ".gitleaksignore"));
    isIgnored = true;
  } catch {
    // no ignore file in the scan root
  }
  const hit = firstLeak(target, (relative) => !isIgnored && !exemptions.some((pattern) => pattern === "*" || new RegExp(pattern).test(relative)));
  if (hit === null) answer("", 0);
  answer(`Finding:     AWS access token\nFile:        ${hit}\nRuleID:      aws-access-token\n`, 1);
}

if (behaviour.mode === "strict") {
  const isStagedScan = args[0] === "dir" && args[1] === "--redact" && args[2] === "--no-banner" && args[3] === "--exit-code" && args[4] === "1" && isDirectory(args[5]);
  const isPushScan = args[0] === "git" && args[1] === "--redact" && args[2] === "-v";
  if (isStagedScan || isPushScan) answer(behaviour.scanOut ?? "", behaviour.scanExit);
}

writeSync(2, `BADECHO: ${args.join(" ")}\n`);
process.exit(42);
