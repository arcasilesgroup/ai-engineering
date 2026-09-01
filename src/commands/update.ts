// `ai-eng update` — re-plant this repo's assets from the installed binary. ZERO
// network: the payload leaves the binary the user already installed (§14.3). What
// is the user's (AGENTS.md, DECISIONS.md, spec/plan, arch.rules) is never touched.

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { plant, buildLock, lockText, parseLock } from "../plant.ts";
import type { PlanEntry } from "../plant.ts";
import { repoRoot, loadConfig } from "../env.ts";
import { planEntries } from "./init-shared.ts";
import { VERSION } from "../version.ts";

export function updateMain(): number {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("update: you are not in a governed repo.\n");
    return 2;
  }
  const lockPath = join(root, ".ai-engineering", "ai-eng.lock");
  if (!existsSync(lockPath)) {
    process.stderr.write("update: no ai-eng.lock — run ai-eng init first.\n");
    return 2;
  }
  const previous = parseLock(readFileSync(lockPath, "utf8"));
  // Surfaces from config.toml — update re-plants what init planted, nothing else.
  const config = loadConfig();
  const surfaces = (config["surfaces"]?.["enabled"] as unknown as string[] | undefined) ?? ["claude-code"];
  const entries: PlanEntry[] = planEntries(Array.isArray(surfaces) ? surfaces : ["claude-code"]);
  const previousOurs = (path: string): string | null => {
    const hash = previous.assets[path];
    return hash ? `sha256:${hash}` : null;
  };
  const report = plant(root, entries, (path) => {
    const hash = previous.assets[path];
    return hash ? `hash-match:${hash}` : null;
  });
  // Hash-based 3-way: compare current content hash against the lock's recorded hash.
  const conflicts = entries.filter((entry) => {
    const recorded = previous.assets[entry.path];
    if (!recorded) return false;
    const absolute = join(root, entry.path);
    if (!existsSync(absolute)) return false;
    const { createHash } = require("node:crypto") as typeof import("node:crypto");
    const currentHash = createHash("sha256").update(readFileSync(absolute)).digest("hex");
    return currentHash !== recorded && currentHash !== createHash("sha256").update(entry.ours).digest("hex");
  });
  void previousOurs;
  for (const written of report.written) process.stdout.write(`✓ ${written} synced\n`);
  for (const untouched of report.untouched) process.stdout.write(`· ${untouched} (already current or yours)\n`);
  for (const conflict of conflicts) {
    process.stdout.write(`⚠ ${conflict.path ?? conflict} — patched by you: 3-way diff. Merge, keep yours, or show the diff?\n`);
  }
  process.stdout.write("untouchable (yours): AGENTS.md · DECISIONS.md · .ai-engineering/{spec,plan}.html · arch.rules.json · overrides.toml\n");
  const lock = buildLock(entries, VERSION);
  const { writeFileSync } = require("node:fs") as typeof import("node:fs");
  writeFileSync(lockPath, lockText(lock));
  process.stdout.write(`✓ ai-eng.lock rewritten (${Object.keys(lock.assets).length} assets)\n`);
  process.stdout.write("Next: ai-eng doctor — verify the chain still works with the new hooks\n");
  return 0;
}
