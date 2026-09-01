// The planter behind init/uninstall/update: templates → disk, idempotent, 3-way diff
// when the user edited what we planted. Never overwrites a user-edited file in
// silence — that is the worst class of bug a governance tool can have (§14.5).

import { existsSync, readFileSync, writeFileSync, mkdirSync, symlinkSync, lstatSync } from "node:fs";
import { join, dirname } from "node:path";
import { createHash } from "node:crypto";
import { parseToml } from "./toml.ts";

export type PlanEntry = {
  path: string; // repo-relative, e.g. ".claude/settings.json"
  ours: string; // the new content from the binary's templates
  mode?: "file" | "symlink";
  target?: string; // for symlinks
};

export type PlantReport = {
  written: string[];
  untouched: string[]; // already ours-current, or the user's own file
  conflicts: string[]; // user-edited AND ours changed: needs the human
};

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

/** Idempotent plant. A file byte-identical to ours is a no-op; a file exactly the
 *  previous version of ours is a safe update; a file the user edited AND that changed
 *  between versions is a conflict, listed — never silently overwritten. */
export function plant(repoRoot: string, entries: PlanEntry[], previousOurs?: (path: string) => string | null): PlantReport {
  const report: PlantReport = { written: [], untouched: [], conflicts: [] };
  for (const entry of entries) {
    const absolute = join(repoRoot, entry.path);
    if (entry.mode === "symlink") {
      plantSymlink(absolute, entry);
      report.written.push(entry.path);
      continue;
    }
    const oursHash = sha256(entry.ours);
    if (existsSync(absolute)) {
      const current = readFileSync(absolute, "utf8");
      if (sha256(current) === oursHash) {
        report.untouched.push(entry.path);
        continue;
      }
      const previous = previousOurs?.(entry.path) ?? null;
      if (previous === null) {
        report.untouched.push(entry.path); // we never planted it: it is the user's
        continue;
      }
      if (sha256(current) === sha256(previous)) {
        writeFileSync(absolute, entry.ours);
        report.written.push(entry.path);
        continue;
      }
      report.conflicts.push(entry.path);
      continue;
    }
    mkdirSync(dirname(absolute), { recursive: true });
    writeFileSync(absolute, entry.ours);
    report.written.push(entry.path);
  }
  return report;
}

function plantSymlink(absolute: string, entry: PlanEntry): void {
  const target = entry.target ?? entry.ours;
  try {
    const stats = lstatSync(absolute);
    const existing = readlinkSafe(absolute);
    if (existing === target) return; // already correct
    if (stats.isDirectory()) return; // never destroy a real directory
    symlinkSync(target, absolute);
    return;
  } catch {
    /* does not exist: create below */
  }
  mkdirSync(dirname(absolute), { recursive: true });
  try {
    symlinkSync(target, absolute);
  } catch {
    writeFileSync(absolute, ""); // FS refused symlinks: empty marker, verified copy path (doctor checks)
  }
}

function readlinkSafe(path: string): string | null {
  try {
    const { readlinkSync } = require("node:fs") as typeof import("node:fs");
    return readlinkSync(path);
  } catch {
    return null;
  }
}

/** The lockfile: sha256 per planted asset + the approved-spec pin. Nothing downloads;
 *  it is an assertion of what this repo expects, not a package manager (§08). */
export type Lock = {
  version: string;
  assets: Record<string, string>;
  spec_sha256?: string;
};

export function buildLock(entries: PlanEntry[], version: string, specContent?: string): Lock {
  const assets: Record<string, string> = {};
  for (const entry of entries) {
    if (entry.mode === "symlink") continue;
    assets[entry.path] = sha256(entry.ours);
  }
  const lock: Lock = { version, assets };
  if (specContent) lock.spec_sha256 = sha256(specContent);
  return lock;
}

export function lockText(lock: Lock): string {
  const lines = ["# ai-eng.lock — sha256 of the global canon this repo expects (§08).", `version = "${lock.version}"`, ""];
  if (lock.spec_sha256) lines.push(`spec_sha256 = "${lock.spec_sha256}"`, "");
  lines.push("[assets]");
  for (const [path, hash] of Object.entries(lock.assets)) lines.push(`"${path}" = "${hash}"`);
  return `${lines.join("\n")}\n`;
}

export function parseLock(text: string): Lock {
  const doc = parseToml(text);
  const assets: Record<string, string> = {};
  const raw = doc["assets"];
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    for (const [path, hash] of Object.entries(raw as Record<string, unknown>)) {
      if (typeof hash === "string") assets[path] = hash;
    }
  }
  const lock: Lock = { version: String(doc["version"] ?? ""), assets };
  if (typeof doc["spec_sha256"] === "string") lock.spec_sha256 = doc["spec_sha256"];
  return lock;
}
