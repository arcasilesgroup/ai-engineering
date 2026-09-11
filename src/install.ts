// The installer behind init/uninstall/update: templates → disk, idempotent, 3-way diff
// when the user edited what we installed. Never overwrites a user-edited file in
// silence — that is the worst class of bug a governance tool can have (§14.5).

import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { createHash } from "node:crypto";

export type PlanEntry = {
  path: string; // repo-relative, e.g. ".claude/settings.json"
  ours: string; // the new content from the binary's templates
};

export type InstallReport = {
  written: string[];
  untouched: string[]; // already ours-current, or the user's own file
  conflicts: string[]; // user-edited AND ours changed: needs the human
};

export function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

/** Idempotent install. A file byte-identical to ours is a no-op; a file exactly the
 *  previous version of ours is a safe update; a file the user edited AND that changed
 *  between versions is a conflict, listed — never silently overwritten. `previousOurs`
 *  may answer with the previous text OR with a `sha256:<hex>` sentinel — update.ts
 *  stores hashes in the lock, not bytes (protocol, measured 2026-09-03).
 *  `force` is the human's resolved decision (update's "take"): write ours even
 *  over an edit — only a caller that asked may pass it. */
export function install(
  repoRoot: string,
  entries: PlanEntry[],
  previousOurs?: (path: string) => string | null,
  force?: (path: string) => boolean,
): InstallReport {
  const report: InstallReport = { written: [], untouched: [], conflicts: [] };
  for (const entry of entries) {
    const absolute = join(repoRoot, entry.path);
    const oursHash = sha256(entry.ours);
    if (existsSync(absolute)) {
      const current = readFileSync(absolute, "utf8");
      if (sha256(current) === oursHash) {
        report.untouched.push(entry.path);
        continue;
      }
      const previous = previousOurs?.(entry.path) ?? null;
      if (previous === null) {
        report.untouched.push(entry.path); // we never installed it: it is the user's
        continue;
      }
      const currentHash = sha256(current);
      const previousHash = previous.slice("sha256:".length);
      if (currentHash === previousHash) {
        writeFileSync(absolute, entry.ours);
        report.written.push(entry.path);
        continue;
      }
      if (force?.(entry.path)) {
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

/** The lockfile: sha256 per installed asset + the approved-spec pin. Nothing downloads;
 *  it is an assertion of what this repo expects, not a package manager (§08). */
export type Lock = {
  version: string;
  assets: Record<string, string>;
  spec_sha256?: string;
  /** The commit the live milestone started from: without it a conditional node has no
   *  diff to judge, and "if it touches UI" stays a sentence nobody can check (§20.1). */
  base_sha?: string;
};

export function buildLock(
  entries: PlanEntry[],
  version: string,
  carry: { spec_sha256?: string | undefined; base_sha?: string | undefined } = {},
): Lock {
  const assets: Record<string, string> = {};
  for (const entry of entries) {
    assets[entry.path] = sha256(entry.ours);
  }
  const lock: Lock = { version, assets };
  // The two contract fields are the milestone's, not the installer's. Rebuilding the
  // lock used to drop them, so any `update` between `spec approve` and `spec close`
  // erased the approval and the next `spec run` refused a contract a human had
  // approved — measured in CI, where update runs before spec run (D-011's pipeline).
  if (carry.spec_sha256) lock.spec_sha256 = carry.spec_sha256;
  if (carry.base_sha) lock.base_sha = carry.base_sha;
  return lock;
}

export function lockText(lock: Lock): string {
  const lines = ["# ai-eng.lock — sha256 of the global canon this repo expects (§08).", `version = "${lock.version}"`, ""];
  if (lock.spec_sha256) lines.push(`spec_sha256 = "${lock.spec_sha256}"`, "");
  if (lock.base_sha) lines.push(`base_sha = "${lock.base_sha}"`, "");
  lines.push("[assets]");
  for (const [path, hash] of Object.entries(lock.assets)) lines.push(`"${path}" = "${hash}"`);
  return `${lines.join("\n")}\n`;
}

export function parseLock(text: string): Lock {
  const doc = Bun.TOML.parse(text) as Record<string, unknown>;
  const assets: Record<string, string> = {};
  const raw = doc["assets"];
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    for (const [path, hash] of Object.entries(raw as Record<string, unknown>)) {
      if (typeof hash === "string") assets[path] = hash;
    }
  }
  const lock: Lock = { version: typeof doc["version"] === "string" ? doc["version"] : "", assets };
  if (typeof doc["spec_sha256"] === "string") lock.spec_sha256 = doc["spec_sha256"];
  if (typeof doc["base_sha"] === "string") lock.base_sha = doc["base_sha"];
  return lock;
}
